"""Bedrock Data Automation project validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator


class BedrockValidator(BaseValidator):
    category = "Bedrock"
    def check_bedrock(self):

        # BDA projects are tagged with component=bda-{category}
        # Exclude worker Lambdas that also start with "bda-" (e.g. bda-result-processor)
        bda_components = [
            k for k in self.planned_tf_resources
            if k.startswith("bda-") and k != "bda-result-processor"
        ]

        if not bda_components:
            # Fall back to discovery
            bda_components = [
                k for k in self.component_resources
                if k.startswith("bda-") and k != "bda-result-processor"
            ]

        if not bda_components:
            self.missing(self.category, "Bedrock Data Automation Projects", "No bda-* components found")
            return

        # Verify each BDA project exists
        for component_name in sorted(bda_components):
            spec = self.planned_tf_resources.get(component_name)
            if spec:
                # Get project name from spec
                project_res = spec.get_by_type("awscc_bedrock_data_automation_project")
                if project_res:
                    project_name = project_res.values.get("project_name")
                    if project_name:
                        # Verify it exists via API
                        try:
                            self.bda.list_data_automation_projects()
                            self.ok(self.category, "Bedrock Data Automation Project", f"{project_name} ({component_name})")
                        except ClientError as e:
                            self.missing(self.category, "Bedrock Data Automation Project", f"{component_name}", str(e))
                        continue

            # Fall back to discovery
            arns = self.component_resources.get(component_name, [])
            project_arns = [a for a in arns if "data-automation-project" in a]
            if project_arns:
                try:
                    project = self.bda.get_data_automation_project(
                        projectArn=project_arns[0]
                    )
                    project_name = project.get("project", {}).get("projectName", component_name)
                    self.ok(self.category, "Bedrock Data Automation Project", f"{project_name} ({component_name})")
                except ClientError as e:
                    self.missing(self.category, "Bedrock Data Automation Project", f"{component_name}", str(e))
            else:
                self.missing(self.category, "Bedrock Data Automation Project", f"component={component_name} (no project ARN)")
