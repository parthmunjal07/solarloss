import hashlib
import re
from typing import Protocol

from .errors import ArtifactNotFound, InvalidExperimentId, StorageUnavailable

_EXPERIMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class ReviewStore(Protocol):
    def list_experiment_ids(self) -> list[str]: ...

    def get_review_bytes(self, experiment_id: str) -> bytes: ...

    def save_report(self, experiment_id: str, html_body: str) -> str: ...


class S3ReviewStore:
    """S3 adapter for private, versioned review artifacts and generated reports."""

    def __init__(
        self,
        client,
        bucket: str,
        review_prefix: str = "artifacts/reviews/",
        report_prefix: str = "artifacts/reports/",
        report_url_ttl_seconds: int = 900,
    ) -> None:
        if not bucket:
            raise ValueError("REVIEW_BUCKET is required")
        if not 60 <= report_url_ttl_seconds <= 604800:
            raise ValueError("REPORT_URL_TTL_SECONDS must be between 60 and 604800")
        self.client = client
        self.bucket = bucket
        self.review_prefix = review_prefix.strip("/") + "/"
        self.report_prefix = report_prefix.strip("/") + "/"
        self.report_url_ttl_seconds = report_url_ttl_seconds

    @staticmethod
    def validate_experiment_id(experiment_id: str) -> str:
        if not _EXPERIMENT_ID.fullmatch(experiment_id):
            raise InvalidExperimentId(experiment_id)
        return experiment_id

    def _review_key(self, experiment_id: str) -> str:
        safe_id = self.validate_experiment_id(experiment_id)
        return f"{self.review_prefix}review_{safe_id}.json"

    def list_experiment_ids(self) -> list[str]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            ids: set[str] = set()
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self.review_prefix):
                for item in page.get("Contents", []):
                    key = item.get("Key", "")
                    name = key[len(self.review_prefix) :]
                    if not (name.startswith("review_") and name.endswith(".json")):
                        continue
                    experiment_id = name[len("review_") : -len(".json")]
                    if _EXPERIMENT_ID.fullmatch(experiment_id):
                        ids.add(experiment_id)
            return sorted(ids)
        except Exception as exc:
            raise StorageUnavailable("Unable to list review artifacts") from exc

    def get_review_bytes(self, experiment_id: str) -> bytes:
        key = self._review_key(experiment_id)
        try:
            result = self.client.get_object(Bucket=self.bucket, Key=key)
            return result["Body"].read()
        except Exception as exc:
            response = getattr(exc, "response", {})
            error = response.get("Error", {}) if isinstance(response, dict) else {}
            code = str(error.get("Code", ""))
            if code in {"NoSuchKey", "NotFound", "404"}:
                raise ArtifactNotFound(experiment_id) from exc
            if getattr(exc, "status_code", None) == 404:
                raise ArtifactNotFound(experiment_id) from exc
            raise StorageUnavailable("Unable to read review artifact") from exc

    def save_report(self, experiment_id: str, html_body: str) -> str:
        safe_id = self.validate_experiment_id(experiment_id)
        body = html_body.encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        key = f"{self.report_prefix}{safe_id}/{digest}.html"
        disposition = f'attachment; filename="solarloss-review-{safe_id}.html"'
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="text/html; charset=utf-8",
                ContentDisposition=disposition,
                CacheControl="private, no-store",
                ServerSideEncryption="AES256",
            )
            return self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ResponseContentDisposition": disposition,
                    "ResponseContentType": "text/html; charset=utf-8",
                },
                ExpiresIn=self.report_url_ttl_seconds,
            )
        except Exception as exc:
            raise StorageUnavailable("Unable to save generated report") from exc
