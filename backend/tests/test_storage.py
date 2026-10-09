import pytest

from solarloss_backend.errors import ArtifactNotFound, InvalidExperimentId
from solarloss_backend.storage import S3ReviewStore


class _MissingS3Object(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class _MissingS3Client:
    def get_object(self, **kwargs):
        raise _MissingS3Object()


def test_s3_adapter_maps_missing_object_to_artifact_not_found():
    store = S3ReviewStore(_MissingS3Client(), bucket="private-test-bucket")
    with pytest.raises(ArtifactNotFound):
        store.get_review_bytes("fixture-001")


def test_s3_adapter_rejects_key_injection_before_storage_access():
    store = S3ReviewStore(_MissingS3Client(), bucket="private-test-bucket")
    with pytest.raises(InvalidExperimentId):
        store.get_review_bytes("../other")
