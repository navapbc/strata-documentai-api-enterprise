"""Tag-based AWS resource discovery using the Resource Groups Tagging API."""

from collections import defaultdict

from .constants import Tag


def discover_resources(
    session,
    project: str,
    stage: str,
) -> dict[str, list[str]]:
    """Discover all resources matching project + stage tags, grouped by component.

    Returns a dict mapping component tag values to lists of resource ARNs.
    Resources without a component tag are grouped under Tag.UNTAGGED.
    """
    client = session.client("resourcegroupstaggingapi")

    tag_filters = [
        {"Key": "project", "Values": [project]},
        {"Key": "stage", "Values": [stage]},
    ]

    resources: dict[str, list[str]] = defaultdict(list)
    pagination_token = ""

    while True:
        kwargs: dict = {"TagFilters": tag_filters, "ResourcesPerPage": 100}
        if pagination_token:
            kwargs["PaginationToken"] = pagination_token

        resp = client.get_resources(**kwargs)

        for item in resp.get("ResourceTagMappingList", []):
            arn = item["ResourceARN"]
            tags = {t["Key"]: t["Value"] for t in item.get("Tags", [])}
            component = tags.get("component", Tag.UNTAGGED)
            resources[component].append(arn)

        pagination_token = resp.get("PaginationToken", "")
        if not pagination_token:
            break

    return dict(resources)


def extract_name_from_arn(arn: str) -> str:
    """Extract the resource name/id from an ARN.

    ARN format: arn:partition:service:region:account:resource
    The resource segment varies by service.
    """
    parts = arn.split(":")
    service = parts[2]

    # S3: arn:aws:s3:::bucket-name
    if service == "s3":
        return parts[5]

    # SQS: arn:aws:sqs:region:acct:queue-name
    if service == "sqs":
        return parts[5]

    # Lambda: arn:aws:lambda:region:acct:function:function-name
    if service == "lambda":
        if len(parts) > 6:
            return parts[6]
        return parts[5]

    # API Gateway: arn:aws:apigateway:region::/apis/api-id
    if service == "apigateway":
        resource = parts[5]  # /apis/api-id or /apis/id/stages/name
        segments = resource.strip("/").split("/")
        if len(segments) >= 2:
            return segments[1]  # the api-id
        return resource

    # SSM: arn:aws:ssm:region:acct:parameter/path/to/param
    if service == "ssm":
        resource = parts[5]
        if resource.startswith("parameter"):
            return resource[len("parameter") :]
        return resource

    # Cognito: arn:aws:cognito-idp:region:acct:userpool/pool-id
    if service == "cognito-idp":
        resource = parts[5]
        if "/" in resource:
            return resource.split("/", 1)[1]
        return resource

    # DynamoDB: arn:aws:dynamodb:region:acct:table/table-name
    # ECR: arn:aws:ecr:region:acct:repository/repo-name
    # Glue: arn:aws:glue:region:acct:database/db-name
    # Athena: arn:aws:athena:region:acct:workgroup/wg-name
    # KMS: arn:aws:kms:region:acct:key/key-id
    resource = parts[5] if len(parts) > 5 else ""
    if "/" in resource:
        return resource.split("/", 1)[1]

    return resource


def filter_arns_by_service(arns: list[str], service: str) -> list[str]:
    """Filter a list of ARNs to only those belonging to a specific AWS service."""
    return [arn for arn in arns if arn.split(":")[2] == service]
