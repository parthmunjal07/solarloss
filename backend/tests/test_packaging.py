import json
from pathlib import Path
from zipfile import ZipFile

from backend.build_lambda import BACKEND_DIR, EXPERIMENTAL_V2_SCHEMA, MANIFEST, SCHEMA
from backend.validate_lambda_package import _REQUIRED, validate_package


def _write_test_package(path: Path, extra_files=(), wrong_files=()):
    with ZipFile(path, "w") as archive:
        for name in _REQUIRED:
            if name in wrong_files:
                content = b"SYNTHETIC STALE PACKAGE TEST FIXTURE"
            elif name == "manifest.json":
                content = MANIFEST.read_bytes()
            elif name == "artifacts/schema/review.schema.json":
                content = SCHEMA.read_bytes()
            elif name == "artifacts/schema/review.schema.v0.2.0.proposed.json":
                content = EXPERIMENTAL_V2_SCHEMA.read_bytes()
            elif name == "build-info/requirements-lambda.txt":
                content = (BACKEND_DIR / "requirements-lambda.txt").read_bytes()
            else:
                content = b"SYNTHETIC PACKAGE TEST FIXTURE"
            archive.writestr(name, content)
        for name in extra_files:
            archive.writestr(name, b"SYNTHETIC PACKAGE TEST FIXTURE")


def test_lambda_package_validation_accepts_required_layout(tmp_path):
    package = tmp_path / "synthetic-test-package.zip"
    _write_test_package(package)
    assert validate_package(package) == []


def test_lambda_package_validation_rejects_missing_runtime_dependency(tmp_path):
    package = tmp_path / "synthetic-test-package.zip"
    with ZipFile(package, "w") as archive:
        for name in _REQUIRED - {"boto3/__init__.py"}:
            if name == "manifest.json":
                content = MANIFEST.read_bytes()
            elif name == "artifacts/schema/review.schema.json":
                content = SCHEMA.read_bytes()
            elif name == "artifacts/schema/review.schema.v0.2.0.proposed.json":
                content = EXPERIMENTAL_V2_SCHEMA.read_bytes()
            elif name == "build-info/requirements-lambda.txt":
                content = (BACKEND_DIR / "requirements-lambda.txt").read_bytes()
            else:
                content = b"test"
            archive.writestr(name, content)
    errors = validate_package(package)
    assert "Missing required package file: boto3/__init__.py" in errors


def test_lambda_package_validation_rejects_science_dependencies(tmp_path):
    package = tmp_path / "synthetic-test-package.zip"
    _write_test_package(package, extra_files=("pvlib/__init__.py",))
    assert any("pvlib" in error for error in validate_package(package))


def test_lambda_package_validation_rejects_stale_schema_copy(tmp_path):
    package = tmp_path / "synthetic-test-package.zip"
    _write_test_package(package, wrong_files=("artifacts/schema/review.schema.json",))
    errors = validate_package(package)
    assert "Packaged file differs from source: artifacts/schema/review.schema.json" in errors


def test_lambda_package_validation_rejects_stale_proposed_v2_schema_copy(tmp_path):
    package = tmp_path / "synthetic-test-package.zip"
    _write_test_package(
        package, wrong_files=("artifacts/schema/review.schema.v0.2.0.proposed.json",)
    )
    errors = validate_package(package)
    assert (
        "Packaged file differs from source: artifacts/schema/review.schema.v0.2.0.proposed.json"
        in errors
    )


def test_package_manifest_is_json_and_declares_runtime_boundary():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["runtime"] == "python3.12"
    assert manifest["architecture"] == "x86_64"
    assert manifest["handler"] == "handler.lambda_handler"
    assert manifest["runtime_dependencies"] == ["boto3", "jsonschema"]
    assert manifest["experimental_schema_assets"] == [
        {
            "version": "0.2.0",
            "path": "artifacts/schema/review.schema.v0.2.0.proposed.json",
            "status": "proposed",
            "production_serving": False,
            "activation_gate": "APPROVED_REVIEW_SCHEMA_V02_SHA256",
        }
    ]
