from documentai_api.models.base import BaseApiResponse


class HealthResponse(BaseApiResponse):
    message: str


class ConfigResponse(BaseApiResponse):
    api_url: str
    version: str
    image_tag: str | None
    environment: str
    endpoints: dict[str, str]
    supported_file_types: list[str]
