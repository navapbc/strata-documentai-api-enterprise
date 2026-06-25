"""SQS queue validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class SqsValidator(BaseValidator):
    def _check_sqs(self, name: str):
        cat = "SQS"
        try:
            self.sqs.get_queue_url(QueueName=name)
            self.ok(cat, "SQS Queue", name)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.SQS_NON_EXISTENT_QUEUE:
                self.missing(cat, "SQS Queue", name)
            else:
                self.missing(cat, "SQS Queue", name, str(e))

    def check_sqs(self):
        # Main metrics queue
        name = self.get_resource_name_by_component_tag("metrics-queue")
        if not name:
            self.missing("SQS", "SQS Queue", "component=metrics-queue (not discovered)")
        else:
            self._check_sqs(name)
            # DLQ is conventionally named with -dlq suffix
            self._check_sqs(f"{name}-dlq")

        # Worker DLQs (S3-triggered workers have DLQs)
        for component_tag in ["document-processor", "bda-result-processor"]:
            arns = self.component_resources.get(component_tag, [])
            lambda_arns = filter_arns_by_service(arns, "lambda")
            if lambda_arns:
                worker_name = extract_name_from_arn(lambda_arns[0])
                self._check_sqs(f"{worker_name}-dlq")
