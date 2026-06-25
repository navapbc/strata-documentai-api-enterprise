"""ECR repository validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode


class EcrValidator(BaseValidator):
    def check_ecr(self):
        cat = "ECR"
        name = self.get_resource_name_by_component_tag("ecr")
        if not name:
            self.missing(cat, "ECR Repository", "component=ecr (not discovered)")
            return
        try:
            repo = self.ecr.describe_repositories(repositoryNames=[name])["repositories"][0]
            drift = []
            if not repo["imageScanningConfiguration"]["scanOnPush"]:
                drift.append("scan_on_push should be true")
            enc = repo["encryptionConfiguration"]["encryptionType"]
            if enc != "AES256":
                drift.append(f"encryptionType: expected AES256, got {enc}")
            self.check_or_drift(cat, "ECR Repository", name, drift)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.REPOSITORY_NOT_FOUND:
                self.missing(cat, "ECR Repository", name)
            else:
                self.missing(cat, "ECR Repository", name, str(e))
