import os
from enum import Enum

STAGE = os.environ['Stage']

class Parameters(Enum):
    # Jira parameters
    JIRA_HOST = f"/{STAGE}/JiraHost"
    JIRA_USER_ID = f"/{STAGE}/JiraUserId"
    JIRA_APP_PASSWORD = f"/{STAGE}/JiraAppPassword"
    JIRA_CUSTOMER_REF_NO_FIELD_ID = f"/{STAGE}/JiraCustomerRefNoFieldId"
    JIRA_ACTUAL_RESULT_FIELD_ID = f"/{STAGE}/JiraActualResultFieldId"
    JIRA_EXPECTED_RESULT_FIELD_ID = f"/{STAGE}/JiraExpectedResultFieldId"
    JIRA_ENVIRONMENT_FIELD_ID = f"/{STAGE}/JiraEnvironmentFieldId"
    JIRA_SERVICE_DESK_ID = f"/{STAGE}/JiraServiceDeskId"
    JIRA_REQUEST_TYPE_ID = f"/{STAGE}/JiraRequestTypeId"
    
    # Snow parameters
    SNOW_HOST = f"/{STAGE}/SnowHost"
    SNOW_CLIENT_ID = f"/{STAGE}/SnowClientId"
    SNOW_BASIC_AUTH = f"/{STAGE}/BasicAuth"
    SNOW_AUTH_USER_NAME = f"/{STAGE}/SnowAuthUserName"
    SNOW_AUTH_PASSWORD = f"/{STAGE}/SnowAuthPassword"
    SNOW_AUTH_URL = f"/{STAGE}/SnowAuthUrl"
    SNOW_API_TOKEN_SSM_2 = f"/{STAGE}/SNOW_API_TOKEN_KEY_2"
    SNOW_API_TOKEN_SSM_1 = f"/{STAGE}/SNOW_API_TOKEN_KEY_1"

    # S3 parameters
    S3_PRESIGNED_URL_TTL = f"/{STAGE}/S3PresignUrlTtl"
