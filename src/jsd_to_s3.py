import json
import boto3
import os
import sys
import requests
from log_cfg import logger
from urllib.parse import unquote_plus
from requests.auth import HTTPBasicAuth
from aws.ssm import get_ssm_value

s3_client = boto3.client('s3')


JiraServerId = os.environ['JiraServerId']
JiraUserId = os.environ['JiraUserId']
JiraPasswordId = os.environ['JiraPasswordId']
S3_JSD_BUCKET = os.environ['S3_JSD_BUCKET']

JIRA_SEVER = None
JIRA_USER = None
JIRA_API_KEY = None


def validate_environment():
    error = ''
    global JIRA_SEVER, JIRA_USER, JIRA_API_KEY
    err, JIRA_SEVER = get_ssm_value(key=JiraServerId)
    error += err
    err, JIRA_USER = get_ssm_value(key=JiraUserId)
    error += err
    err, JIRA_API_KEY = get_ssm_value(key=JiraPasswordId)
    error += err

    resp = {
        "ok": not error,
    }
    
    if error:
        resp["error"] = error
        logger.error(error)
    return 500 if error else 200, resp

def download_file_and_upload_to_s3(file_name,attachment_id,customer_ref_no):
    msg = None
    logger.debug('Uploading attachment to s3 {}'.format(attachment_id))
    try:
        url = f'{JIRA_SEVER}/secure/attachment/{attachment_id}/{file_name}'
        download_path = f'/tmp/{attachment_id}/{file_name}'
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        with open(download_path, 'wb') as out:
            response = requests.get(url, auth=(JIRA_USER, JIRA_API_KEY), stream=True)
            out.write(response.content)
        with open(download_path, 'rb') as data:
            s3_client.upload_fileobj(data, S3_JSD_BUCKET, f'{customer_ref_no}/{attachment_id}/{file_name}')
        msg = f'Uploaded {file_name}'
    except Exception as ex:
        msg = f'Failed to upload {file_name}: {str(ex)}'
    logger.debug(msg)
    return msg

def download_comment_attachments_and_upload_to_s3(issue_key, body,customer_ref_no):
    error = None
    logger.debug('Handling attachments in comment...')

    headers = {
        "Accept" : "application/json"
    }
    resp = {
        "ok": not error,
    }
    try:
        auth = HTTPBasicAuth(JIRA_USER, JIRA_API_KEY)
        response = requests.request(method='GET',url=f'{JIRA_SEVER}/rest/api/3/issue/{issue_key}?fields=attachment',headers=headers,auth=auth)
        
        data = json.loads(response.text)

        attachments = [item for item in data['fields']['attachment'] if item['filename'] in body]
        msgs = []
        if not attachments:
            msgs.append('No attachemnt matched')
        else:
            for attachment in attachments:
                msg = download_file_and_upload_to_s3(attachment['filename'], attachment['id'],customer_ref_no)
                msgs.append(msg)
        resp["info"] = msgs
    except Exception as ex:
        error = f"Something wrong here: {str(ex)}"
    
    if error:
        resp["error"] = error
        logger.error(error)
    return 400 if error else 200, resp

def upload_to_s3(body, customer_ref_no):
    error = None
    attachments = body.get("attachments")

    resp = {
        "ok": not error,
    }
    msgs = []
    if not attachments:
        msgs.append('No attachemnt found')
    else:
        for attachment in attachments:
            msg = download_file_and_upload_to_s3(attachment['fileName'], attachment['attachmentId'],customer_ref_no)
            msgs.append(msg)
    resp["info"] = msgs
    return resp

def validate_body(body):
    error = None
    issue_key = None
    customer_ref_no= None
    if not body:
        error = "`body` is absent or empty: {}".format(body)
    else:
        issue_key = body.get("issueKey")
        customer_ref_no = body.get('customerRefNo')
        if not issue_key:
            error = "`issueKey` is empty"
        elif not customer_ref_no:
            error = "`customerRefNo` is empty"
    resp = {
        "ok": not error,
    }
    if error:
        resp["error"] = error
        logger.error(error)
    return 400 if error else 200, resp, issue_key, customer_ref_no


def validate_event(event):
    error = None
    status = 200
    body = None

    httpMethod = event.get("httpMethod")
    if httpMethod != "POST":
        status = 405
        error = "Method not allowed: {}".format(httpMethod)
    else:
        body = event.get("body")
        try:
            body = json.loads(body)
        except (json.decoder.JSONDecodeError, TypeError):
            status = 400
            error = "`body` is not valid JSON: {}".format(body)

    resp = {
        "ok": not error,
    }

    if error:
        resp["error"] = error
        logger.error(error)
    return status, resp, body

def handler(event, context):
    """
    Upload attachments from JSD to S3
    """
    logger.debug("Event: %s", json.dumps(event))
    logger.info("HTTP request received, validating...")

    status, resp, body = validate_event(event)
    if resp["ok"]:
        status, resp = validate_environment()
        if resp["ok"]:
            status, resp, issue_key, customer_ref_no = validate_body(body)
            if resp["ok"]:
                if 'commentId' in body:
                    status, resp = download_comment_attachments_and_upload_to_s3(issue_key,body['body'],customer_ref_no)
                else:
                    resp = upload_to_s3(body,customer_ref_no)
    return {
        "statusCode": status,
        "body": json.dumps(resp)
    }

