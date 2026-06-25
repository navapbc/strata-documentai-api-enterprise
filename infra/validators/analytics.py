"""Glue and Athena analytics validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import filter_arns_by_service


class AnalyticsValidator(BaseValidator):
    def check_analytics(self):
        cat = "Analytics"
        arns = self.component_resources.get("analytics", [])

        # Glue database
        glue_arns = filter_arns_by_service(arns, "glue")
        glue_db = None
        for arn in glue_arns:
            if ":database/" in arn:
                glue_db = arn.split("/")[-1]
                break

        if not glue_db:
            self.missing(cat, "Glue Database", "component=analytics (no glue DB discovered)")
        else:
            try:
                self.glue.get_database(Name=glue_db)
                self.ok(cat, "Glue Database", glue_db)

                # Check for raw_metrics table
                try:
                    self.glue.get_table(DatabaseName=glue_db, Name="raw_metrics")
                    self.ok(cat, "Glue Table", f"{glue_db}.raw_metrics")
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.ENTITY_NOT_FOUND:
                        self.missing(cat, "Glue Table", f"{glue_db}.raw_metrics")
                    else:
                        self.missing(cat, "Glue Table", f"{glue_db}.raw_metrics", str(e))

            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == AwsErrorCode.ENTITY_NOT_FOUND:
                    self.missing(cat, "Glue Database", glue_db)
                else:
                    self.missing(cat, "Glue Database", glue_db, str(e))

        # Athena workgroup
        athena_arns = filter_arns_by_service(arns, "athena")
        athena_wg = None
        for arn in athena_arns:
            if ":workgroup/" in arn:
                athena_wg = arn.split("/")[-1]
                break

        if not athena_wg:
            self.missing(cat, "Athena Workgroup", "component=analytics (no workgroup discovered)")
        else:
            try:
                wg = self.athena.get_work_group(WorkGroup=athena_wg)["WorkGroup"]
                drift = []
                enforce = wg.get("Configuration", {}).get(
                    "EnforceWorkGroupConfiguration", False
                )
                if not enforce:
                    drift.append("enforce_workgroup_configuration: should be true")
                self.check_or_drift(cat, "Athena Workgroup", athena_wg, drift)
            except ClientError as e:
                self.missing(cat, "Athena Workgroup", athena_wg, str(e))
