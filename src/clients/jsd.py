"""
The Jira Service Desk Cloud REST API client.
"""
import os
import boto3
import requests
from requests.auth import HTTPBasicAuth
from settings import Parameters

class ClientError(Exception):
    pass


def get_param_value(name):
    client = boto3.client("ssm")
    parameter = client.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


JIRA_API_URL = get_param_value(Parameters.JIRA_HOST.value)
JIRA_SERVICE_DESK_ID = get_param_value(Parameters.JIRA_SERVICE_DESK_ID.value)

session = requests.Session()
session.auth = HTTPBasicAuth(
    get_param_value(Parameters.JIRA_USER_ID.value),
    get_param_value(Parameters.JIRA_APP_PASSWORD.value)
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

def attach_temporary_file(service_desk_id, filename):
    """
    Create temporary attachment, which can later be converted into permanent attachment
    :param service_desk_id: str
    :param filename: str
    :return: Temporary Attachment ID
    """
    temporary_attachment_headers = {
            "Accept": "application/json",
            "X-Atlassian-Token": "nocheck",
            "X-ExperimentalApi": "opt-in",
            "Origin": JIRA_API_URL
    }
    url = f'{JIRA_API_URL}/rest/servicedeskapi/servicedesk/{service_desk_id}/attachTemporaryFile'
    
    with open(filename, 'rb') as file:
        session.headers = temporary_attachment_headers
        response = session.post(url=url,
                            files={'file': file})
        raise_not_ok_exception(response)
        temp_attachment_id = response.json()['temporaryAttachments'][0].get('temporaryAttachmentId')

        return temp_attachment_id
def add_attachment(issue_id_or_key, temp_attachment_id, public=True, comment=None):
    """
    Adds temporary attachment to customer request using attach_temporary_file function
    :param issue_id_or_key: str
    :param temp_attachment_id: str, ID from result attach_temporary_file function
    :param public: bool (default is True)
    :param comment: str (default is None)
    :return:
    """
    data = {'temporaryAttachmentIds': [temp_attachment_id],
            'public': public,
            'additionalComment': {'body': comment}}
    url = f'{JIRA_API_URL}/rest/servicedeskapi/request/{issue_id_or_key}/attachment'
    add_attachment_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",     
            "Origin": JIRA_API_URL
    }
    session.headers = add_attachment_headers
    response = session.post(url=url,
                            json=data)
    raise_not_ok_exception(response)
    return response.json()


def create_comment(issueIdOrKey, comment, public=True):
    body = {
        "body": comment,
        "public": public,
    }
    return sda_post_request(f'/request/{issueIdOrKey}/comment', body)
