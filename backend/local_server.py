"""Run the Lambda-compatible handler against configured private S3 artifacts."""

from http import HTTPStatus
from pathlib import Path
import os
import sys
from wsgiref.simple_server import make_server

LAMBDA_DIR = Path(__file__).resolve().parent / "lambda"
sys.path.insert(0, str(LAMBDA_DIR))

from handler import build_application_from_environment  # noqa: E402


class _LocalContext:
    aws_request_id = "local-request"


_api = None


def _application(environ, start_response):
    global _api
    if _api is None:
        _api = build_application_from_environment()
    headers = {
        key[5:].replace("_", "-").title(): value
        for key, value in environ.items()
        if key.startswith("HTTP_")
    }
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    event = {
        "rawPath": environ.get("PATH_INFO", "/"),
        "headers": headers,
        "requestContext": {"http": {"method": environ.get("REQUEST_METHOD", "GET")}},
    }
    response = _api.handle_event(event, _LocalContext.aws_request_id)
    status = int(response["statusCode"])
    body = response.get("body", "").encode("utf-8")
    response_headers = [(key, str(value)) for key, value in response.get("headers", {}).items()]
    response_headers.append(("Content-Length", str(len(body))))
    phrase = HTTPStatus(status).phrase
    start_response(f"{status} {phrase}", response_headers)
    return [body]


def main():
    if not os.environ.get("REVIEW_BUCKET"):
        raise SystemExit("Set REVIEW_BUCKET to an existing private bucket containing review artifacts.")
    print("SolarLoss API listening at http://127.0.0.1:8000")
    with make_server("127.0.0.1", 8000, _application) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
