"""Infrastructure validation constants."""


class AwsErrorCode:
    REPOSITORY_NOT_FOUND = "RepositoryNotFoundException"
    RESOURCE_NOT_FOUND = "ResourceNotFoundException"
    ENTITY_NOT_FOUND = "EntityNotFoundException"
    NO_SUCH_ENTITY = "NoSuchEntity"
    PARAMETER_NOT_FOUND = "ParameterNotFound"
    SQS_NON_EXISTENT_QUEUE = "AWS.SimpleQueueService.NonExistentQueue"
