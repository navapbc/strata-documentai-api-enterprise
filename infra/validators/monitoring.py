"""Monitoring infrastructure validation (SNS topics)."""

from . import BaseValidator
from .discovery import extract_name_from_arn, filter_arns_by_service


class MonitoringValidator(BaseValidator):
    category = "Monitoring"

    def check_monitoring(self):
        monitoring = self.manifest.get("monitoring")
        if not monitoring:
            return

        arns = self.component_resources.get("monitoring", [])
        if not arns:
            self.warn(
                self.category, "Monitoring", "component=monitoring", "not discovered via tags"
            )
            return

        # SNS topics - verify via tag discovery
        sns_arns = filter_arns_by_service(arns, "sns")
        sns_entries = monitoring.get_all_by_type("aws_sns_topic")
        if sns_entries:
            if sns_arns:
                self.ok(self.category, "SNS Topic", extract_name_from_arn(sns_arns[0]))
            else:
                self.warn(
                    self.category,
                    "SNS Topic",
                    "component=monitoring",
                    "no SNS topic discovered via tags",
                )
