"""SQS queue validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import extract_name_from_arn, filter_arns_by_service


class SqsValidator(BaseValidator):
    category = "SQS"

    def _check_sqs(self, name: str):
        try:
            self.sqs.get_queue_url(QueueName=name)
            self.ok(self.category, "SQS Queue", name)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.SQS_NON_EXISTENT_QUEUE:
                self.missing(self.category, "SQS Queue", name)
            else:
                self.missing(self.category, "SQS Queue", name, str(e))

    def check_sqs(self):
        for component_name, component in sorted(self.manifest.items()):
            queues = component.get_all_by_type("aws_sqs_queue")
            if not queues:
                continue

            expected_count = sum(q.values.get("count", 1) for q in queues)
            arns = self.component_resources.get(component_name, [])
            sqs_arns = filter_arns_by_service(arns, "sqs")

            if not sqs_arns:
                self.warn(
                    self.category,
                    "SQS Queue",
                    f"component={component_name}",
                    "not discovered via tags",
                )
                continue

            if len(sqs_arns) < expected_count:
                self.drifted(
                    self.category,
                    "SQS Queue",
                    f"component={component_name}",
                    [f"count: expected {expected_count}, found {len(sqs_arns)}"],
                )

            for arn in sqs_arns:
                queue_name = extract_name_from_arn(arn)
                self._check_sqs(queue_name)
