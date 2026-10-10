import json
import logging
import os
import time
import uuid

import boto3
from solarloss_backend.application import ReviewApplication, parse_allowed_origins
from solarloss_backend.storage import S3ReviewStore


class _JsonFormatter(logging.Formatter):
    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for name in ("request_id", "method", "path", "status_code", "experiment_id", "error_type"):
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("solarloss")
logger.setLevel(logging.INFO)
if not logger.handlers:
    stream = logging.StreamHandler()
    stream.setFormatter(_JsonFormatter())
    logger.addHandler(stream)
logger.propagate = False

_application: ReviewApplication | None = None


def configure_application(application: ReviewApplication | None) -> None:
    """Dependency injection seam used by local tools and tests."""
    global _application
    _application = application


def build_application_from_environment() -> ReviewApplication:
    bucket = os.environ.get("REVIEW_BUCKET", "")
    store = S3ReviewStore(
        client=boto3.client("s3"),
        bucket=bucket,
        review_prefix=os.environ.get("REVIEW_PREFIX", "artifacts/reviews/"),
        report_prefix=os.environ.get("REPORT_PREFIX", "artifacts/reports/"),
        report_url_ttl_seconds=int(os.environ.get("REPORT_URL_TTL_SECONDS", "900")),
    )
    return ReviewApplication(
        store=store,
        approved_v02_schema_sha256=os.environ.get("APPROVED_REVIEW_SCHEMA_V02_SHA256") or None,
        allowed_origins=parse_allowed_origins(os.environ.get("ALLOWED_ORIGINS")),
    )


def _get_application() -> ReviewApplication:
    global _application
    if _application is None:
        _application = build_application_from_environment()
    return _application


def lambda_handler(event, context):
    request_context = event.get("requestContext") or {}
    request_id = (
        request_context.get("requestId")
        or getattr(context, "aws_request_id", None)
        or str(uuid.uuid4())
    )
    http = request_context.get("http") or {}
    method = str(http.get("method") or event.get("httpMethod") or "GET").upper()
    path = event.get("rawPath") or http.get("path") or event.get("path") or "/"
    try:
        response = _get_application().handle_event(event, request_id)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.get("statusCode"),
            },
        )
        return response
    except Exception as exc:
        logger.error(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": 500,
                "error_type": type(exc).__name__,
            },
        )
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "X-Request-Id": request_id,
            },
            "body": json.dumps(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "The review request could not be completed",
                        "request_id": request_id,
                    }
                }
            ),
            "isBase64Encoded": False,
        }
