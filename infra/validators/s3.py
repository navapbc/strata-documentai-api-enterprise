"""S3 bucket validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class S3Validator(BaseValidator):
    category = "S3"

    def _check_s3(
        self,
        name: str,
        expect_kms: bool = True,
        expect_public_block: bool = True,
    ):
        try:
            self.s3.head_bucket(Bucket=name)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "403", "NoSuchBucket"):
                self.missing(self.category, "S3 Bucket", name)
            else:
                self.missing(self.category, "S3 Bucket", name, str(e))
            return

        drift = []

        if expect_public_block:
            try:
                pab = self.s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
                drift.extend(
                    f"public_access_block.{key} should be true"
                    for key in [
                        "BlockPublicAcls",
                        "BlockPublicPolicy",
                        "IgnorePublicAcls",
                        "RestrictPublicBuckets",
                    ]
                    if not pab.get(key)
                )
            except ClientError:
                drift.append("Cannot read PublicAccessBlock configuration")

        if expect_kms:
            try:
                rules = self.s3.get_bucket_encryption(Bucket=name)[
                    "ServerSideEncryptionConfiguration"
                ]["Rules"]
                algo = (
                    rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
                    if rules
                    else "none"
                )
                if algo != "aws:kms":
                    drift.append(f"SSE algorithm: expected aws:kms, got '{algo}'")
            except ClientError:
                drift.append("No KMS encryption configuration found")

        self.check_or_drift(self.category, "S3 Bucket", name, drift)

    def check_s3(self):
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            bucket = spec.get_by_type("aws_s3_bucket")
            if not bucket:
                continue

            v = bucket.values
            arns = self.component_resources.get(component_name, [])
            s3_arns = filter_arns_by_service(arns, "s3")
            if s3_arns:
                name = extract_name_from_arn(s3_arns[0])
            else:
                name = v.get("bucket")

            if not name:
                self.missing(
                    self.category, "S3 Bucket",
                    f"component={component_name} (not discovered)",
                )
                continue

            is_static_site = component_name in ("admin-ui", "demo-ui")
            self._check_s3(name, expect_kms=not is_static_site)
