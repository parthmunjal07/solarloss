"""Verify a caller-supplied approved release through the real API without AWS.

This loopback-only tool is separate from local_server's private-S3 adapter and
is not included in the Lambda package. It cannot serve a proposed V3 preview.
"""

import argparse
import hashlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LAMBDA_DIR = Path(__file__).resolve().parent / "lambda"
sys.path.insert(0, str(LAMBDA_DIR))

from solarloss_backend.application import ReviewApplication  # noqa: E402
from solarloss_backend.errors import ArtifactNotFound, InvalidArtifact  # noqa: E402
from solarloss_backend.schema import (  # noqa: E402
    load_versioned_review,
    validate_review_for_experiment,
)


class LocalReleaseStore:
    """One strictly approved local release and generated reports; never contacts S3."""

    def __init__(self, artifact: Path, schema_sha256: str):
        self.raw = artifact.read_bytes()
        review = load_versioned_review(self.raw, approved_v02_schema_sha256=schema_sha256)
        self.experiment_id = review["experiment"]["identifier"]
        validate_review_for_experiment(review, self.experiment_id)
        if artifact.name != f"review_{self.experiment_id}.json":
            raise InvalidArtifact("Release filename must match experiment.identifier")
        self.reports: dict[str, bytes] = {}
        self.report_origin = ""

    def list_experiment_ids(self) -> list[str]:
        return [self.experiment_id]

    def get_review_bytes(self, experiment_id: str) -> bytes:
        if experiment_id != self.experiment_id:
            raise ArtifactNotFound(experiment_id)
        return self.raw

    def save_report(self, experiment_id: str, html_body: str) -> str:
        if experiment_id != self.experiment_id:
            raise ArtifactNotFound(experiment_id)
        raw = html_body.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        path = f"/local-reports/{digest}.html"
        self.reports[path] = raw
        return f"{self.report_origin}{path}"


def build_server(artifact: Path, schema_sha256: str, port: int) -> ThreadingHTTPServer:
    store = LocalReleaseStore(artifact, schema_sha256)
    application = ReviewApplication(store, approved_v02_schema_sha256=schema_sha256)

    class Handler(BaseHTTPRequestHandler):
        def _write_body(self, raw: bytes):
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                # A browser can cancel a query during route navigation.
                pass

        def do_GET(self):
            if self.path.startswith("/local-reports/"):
                raw = store.reports.get(self.path)
                self.send_response(200 if raw is not None else 404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{store.experiment_id}-report.html"',
                )
                self.end_headers()
                self._write_body(raw if raw is not None else b"Report not found")
                return
            response = application.handle_event(
                {
                    "rawPath": self.path,
                    "headers": dict(self.headers),
                    "requestContext": {"http": {"method": "GET"}},
                },
                "local-approved-release-verification",
            )
            self.send_response(response["statusCode"])
            for key, value in response.get("headers", {}).items():
                self.send_header(key, value)
            self.end_headers()
            self._write_body(response.get("body", "").encode("utf-8"))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    store.report_origin = f"http://127.0.0.1:{server.server_address[1]}"
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--schema-sha256", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        server = build_server(args.artifact, args.schema_sha256, args.port)
    except (OSError, InvalidArtifact) as exc:
        raise SystemExit(f"Approved release validation failed: {exc}") from exc
    print(
        json.dumps(
            {
                "local_api": f"http://127.0.0.1:{args.port}",
                "artifact": str(args.artifact),
                "aws_contacted": False,
                "production_environment_changed": False,
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
