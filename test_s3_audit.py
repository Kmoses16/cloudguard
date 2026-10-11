import boto3
import pytest
from moto import mock_aws

import audit_live_s3 as auditor


@pytest.mark.parametrize(
    "block_policy,versioning,algorithm,expected",
    [
        (True, "Enabled", "AES256", (True, True, True)),
        (False, "Enabled", "AES256", (False, True, True)),
        (True, "Suspended", "AES256", (True, False, True)),
        (True, "Enabled", "aws:kms", (True, True, False)),
    ],
    ids=[
        "compliant-bucket",
        "one-public-access-block-disabled",
        "versioning-suspended",
        "encryption-baseline-mismatch",
    ],
)
def test_bucket_checks(
    monkeypatch, block_policy, versioning, algorithm, expected
):
    # Use dummy credentials only inside this test process.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("MOTO_ACCOUNT_ID", "123456789012")

    # Temporarily point the auditor at our simulated bucket.
    monkeypatch.setattr(auditor, "BUCKET_NAME", "cloudguard-test-bucket")
    monkeypatch.setattr(auditor, "ACCOUNT_ID", "123456789012")

    with mock_aws():
        session = boto3.Session(region_name="us-east-1")
        s3 = session.client("s3")
        bucket = auditor.BUCKET_NAME

        s3.create_bucket(Bucket=bucket)

        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": block_policy,
                "RestrictPublicBuckets": True,
            },
        )

        s3.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={"Status": versioning},
        )

        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": algorithm
                        }
                    }
                ]
            },
        )

        actual = (
            auditor.check_public_access(s3),
            auditor.check_versioning(s3),
            auditor.check_encryption(s3),
        )

        assert actual == expected