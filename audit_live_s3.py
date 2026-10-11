import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


BUCKET_NAME = "cloudguard-moses-iac-8cbc1cf93fb9a987674486494d"
REGION = "us-east-2"
PROFILE = "cloudguard"
ACCOUNT_ID = "661614507571"

PUBLIC_ACCESS_SETTINGS = (
    "BlockPublicAcls",
    "IgnorePublicAcls",
    "BlockPublicPolicy",
    "RestrictPublicBuckets",
)


def check_public_access(s3):
    response = s3.get_public_access_block(
        Bucket=BUCKET_NAME,
        ExpectedBucketOwner=ACCOUNT_ID,
    )
    settings = response["PublicAccessBlockConfiguration"]

    return all(
        settings.get(name) is True
        for name in PUBLIC_ACCESS_SETTINGS
    )


def check_versioning(s3):
    response = s3.get_bucket_versioning(
        Bucket=BUCKET_NAME,
        ExpectedBucketOwner=ACCOUNT_ID,
    )
    return response.get("Status") == "Enabled"


def check_encryption(s3):
    response = s3.get_bucket_encryption(
        Bucket=BUCKET_NAME,
        ExpectedBucketOwner=ACCOUNT_ID,
    )
    rules = response["ServerSideEncryptionConfiguration"]["Rules"]

    return any(
        rule.get("ApplyServerSideEncryptionByDefault", {}).get(
            "SSEAlgorithm"
        ) == "AES256"
        for rule in rules
    )


def main():
    session = boto3.Session(
        profile_name=PROFILE,
        region_name=REGION,
    )

    identity = session.client("sts").get_caller_identity()
    expected_arn = f"arn:aws:iam::{ACCOUNT_ID}:user/cloudguard-lab"

    if identity["Arn"] != expected_arn:
        raise RuntimeError("Unexpected AWS identity. Audit stopped.")

    s3 = session.client("s3")

    checks = [
        ("All four bucket public-access blocks enabled", check_public_access),
        ("Bucket versioning enabled", check_versioning),
        ("Default encryption matches our SSE-S3 baseline", check_encryption),
    ]

    totals = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    findings = []

    print(f"CloudGuard live audit: {BUCKET_NAME}")
    print(f"Region: {REGION}")
    print("Mode: read-only\n")

    for label, check in checks:
        error_code = None

        try:
            status = "PASS" if check(s3) else "FAIL"
            print(f"{status}: {label}")
        except ClientError as error:
            status = "ERROR"
            error_code = error.response["Error"]["Code"]
            print(f"ERROR: {label} — AWS returned {error_code}")
        except BotoCoreError as error:
            status = "ERROR"
            error_code = type(error).__name__
            print(f"ERROR: {label} — {error_code}")

        totals[status] += 1

        findings.append({
            "check_id": check.__name__,
            "description": label,
            "status": status,
            "error_code": error_code,
        })

    print(
        f"\nSummary: {totals['PASS']} passed, "
        f"{totals['FAIL']} failed, "
        f"{totals['ERROR']} errors."
    )

    completed_at = datetime.now(timezone.utc)

    report = {
        "project": "CloudGuard",
        "report_version": 1,
        "completed_at_utc": completed_at.isoformat(),
        "mode": "live-read-only",
        "account_id": identity["Account"],
        "identity_arn": identity["Arn"],
        "region": REGION,
        "bucket": BUCKET_NAME,
        "findings": findings,
        "summary": totals,
    }

    report_directory = Path(__file__).resolve().parent / "reports"
    report_directory.mkdir(exist_ok=True)

    filename = completed_at.strftime("s3-audit-%Y%m%dT%H%M%S%fZ.json")
    report_path = report_directory / filename

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"Report saved: {report_path}")

    return 2 if totals["ERROR"] else 1 if totals["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())