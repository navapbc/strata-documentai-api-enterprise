"""ECR repository validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode


class EcrValidator(BaseValidator):
    category = "ECR"
    def check_ecr(self):

        spec = self.planned_tf_resources.get("ecr")
        if spec:
            repo = spec.get_by_type("aws_ecr_repository")
            if repo:
                name = repo.values.get("name")
            else:
                name = self.get_resource_name_by_component_tag("ecr")
        else:
            name = self.get_resource_name_by_component_tag("ecr")

        if not name:
            self.missing(self.category, "ECR Repository", "component=ecr (not discovered)")
            return

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
