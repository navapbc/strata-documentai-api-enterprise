"""EventBridge rules and Lambda trigger validation.

Validates that:
- EventBridge rules (S3 triggers, schedules) exist and are enabled
- SQS event source mappings exist and are active
"""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class TriggersValidator(BaseValidator):
    category = "Triggers"

    def check_triggers(self):
        # Check EventBridge rules
        self._check_eventbridge_rules()
        # Check SQS event source mappings
        self._check_event_source_mappings()

    def _check_eventbridge_rules(self):
        """Check EventBridge rules exist and are enabled."""
        for _component_name, spec in sorted(self.planned_tf_resources.items()):
            rules = spec.get_all_by_type("aws_cloudwatch_event_rule")
            if not rules:
                continue

            for rule in rules:
                rule_name = rule.values.get("name")
                if not rule_name:
                    continue

                try:
                    resp = self.events.describe_rule(Name=rule_name)
                    drift = []
                    state = resp.get("State", "DISABLED")
                    if state != "ENABLED":
                        drift.append(f"state: expected ENABLED, got {state}")
                    self.check_or_drift(
                        self.category, "EventBridge Rule", rule_name, drift
                    )
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == "ResourceNotFoundException":
                        self.missing(self.category, "EventBridge Rule", rule_name)
                    else:
                        self.missing(self.category, "EventBridge Rule", rule_name, str(e))

    def _check_event_source_mappings(self):
        """Check SQS event source mappings are active."""
        # Find Lambda functions that have SQS triggers
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            mappings = spec.get_all_by_type("aws_lambda_event_source_mapping")
            if not mappings:
                continue

            # Get the Lambda function name for this component
            arns = self.component_resources.get(component_name, [])
            lambda_arns = filter_arns_by_service(arns, "lambda")
            if not lambda_arns:
                lmb_spec = spec.get_by_type("aws_lambda_function")
                function_name = lmb_spec.values.get("function_name") if lmb_spec else None
            else:
                function_name = extract_name_from_arn(lambda_arns[0])

            if not function_name:
                continue

            # List event source mappings for this function
            try:
                resp = self.lambda_client.list_event_source_mappings(
                    FunctionName=function_name
                )
                active_mappings = resp.get("EventSourceMappings", [])

                if not active_mappings:
                    self.missing(
                        self.category,
                        "Event Source Mapping",
                        f"{function_name} (no mappings found)",
                    )
                    continue

                for mapping in active_mappings:
                    source_arn = mapping.get("EventSourceArn", "")
                    state = mapping.get("State", "")
                    # Extract queue name from ARN for readability
                    source_name = source_arn.split(":")[-1] if source_arn else "unknown"
                    display = f"{function_name} <- {source_name}"

                    drift = []
                    if state != "Enabled":
                        drift.append(f"state: expected Enabled, got {state}")
                    self.check_or_drift(
                        self.category, "Event Source Mapping", display, drift
                    )

            except ClientError as e:
                self.missing(
                    self.category,
                    "Event Source Mapping",
                    f"{function_name}",
                    str(e),
                )
