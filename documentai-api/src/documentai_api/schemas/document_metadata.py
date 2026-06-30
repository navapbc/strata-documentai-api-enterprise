class DocumentMetadata:
    # core fields
    FILE_NAME = "fileName"
    ORIGINAL_FILE_NAME = "originalFileName"
    USER_PROVIDED_DOCUMENT_CATEGORY = "userProvidedDocumentCategory"
    PROCESS_STATUS = "processStatus"
    DELETION_TYPE = "deletionType"  # "soft" | "hard" once a record is DELETED
    BDA_INVOCATION_ARN = "bdaInvocationArn"
    BDA_INVOCATION_ID = "bdaInvocationId"
    BDA_PROJECT_ARN_USED = "bdaProjectArn"
    BDA_OUTPUT_S3_URI = "bdaOutputS3Uri"
    ERROR_MESSAGE = "errorMessage"
    RESPONSE_JSON = "responseJson"
    RESPONSE_CODE = "responseCode"
    PROCESSED_DATE = "processedDate"
    JOB_ID = "jobId"
    TRACE_ID = "traceId"
    BATCH_ID = "batchId"
    EXTERNAL_DOCUMENT_ID = "externalDocumentId"
    EXTERNAL_SYSTEM_ID = "externalSystemId"
    AI_CONSENT_FLAG = "aiConsentFlag"
    UPLOAD_METHOD = "uploadMethod"
    TENANT_ID = "tenantId"
    API_KEY_NAME = "apiKeyName"
    IS_DEMO = "isDemo"
    V1_API_RESPONSE_JSON = "v1ApiResponseJson"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    TIME_TO_LIVE = "ttl"

    # preclassification fields
    PRECLASSIFICATION_CATEGORY = "preclassificationCategory"
    PRECLASSIFICATION_CONFIDENCE = "preclassificationConfidence"
    PRECLASSIFICATION_INPUT_TOKENS = "preclassificationInputTokens"
    PRECLASSIFICATION_OUTPUT_TOKENS = "preclassificationOutputTokens"
    PRECLASSIFICATION_DURATION_SECONDS = "preclassificationDurationSeconds"
    PRECLASSIFICATION_MODEL_ID = "preclassificationModelId"

    # image optimization fields
    CROP_BOUNDING_BOX = "cropBoundingBox"
    CROP_RETAINED_PERCENTAGE = "cropRetainedPercentage"
    CROP_DURATION_SECONDS = "cropDurationSeconds"
    CROP_INPUT_TOKENS = "cropInputTokens"
    CROP_OUTPUT_TOKENS = "cropOutputTokens"
    CROP_MODEL_ID = "cropModelId"
    GRAYSCALE_CONVERSION = "grayscaleConversion"
    PROCESSED_FILE_SIZE_BYTES = "processedFileSizeBytes"

    # performance tracking
    DOCUMENT_PROCESSOR_STARTED_AT = "documentProcessorStartedAt"
    # TODO: Rename BDA_STARTED_AT/BDA_COMPLETED_AT/BDA_PROCESSING_TIME_SECONDS to
    # generic extract timing fields (extractStartedAt, extractCompletedAt, etc.)
    # now that Textract also uses them. EXTRACT_METHOD disambiguates the source.
    BDA_STARTED_AT = "bdaStartedAt"
    BDA_COMPLETED_AT = "bdaCompletedAt"
    EXTRACTION_STARTED_AT = "extractionStartedAt"
    EXTRACTION_COMPLETED_AT = "extractionCompletedAt"
    EXTRACTION_PROCESSING_TIME_SECONDS = "extractionProcessingTimeSeconds"
    EXTRACTION_WAIT_TIME_SECONDS = "extractionWaitTimeSeconds"
    RESULT_PROCESSOR_STARTED_AT = "resultProcessorStartedAt"
    TOTAL_PROCESSING_TIME_SECONDS = "totalProcessingTimeSeconds"
    BDA_PROCESSING_TIME_SECONDS = "bdaProcessingTimeSeconds"  # time bda took to process the file
    BDA_WAIT_TIME_SECONDS = "bdaWaitTimeSeconds"  # time between s3 write and bda invocation
    IS_DOCUMENT_PROCESSOR_COLD_START = "isDocumentProcessorColdStart"
    PAGES_SENT_TO_BDA = "pagesSentToBda"

    # file metadata
    FILE_SIZE_BYTES = "fileSizeBytes"
    CONTENT_TYPE = "contentType"
    PAGES_DETECTED = "pagesDetected"
    IS_DOCUMENT_BLURRY = "isDocumentBlurry"
    IS_PASSWORD_PROTECTED = "isPasswordProtected"
    DOCUMENT_METRICS_RAW = "documentMetricsRaw"
    DOCUMENT_METRICS_NORMALIZED = "documentMetricsNormalized"
    OVERALL_BLUR_SCORE = "overallBlurScore"

    # operational intelligence
    ADDITIONAL_INFO = "additionalInfo"
    RETRY_COUNT = "retryCount"
    FIELD_CONFIDENCE_SCORES = "fieldConfidenceScores"

    # bda processing info
    BDA_REGION_USED = "bdaRegionUsed"
    BDA_MATCHED_BLUEPRINT_NAME = "matchedBlueprintName"
    BDA_MATCHED_BLUEPRINT_CONFIDENCE = "matchedBlueprintConfidence"
    BDA_MATCHED_DOCUMENT_CLASS = "bdaMatchedDocumentClass"

    # list of blueprint fields that were expected but did not have any data extracted
    BDA_MATCHED_BLUEPRINT_FIELD_EMPTY_LIST = "matchedBlueprintFieldEmptyList"
    BDA_MATCHED_BLUEPRINT_FIELD_BELOW_THRESHOLD_LIST = "matchedBlueprintFieldBelowThresholdList"
    BDA_MATCHED_BLUEPRINT_FIELD_COUNT = "matchedBlueprintFieldCount"
    BDA_MATCHED_BLUEPRINT_FIELD_COUNT_NOT_EMPTY = "matchedBlueprintFieldCountNotEmpty"
    BDA_MATCHED_BLUEPRINT_FIELD_NOT_EMPTY_AVG_CONFIDENCE = (
        "matchedBlueprintFieldNotEmptyAvgConfidence"
    )
    BELOW_EXTRACTION_CONFIDENCE_FLOOR = "belowExtractionConfidenceFloor"

    # extraction method
    EXTRACT_METHOD = "extractMethod"
