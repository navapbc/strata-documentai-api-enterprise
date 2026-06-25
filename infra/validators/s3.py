"""S3 bucket validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator


class S3Validator(BaseValidator):
    def _check_s3(
        self,
        cat: str,
        name: str,
        expect_kms: bool = True,
        expect_public_block: bool = True,
    ):
        try:
            self.s3.head_bucket(Bucket=name)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "403", "NoSuchBucket"):
                self.missing(cat, "S3 Bucket", name)
            else:
                self.missing(cat, "S3 Bucket", name, str(e))
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

        self.check_or_drift(cat, "S3 Bucket", name, drift)

    def check_s3(self):
        cat = "S3"
        # Storage buckets (KMS + public access block)
        for component_tag in ["input-bucket", "output-bucket", "metrics-bucket"]:
            name = self.get_resource_name_by_component_tag(component_tag)
            if not name:
                self.missing(cat, "S3 Bucket", f"component={component_tag} (not discovered)")
            else:
                self._check_s3(cat, name, expect_kms=True)

        # Static site buckets (no KMS)
        for component_tag in ["admin-ui", "demo-ui"]:
            name = self.get_resource_name_by_component_tag(component_tag)
            if not name:
                self.missing(cat, "S3 Bucket", f"component={component_tag} (not discovered)")
            else:
                self._check_s3(cat, name, expect_kms=False)
