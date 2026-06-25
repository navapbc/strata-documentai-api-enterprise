"""Bedrock Data Automation project validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator


class BedrockValidator(BaseValidator):
    def check_bedrock(self):
        cat = "Bedrock"

        # BDA projects are tagged with component=bda-{category}
        # Exclude worker Lambdas that also start with "bda-" (e.g. bda-result-processor)
        bda_components = [
            k for k in self.component_resources
            if k.startswith("bda-") and k != "bda-result-processor"
        ]

        if not bda_components:
            self.missing(cat, "Bedrock DA Projects", "No bda-* components discovered")
            return

        # List deployed projects for cross-reference
        try:
            existing = set()
            next_token = None
            while True:
                kwargs = {}
                if next_token:
                    kwargs["nextToken"] = next_token
                resp = self.bda.list_data_automation_projects(**kwargs)
                existing.update(p["projectName"] for p in resp.get("projects", []))
                next_token = resp.get("nextToken")
                if not next_token:
                    break
        except ClientError as e:
            for comp in bda_components:
                self.missing(cat, "Bedrock DA Project", f"component={comp}", str(e))
            return

        # For each discovered bda component, verify the project exists
        for comp in sorted(bda_components):
            arns = self.component_resources[comp]
            # Find the project ARN (contains "data-automation-project")
            project_arns = [a for a in arns if "data-automation-project" in a]
            if project_arns:
                # Extract project name by checking against listed projects
                project_id = project_arns[0].split("/")[-1]
                # We can verify it exists by checking if it's in our list
                # The project name isn't in the ARN, so check via API
                try:
                    project = self.bda.get_data_automation_project(
                        projectArn=project_arns[0]
                    )
                    project_name = project.get("project", {}).get("projectName", project_id)
                    self.ok(cat, "Bedrock DA Project", f"{project_name} ({comp})")
                except ClientError as e:
                    self.missing(cat, "Bedrock DA Project", f"{comp} ({project_arns[0]})", str(e))
            else:
                self.missing(cat, "Bedrock DA Project", f"component={comp} (no project ARN)")
