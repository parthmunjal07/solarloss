"""Build a self-contained ZIP for the Python 3.12 Lambda runtime."""

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
LAMBDA_DIR = BACKEND_DIR / "lambda"
SCHEMA = ROOT / "artifacts" / "schema" / "review.schema.json"
EXPERIMENTAL_V2_SCHEMA = ROOT / "artifacts" / "schema" / "review.schema.v0.2.0.proposed.json"
MANIFEST = LAMBDA_DIR / "manifest.json"


def _copy_application_files(stage: Path) -> None:
    shutil.copy2(LAMBDA_DIR / "handler.py", stage / "handler.py")
    shutil.copytree(LAMBDA_DIR / "solarloss_backend", stage / "solarloss_backend")
    schema_target = stage / "artifacts" / "schema" / "review.schema.json"
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCHEMA, schema_target)
    experimental_schema_target = (
        stage / "artifacts" / "schema" / "review.schema.v0.2.0.proposed.json"
    )
    shutil.copy2(EXPERIMENTAL_V2_SCHEMA, experimental_schema_target)
    shutil.copy2(MANIFEST, stage / "manifest.json")
    lock_target = stage / "build-info" / "requirements-lambda.txt"
    lock_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BACKEND_DIR / "requirements-lambda.txt", lock_target)


def build_lambda_package(output: Path, include_dependencies: bool = True) -> Path:
    """Build the package in a clean temporary directory and return its path."""
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="solarloss-lambda-") as temporary:
        stage = Path(temporary) / "package"
        stage.mkdir()
        if include_dependencies:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-compile",
                    "--only-binary=:all:",
                    "--platform",
                    "manylinux2014_x86_64",
                    "--python-version",
                    "3.12",
                    "--implementation",
                    "cp",
                    "--abi",
                    "cp312",
                    "--requirement",
                    str(BACKEND_DIR / "requirements-lambda.txt"),
                    "--target",
                    str(stage),
                ],
                check=True,
                cwd=ROOT,
            )
        _copy_application_files(stage)
        temporary_output = Path(temporary) / "solarloss-lambda.zip"
        with ZipFile(temporary_output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for source in sorted(stage.rglob("*")):
                if not source.is_file() or source.suffix == ".pyc" or "__pycache__" in source.parts:
                    continue
                relative = source.relative_to(stage).as_posix()
                info = ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, source.read_bytes())
        os.replace(temporary_output, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_DIR / "build" / "solarloss-lambda.zip",
        help="Output ZIP path (default: backend/build/solarloss-lambda.zip)",
    )
    args = parser.parse_args()
    package = build_lambda_package(args.output)
    print(f"Built {package} ({package.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
