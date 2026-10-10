import pytest
from solarloss_backend.errors import ArtifactNotFound, InvalidExperimentId
from solarloss_backend.storage import S3ReviewStore


class _MissingS3Object(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class _MissingS3Client:
    def get_object(self, **kwargs):
        raise _MissingS3Object()


class _ReportS3Client:
    def __init__(self):
        self.put_kwargs = None
        self.presign_kwargs = None

    def put_object(self, **kwargs):
        self.put_kwargs = kwargs

    def generate_presigned_url(self, operation, **kwargs):
        self.presign_kwargs = (operation, kwargs)
        return "https://private.example/presigned-report"


def test_s3_adapter_maps_missing_object_to_artifact_not_found():
    store = S3ReviewStore(_MissingS3Client(), bucket="private-test-bucket")
    with pytest.raises(ArtifactNotFound):
        store.get_review_bytes("fixture-001")


def test_s3_adapter_rejects_key_injection_before_storage_access():
    store = S3ReviewStore(_MissingS3Client(), bucket="private-test-bucket")
    with pytest.raises(InvalidExperimentId):
        store.get_review_bytes("../other")


def test_saved_report_uses_private_presigned_attachment_url():
    client = _ReportS3Client()
    store = S3ReviewStore(client, bucket="private-test-bucket", report_url_ttl_seconds=300)
    url = store.save_report("fixture-001", "<h1>Synthetic test report</h1>")
    assert url == "https://private.example/presigned-report"
    assert client.put_kwargs["Key"].startswith("artifacts/reports/fixture-001/")
    assert client.put_kwargs["ServerSideEncryption"] == "AES256"
    assert client.put_kwargs["ContentDisposition"].startswith("attachment;")
    operation, parameters = client.presign_kwargs
    assert operation == "get_object"
    assert parameters["ExpiresIn"] == 300
    assert parameters["Params"]["Bucket"] == "private-test-bucket"
