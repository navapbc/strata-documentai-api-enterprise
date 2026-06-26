"""Bedrock Data Automation project validation.

Uses direct BDA API listing since AWSCC-managed resources are not indexed
by the Resource Groups Tagging API.
"""

from botocore.exceptions import ClientError

from . import BaseValidator


class BedrockValidator(BaseValidator):
    category = "Bedrock"

    def check_bedrock(self):
        # BDA components in spec (exclude worker lambdas like bda-result-processor)
        bda_components = [
            k
            for k in self.manifest
            if k.startswith("bda-")
            and self.manifest[k].get_by_type("awscc_bedrock_data_automation_project")
        ]

        if not bda_components:
            return

        # List all BDA projects once via API
        try:
            projects = []
            resp = self.bda.list_data_automation_projects(maxResults=100)
            projects.extend(resp.get("projects", []))
            while resp.get("nextToken"):
                resp = self.bda.list_data_automation_projects(
                    maxResults=100, nextToken=resp["nextToken"]
                )
                projects.extend(resp.get("projects", []))
        except ClientError as e:
            self.warn(self.category, "Bedrock Data Automation", "list-projects", str(e))
            return

        project_names = {p.get("projectName", ""): p for p in projects}

        # Check each expected BDA component has a matching project
        for component_name in sorted(bda_components):
            # Try tag-based discovery first (in case it works in future)
            arns = self.component_resources.get(component_name, [])
            bda_arns = [a for a in arns if "data-automation-project" in a]

            if bda_arns:
                # Verify it still exists
                try:
                    project = self.bda.get_data_automation_project(projectArn=bda_arns[0])
                    name = project.get("project", {}).get("projectName", component_name)
                    self.ok(self.category, "BDA Project", f"{name} ({component_name})")
                except ClientError as e:
                    self.missing(self.category, "BDA Project", component_name, str(e))
            else:
                # Match by component name pattern in project names
                # Convention: project name contains the category slug
                category_slug = component_name.removeprefix("bda-")
                matched = next(
                    (name for name in project_names if category_slug in name),
                    None,
                )
                if matched:
                    self.ok(self.category, "BDA Project", f"{matched} ({component_name})")
                else:
                    self.missing(
                        self.category,
                        "BDA Project",
                        component_name,
                        f"no project matching '{category_slug}' found in BDA API",
                    )
