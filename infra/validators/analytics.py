"""Glue and Athena analytics validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import filter_arns_by_service


class AnalyticsValidator(BaseValidator):
    category = "Analytics"

    def check_analytics(self):

        arns = self.component_resources.get("analytics", [])

        if not arns:
            self.warn(self.category, "Analytics", "component=analytics", "not discovered via tags")
            return

        # Glue database
        glue_arns = filter_arns_by_service(arns, "glue")
        glue_db = None
        for arn in glue_arns:
            if ":database/" in arn:
                glue_db = arn.split("/")[-1]
                break

        if not glue_db:
            self.warn(
                self.category, "Glue Database", "component=analytics", "no glue DB found via tags"
            )
        else:
            try:
                self.glue.get_database(Name=glue_db)
                self.ok(self.category, "Glue Database", glue_db)

                try:
                    self.glue.get_table(DatabaseName=glue_db, Name="raw_metrics")
                    self.ok(self.category, "Glue Table", f"{glue_db}.raw_metrics")
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.ENTITY_NOT_FOUND:
                        self.missing(self.category, "Glue Table", f"{glue_db}.raw_metrics")
                    else:
                        self.missing(self.category, "Glue Table", f"{glue_db}.raw_metrics", str(e))

            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == AwsErrorCode.ENTITY_NOT_FOUND:
                    self.missing(self.category, "Glue Database", glue_db)
                else:
                    self.missing(self.category, "Glue Database", glue_db, str(e))

        # Athena workgroup
        athena_arns = filter_arns_by_service(arns, "athena")
        athena_wg = None
        for arn in athena_arns:
            if ":workgroup/" in arn:
                athena_wg = arn.split("/")[-1]
                break

        if not athena_wg:
            self.warn(
                self.category,
                "Athena Workgroup",
                "component=analytics",
                "no workgroup found via tags",
            )
        else:
            try:
                wg = self.athena.get_work_group(WorkGroup=athena_wg)["WorkGroup"]
                drift = []
                enforce = wg.get("Configuration", {}).get("EnforceWorkGroupConfiguration", False)
                if not enforce:
                    drift.append("enforce_workgroup_configuration: should be true")
                self.check_or_drift(self.category, "Athena Workgroup", athena_wg, drift)
            except ClientError as e:
                self.missing(self.category, "Athena Workgroup", athena_wg, str(e))
