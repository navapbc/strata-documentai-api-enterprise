"""Monitoring infrastructure validation (SNS topics, CloudWatch alarms/dashboards)."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import filter_arns_by_service


class MonitoringValidator(BaseValidator):
    category = "Monitoring"

    def check_monitoring(self):
        spec = self.planned_tf_resources.get("monitoring")
        if not spec:
            return

        # SNS topics - verify via tag discovery
        for topic in spec.get_all_by_type("aws_sns_topic"):
            topic_name = topic.values.get("name")
            if not topic_name:
                continue

            arns = self.component_resources.get("monitoring", [])
            sns_arns = filter_arns_by_service(arns, "sns")

            if sns_arns:
                self.ok(self.category, "SNS Topic", topic_name)
            else:
                self.missing(self.category, "SNS Topic", topic_name)

        # CloudWatch alarms
        for alarm in spec.get_all_by_type("aws_cloudwatch_metric_alarm"):
            alarm_name = alarm.values.get("alarm_name")
            if not alarm_name:
                continue
            try:
                resp = self.cloudwatch.describe_alarms(AlarmNames=[alarm_name])
                if resp.get("MetricAlarms"):
                    self.ok(self.category, "CloudWatch Alarm", alarm_name)
                else:
                    self.missing(self.category, "CloudWatch Alarm", alarm_name)
            except ClientError:
                self.missing(self.category, "CloudWatch Alarm", alarm_name)

        # CloudWatch dashboards
        for dashboard in spec.get_all_by_type("aws_cloudwatch_dashboard"):
            dashboard_name = dashboard.values.get("dashboard_name")
            if not dashboard_name:
                continue
            try:
                self.cloudwatch.get_dashboard(DashboardName=dashboard_name)
                self.ok(self.category, "CloudWatch Dashboard", dashboard_name)
            except ClientError:
                self.missing(self.category, "CloudWatch Dashboard", dashboard_name)
