"""SSM Parameter Store service methods."""

from documentai_api.services.aws_client_factory import AWSClientFactory


def get_parameter(name: str) -> str:
    """Get SSM parameter value."""
    response = AWSClientFactory.get_ssm_client().get_parameter(Name=name)
    return response["Parameter"]["Value"]


def put_parameter(name: str, value: str) -> None:
    """Set SSM parameter value (String type, overwrite)."""
    AWSClientFactory.get_ssm_client().put_parameter(
        Name=name, Value=value, Type="String", Overwrite=True
    )
