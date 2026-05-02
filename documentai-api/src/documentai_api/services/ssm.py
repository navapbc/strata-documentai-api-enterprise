"""SSM Parameter Store service methods."""

from documentai_api.utils.aws_client_factory import AWSClientFactory


def get_parameter(name: str) -> str:
    """Get SSM parameter value."""
    response = AWSClientFactory.get_ssm_client().get_parameter(Name=name)
    return response["Parameter"]["Value"]
