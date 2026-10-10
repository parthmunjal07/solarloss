import json
import logging
from typing import Any
from urllib.parse import unquote

from .errors import ArtifactNotFound, InvalidArtifact, InvalidExperimentId, StorageUnavailable
from .report import render_review_report
from .schema import load_review, load_versioned_review, validate_review_for_experiment
from .storage import ReviewStore, S3ReviewStore

logger = logging.getLogger("solarloss")


def parse_allowed_origins(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    origins = frozenset(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())
    if "*" in origins:
        raise ValueError("ALLOWED_ORIGINS must list explicit origins; wildcard CORS is not allowed")
    return origins


class ReviewApplication:
    def __init__(
        self,
        store: ReviewStore,
        schema_path=None,
        allowed_origins: frozenset[str] | None = None,
        approved_v02_schema_sha256: str | None = None,
        experimental_v2_schema_path=None,
    ) -> None:
        self.store = store
        self.schema_path = schema_path
        self.allowed_origins = allowed_origins or frozenset()
        self.approved_v02_schema_sha256 = approved_v02_schema_sha256
        self.experimental_v2_schema_path = experimental_v2_schema_path

    def handle_event(self, event: dict[str, Any], request_id: str) -> dict[str, Any]:
        context = event.get("requestContext") or {}
        http = context.get("http") or {}
        method = str(http.get("method") or event.get("httpMethod") or "GET").upper()
        path = event.get("rawPath") or http.get("path") or event.get("path") or "/"
        path = str(path).split("?", 1)[0]
        if path != "/":
            path = path.rstrip("/") or "/"
        headers = event.get("headers") or {}
        origin = next((value for key, value in headers.items() if key.lower() == "origin"), None)

        if method == "OPTIONS":
            if origin in self.allowed_origins:
                response = {"statusCode": 204, "headers": {}, "body": "", "isBase64Encoded": False}
            else:
                response = self._error(
                    403, "origin_not_allowed", "Request origin is not allowed", request_id
                )
        else:
            response = self._dispatch(method, path, request_id)

        response_headers = response.setdefault("headers", {})
        response_headers.setdefault("X-Request-Id", request_id)
        if origin and origin in self.allowed_origins:
            response_headers.update(
                {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Vary": "Origin",
                }
            )
        return response

    def _dispatch(self, method: str, path: str, request_id: str) -> dict[str, Any]:
        if method != "GET":
            return self._error(
                405, "method_not_allowed", "Only GET and OPTIONS are supported", request_id
            )
        if path == "/api/v1/health":
            return self._json_response(200, {"status": "ok"}, request_id)
        if path == "/api/v1/experiments":
            try:
                return self._json_response(
                    200, {"experiments": self._list_experiments()}, request_id
                )
            except InvalidArtifact:
                return self._error(
                    500,
                    "invalid_review_artifact",
                    "A stored review artifact failed validation",
                    request_id,
                )
            except StorageUnavailable:
                return self._error(
                    503,
                    "storage_unavailable",
                    "Review storage is temporarily unavailable",
                    request_id,
                )

        prefix = "/api/v1/reviews/"
        if path.startswith(prefix):
            tail = path[len(prefix) :].split("/")
            if len(tail) not in (1, 2) or (len(tail) == 2 and tail[1] != "report"):
                return self._error(404, "route_not_found", "Route not found", request_id)
            experiment_id = unquote(tail[0])
            try:
                S3ReviewStore.validate_experiment_id(experiment_id)
                review = self._get_review(experiment_id)
                if len(tail) == 2:
                    report = render_review_report(
                        review,
                        allow_approved_v2=self.approved_v02_schema_sha256 is not None,
                    )
                    report_url = self.store.save_report(experiment_id, report)
                    return {
                        "statusCode": 302,
                        "headers": {
                            "Location": report_url,
                            "Cache-Control": "no-store",
                        },
                        "body": "",
                        "isBase64Encoded": False,
                    }
                return self._json_response(200, review, request_id)
            except InvalidExperimentId:
                return self._error(
                    400, "invalid_experiment_id", "Experiment id has an invalid format", request_id
                )
            except ArtifactNotFound:
                return self._error(
                    404,
                    "review_not_found",
                    "No review artifact exists for this experiment",
                    request_id,
                )
            except InvalidArtifact:
                return self._error(
                    500,
                    "invalid_review_artifact",
                    "The stored review artifact failed validation",
                    request_id,
                )
            except StorageUnavailable:
                return self._error(
                    503,
                    "storage_unavailable",
                    "Review storage is temporarily unavailable",
                    request_id,
                )

        return self._error(404, "route_not_found", "Route not found", request_id)

    def _get_review(self, experiment_id: str) -> dict[str, Any]:
        raw = self.store.get_review_bytes(experiment_id)
        if self.approved_v02_schema_sha256 is None:
            review = load_review(raw, self.schema_path)
        else:
            review = load_versioned_review(
                raw,
                schema_path=self.schema_path,
                approved_v02_schema_sha256=self.approved_v02_schema_sha256,
                experimental_v2_schema_path=self.experimental_v2_schema_path,
            )
        return validate_review_for_experiment(review, experiment_id)

    def _list_experiments(self) -> list[dict[str, Any]]:
        result = []
        for experiment_id in self.store.list_experiment_ids():
            S3ReviewStore.validate_experiment_id(experiment_id)
            review = self._get_review(experiment_id)
            experiment = review["experiment"]
            if review["schema_version"] == "0.2.0":
                result.append(
                    {
                        "experiment_id": experiment_id,
                        "review_id": review["review_id"],
                        "schema_version": review["schema_version"],
                        "experiment_type": experiment["type"],
                        "time_window": {"start": experiment["start"], "end": experiment["end"]},
                        "research_verdict": review["decision"]["verdict"],
                        "event_review": review["decision"]["event_review"],
                    }
                )
            else:
                result.append(
                    {
                        "experiment_id": experiment_id,
                        "review_id": review["review_id"],
                        "analysis_version": review["analysis_version"],
                        "experiment_type": experiment["type"],
                        "experimental_system": experiment["experimental_system"],
                        "reference_system": experiment["reference_system"],
                        "time_window": experiment["time_window"],
                        "decision_state": review["decision"]["state"],
                    }
                )
        return result

    @staticmethod
    def _json_response(status: int, body: Any, request_id: str) -> dict[str, Any]:
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps(body, ensure_ascii=False, allow_nan=False),
            "isBase64Encoded": False,
        }

    @classmethod
    def _error(cls, status: int, code: str, message: str, request_id: str) -> dict[str, Any]:
        return cls._json_response(
            status,
            {"error": {"code": code, "message": message, "request_id": request_id}},
            request_id,
        )
