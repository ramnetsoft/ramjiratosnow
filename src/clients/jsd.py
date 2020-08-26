"""
The Jira Service Desk Cloud REST API client.
"""
import os
import boto3
import requests
from requests.auth import HTTPBasicAuth


class ClientError(Exception):
    pass


def get_param_value(name):
    client = boto3.client("ssm")
    parameter = client.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


JIRA_USER_EMAIL_SSM_PARAM_NAME = os.environ.get("JIRA_USER")
JIRA_API_TOKEN_SSM_PARAM_NAME = os.environ.get("JIRA_PASSWORD")
JIRA_API_URL_SSM_PARAM_NAME = os.environ.get("JIRA_SERVER")
JIRA_SERVICE_DESK_ID_PARAM_NAME = os.environ.get("JIRA_SERVICE_DESK_ID")

JIRA_API_URL = get_param_value(JIRA_API_URL_SSM_PARAM_NAME)
JIRA_SERVICE_DESK_ID = get_param_value(JIRA_SERVICE_DESK_ID_PARAM_NAME)

session = requests.Session()
session.auth = HTTPBasicAuth(
    get_param_value(JIRA_USER_EMAIL_SSM_PARAM_NAME),
    get_param_value(JIRA_API_TOKEN_SSM_PARAM_NAME)
)
session.headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def raise_not_ok_exception(response):
    """
    Raise an exception if `response.ok` equals to `False`.
    """
    if not response.ok:
        if response.status_code in (400,):
            # Raise an exception this way in order to provide more
            # details (located in `response.text`) than
            # `raise_for_status` provides.
            raise ClientError(response.text)
        else:
            response.raise_for_status()


def sda_get_request(uri):
    response = session.get(f"{JIRA_API_URL}/rest/servicedeskapi{uri}")
    raise_not_ok_exception(response)
    return response.json()


def sda_post_request(uri, data):
    response = session.post(f"{JIRA_API_URL}/rest/servicedeskapi{uri}", json=data)
    raise_not_ok_exception(response)
    if response.text:
        return response.json()


def get_service_desks():
    return sda_get_request('/servicedesk')


def get_request_types():
    return sda_get_request(
        '/rest/servicedesk/{}/requesttype'.format(JIRA_SERVICE_DESK_ID))


def create_request(body):
    return sda_post_request('/request', body)


def update_issue(issue_id, data):
    url = f'{JIRA_API_URL}/rest/api/latest/issue/{issue_id}'
    response = session.put(url, json=data)
    raise_not_ok_exception(response)
    if response.text:
        return response.json()


def get_request(issueIdOrKey):
    return sda_get_request(f'/request/{issueIdOrKey}')


def create_comment(issueIdOrKey, comment, public=True):
    body = {
        "body": comment,
        "public": public,
    }
    return sda_post_request(f'/request/{issueIdOrKey}/comment', body)
