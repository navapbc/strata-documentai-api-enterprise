"""ECR repository validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import extract_name_from_arn


class EcrValidator(BaseValidator):
    category = "ECR"

    def check_ecr(self):

        arns = self.component_resources.get("ecr", [])
        ecr_arns = [a for a in arns if ":repository/" in a]

        if not ecr_arns:
            self.warn(self.category, "ECR Repository", "component=ecr", "not discovered via tags")
            return

        name = extract_name_from_arn(ecr_arns[0])
        try:
            repo_desc = self.ecr.describe_repositories(repositoryNames=[name])["repositories"][0]
            drift = []
            if not repo_desc["imageScanningConfiguration"]["scanOnPush"]:
                drift.append("scan_on_push should be true")
            enc = repo_desc["encryptionConfiguration"]["encryptionType"]
            if enc != "AES256":
                drift.append(f"encryptionType: expected AES256, got {enc}")
            self.check_or_drift(self.category, "ECR Repository", name, drift)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.REPOSITORY_NOT_FOUND:
                self.missing(self.category, "ECR Repository", name)
            else:
                self.missing(self.category, "ECR Repository", name, str(e))
