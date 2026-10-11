# CloudGuard — AWS Security Auditing and CI Guardrails

CloudGuard is a hands-on cloud security project that checks a live AWS S3
bucket, tests audit logic with simulated AWS resources, and scans Terraform
configuration through GitHub Actions.

It demonstrates preventive checks before merging code and a manually
reviewed workflow for correcting live configuration drift.

## What it does

- Audits a configured AWS S3 bucket using Python and Boto3.
- Checks all four bucket-level Block Public Access settings.
- Checks that bucket versioning is enabled.
- Checks that default encryption matches the project's SSE-S3 baseline.
- Saves timestamped JSON audit reports locally.
- Tests compliant and noncompliant configurations with pytest and Moto.
- Validates Terraform and scans selected security controls with Checkov.
- Uses required GitHub checks to protect the main branch.

## Tools

Python, Boto3, Moto, pytest, AWS CLI, Amazon S3, IAM, Terraform,
Checkov, Git, and GitHub Actions.

## Project files

| File or directory | Purpose |
| --- | --- |
| `audit_live_s3.py` | Read-only live S3 audit and JSON reporting |
| `test_s3_audit.py` | Four simulated audit test cases |
| `demo_s3.py` | Simulated S3 object demonstration |
| `demo_s3_audit.py` | Simulated S3 audit demonstration |
| `terraform/` | S3 bucket and security configuration |
| `examples/insecure_ssh.tf` | Intentionally insecure SSH scan fixture |
| `examples/restricted_ssh.tf` | Restricted SSH scan fixture |
| `.github/workflows/security.yml` | Automated tests and infrastructure checks |
| `reports/` | Generated local reports; excluded from Git |

## Security checks

### Live S3 audit

| Control | Expected configuration |
| --- | --- |
| Block Public Access | All four bucket-level settings enabled |
| Versioning | Enabled |
| Default encryption | SSE-S3 / AES256 |

The encryption check enforces this project's specific baseline.
SSE-KMS is encrypted, but does not match the SSE-S3 baseline.

### Terraform scans

The S3 scan selects Checkov controls CKV_AWS_19, CKV_AWS_21,
CKV_AWS_53, CKV_AWS_54, CKV_AWS_55, and CKV_AWS_56.

The SSH example scan selects CKV_AWS_24 to detect unrestricted
IPv4 SSH ingress.

These selected checks are not a comprehensive cloud security assessment.

## Run locally on Windows

Run commands from the repository root using PowerShell.

### Install Python dependencies

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run simulated tests

These tests use Moto and do not require real AWS credentials.

```powershell
.\.venv\Scripts\python.exe -m pytest test_s3_audit.py -v
```

The four test cases cover:

1. A compliant bucket.
2. One disabled public-access block.
3. Suspended versioning.
4. An encryption baseline mismatch.

### Run a live audit

The live audit requires an existing bucket and authorized AWS credentials.

Before using your own environment, update `BUCKET_NAME`, `REGION`,
`PROFILE`, and `ACCOUNT_ID` in `audit_live_s3.py`. The expected IAM user
ARN in `main()` must also match your intended audit identity.

The lab uses the `cloudguard` AWS profile and the `cloudguard-lab` IAM user.
With AWS CLI browser login configured:

```powershell
aws login --profile cloudguard --region us-east-2 --remote
.\.venv\Scripts\python.exe audit_live_s3.py
```

The audit needs these S3 read permissions on its target bucket:

- `s3:GetBucketPublicAccessBlock`
- `s3:GetBucketVersioning`
- `s3:GetEncryptionConfiguration`

It also verifies the caller using STS and supplies the expected bucket
owner on S3 audit requests.

Reports are written to `reports/`.

Completed audits return:

- `0`: All checks passed.
- `1`: At least one baseline check failed, with no check errors.
- `2`: At least one check encountered an AWS or SDK error.

Credential or identity failures can stop execution before a report
is generated.

### Run Checkov

Install the scanner in a separate environment:

```powershell
py -3.13 -m venv .venv-checkov
.\.venv-checkov\Scripts\python.exe -m pip install -r requirements-checkov.txt
```

Scan the S3 configuration:

```powershell
.\.venv-checkov\Scripts\python.exe .\.venv-checkov\Scripts\checkov -d terraform --framework terraform --check CKV_AWS_19,CKV_AWS_21,CKV_AWS_53,CKV_AWS_54,CKV_AWS_55,CKV_AWS_56 --skip-download
```

Scan the restricted SSH example:

```powershell
.\.venv-checkov\Scripts\python.exe .\.venv-checkov\Scripts\checkov -f examples/restricted_ssh.tf --framework terraform --check CKV_AWS_24 --skip-download
```

Scanning `examples/insecure_ssh.tf` with the same SSH check is expected
to fail. That file is an intentional test fixture and is excluded
from the passing CI baseline. The SSH examples are not deployed.

### Validate Terraform

Install Terraform before running:

```powershell
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

Validation does not deploy AWS resources.

Deployment requires separately authorized AWS credentials, review of
the account restriction in `terraform/main.tf`, and a reviewed Terraform
plan. The live auditor's bucket setting must match the deployed bucket.

## GitHub Actions

The workflow runs on pushes, pull requests, and manual dispatch.

Its two jobs are:

1. **Python auditor tests**
2. **Terraform validation and security scans**

CI runs simulated tests and static checks without AWS credentials.
It does not run the live auditor or deploy infrastructure.

Branch protection is configured separately in GitHub repository settings.

## Demonstration: insecure SSH change

[Pull request #1](https://github.com/Kmoses16/cloudguard/pull/1)
preserves the demonstration history:

1. The restricted SSH example was changed to allow `0.0.0.0/0`.
2. The infrastructure check failed.
3. The permitted range was restored to `10.20.30.0/24`.
4. The checks passed again.

The private subnet is illustrative. A real deployment must use its
own approved management network.

## Demonstration: live drift remediation

The lab workflow temporarily suspended versioning on the Terraform-managed
S3 bucket, then used the auditor and Terraform to detect and repair the
configuration.

The repair completed with:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

The subsequent independent live audit confirmed:

```text
PASS: All four bucket public-access blocks enabled
PASS: Bucket versioning enabled
PASS: Default encryption matches our SSE-S3 baseline

Summary: 3 passed, 0 failed, 0 errors.
```

The verification report was saved locally as:

```text
s3-audit-20261011T062030572925Z.json
```

Remediation is operator initiated: review a Terraform plan, apply the
approved changes, and rerun the auditor. There is no automatic remediation
service or continuous monitoring in this version.

## Scope and limitations

- Live auditing currently targets one configured S3 bucket.
- Passing results establish only the checked configuration baseline.
- IAM policies, bucket policies, object contents, and account-wide
  exposure are not comprehensively assessed.
- Audit errors are reported separately from failed configuration checks.
- No live security groups are deployed by the SSH demonstration.
- Multi-account discovery and event-driven remediation are future work.

## Credentials, state, and costs

Credentials, virtual environments, generated reports, Terraform state,
and saved plans are excluded from Git.

Real AWS use can consume credits or incur costs depending on the account
plan and usage. Simulated tests do not create AWS resources.

## Cleanup

For the original lab, review a destroy plan from the existing local
Terraform working directory and state:

```powershell
terraform -chdir=terraform plan -destroy
```

Only if the plan targets the intended lab resources, run:

```powershell
terraform -chdir=terraform destroy
```

Review the confirmation before approving. The bucket must be empty,
including object versions and delete markers.

The separately created manual lab bucket is outside this Terraform state
and requires separate cleanup. A fresh clone does not contain the local
state needed to manage the original deployment.