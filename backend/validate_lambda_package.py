"""Check required application files, runtime dependencies, and bundle scope."""

import argparse
import json
import re
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from backend.build_lambda import BACKEND_DIR, EXPERIMENTAL_V2_SCHEMA, MANIFEST, SCHEMA

_REQUIRED = {
    "handler.py",
    "solarloss_backend/application.py",
    "solarloss_backend/schema.py",
    "solarloss_backend/storage.py",
    "artifacts/schema/review.schema.json",
    "artifacts/schema/review.schema.v0.2.0.proposed.json",
    "manifest.json",
    "build-info/requirements-lambda.txt",
    "boto3/__init__.py",
    "botocore/__init__.py",
    "jsonschema/__init__.py",
}
_DISALLOWED_PREFIXES = {
    "numpy",
    "pandas",
    "pvlib",
    "scipy",
    "sklearn",
    "torch",
    "tensorflow",
}


def validate_package(package: Path) -> list[str]:
    try:
        with ZipFile(package) as archive:
            names = set(archive.namelist())
            errors = [
                f"Missing required package file: {name}" for name in sorted(_REQUIRED - names)
            ]
            try:
                manifest = json.loads(archive.read("manifest.json"))
            except (KeyError, json.JSONDecodeError) as exc:
                return errors + [f"Invalid or missing package manifest: {exc}"]
            expected_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            if manifest != expected_manifest:
                errors.append(
                    "Package manifest does not match the repository Lambda configuration."
                )
            expected_files = {
                "artifacts/schema/review.schema.json": SCHEMA,
                "artifacts/schema/review.schema.v0.2.0.proposed.json": EXPERIMENTAL_V2_SCHEMA,
                "build-info/requirements-lambda.txt": BACKEND_DIR / "requirements-lambda.txt",
            }
            for name, expected_path in expected_files.items():
                if name in names and archive.read(name) != expected_path.read_bytes():
                    errors.append(f"Packaged file differs from source: {name}")
            disallowed = []
            for name in names:
                top = name.split("/", 1)[0].lower()
                normalized = re.split(r"[-.]", top, maxsplit=1)[0]
                if normalized in _DISALLOWED_PREFIXES:
                    disallowed.append(top)
            if disallowed:
                errors.append(
                    "Scientific dependencies must stay out of Lambda: "
                    + ", ".join(sorted(set(disallowed)))
                )
            return errors
    except (OSError, BadZipFile) as exc:
        return [f"Cannot read Lambda package {package}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Lambda ZIP created by backend.build_lambda")
    args = parser.parse_args()
    errors = validate_package(args.package)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Valid Lambda package: {args.package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
