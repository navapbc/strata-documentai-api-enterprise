"""SQS queue validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


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

        # Derive SQS specs from expected.json
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            queues = spec.get_all_by_type("aws_sqs_queue")
            if not queues:
                continue

            arns = self.component_resources.get(component_name, [])
            sqs_arns = filter_arns_by_service(arns, "sqs")

            for queue in queues:
                v = queue.values
                queue_name = v.get("name")

                # Try to match by name from discovered SQS ARNs
                if sqs_arns:
                    matched = next(
                        (extract_name_from_arn(a) for a in sqs_arns
                         if extract_name_from_arn(a) == queue_name),
                        None,
                    )
                    if matched:
                        queue_name = matched

                if not queue_name:
                    self.missing(self.category, "SQS Queue", f"component={component_name} (not discovered)")
                    continue

                self._check_sqs(queue_name)
