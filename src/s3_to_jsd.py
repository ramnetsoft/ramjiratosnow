import json
import boto3
import os
import sys
from log_cfg import logger
from urllib.parse import unquote_plus
from atlassian import ServiceDesk
from aws.ssm import get_ssm_value


s3_client = boto3.client('s3')


JiraServerId = os.environ['JiraServerId']
JiraUserId = os.environ['JiraUserId']
JiraPasswordId = os.environ['JiraPasswordId']

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
    logger.debug(f'JIRA_SEVER: {JIRA_SEVER} {JIRA_USER} {JIRA_API_KEY}')
    return error

def handler(event, context):
    
    logger.debug("Event: %s", json.dumps(event))

    error = validate_environment()

    if error:
        logger.error(error)
    else:
        logger.debug(f'JIRA_SEVER: {JIRA_SEVER} {JIRA_USER} {JIRA_API_KEY}')
        temporary_attachment_headers = {
            "Accept": "application/json",
            "X-Atlassian-Token": "nocheck",
            "X-ExperimentalApi": "opt-in",
            "Origin": JIRA_SEVER
        }

        add_attachment_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",     
            "Origin": JIRA_SEVER
        }
        jsd = ServiceDesk(url=JIRA_SEVER, username=JIRA_USER, password=JIRA_API_KEY)
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            logger.debug('bucket key: {}'.format(key))
            issue_key= key.split('/')[0]
            logger.debug('issue_key: {}'.format(issue_key))
            tmpkey = key.replace(f'{issue_key}/', '')
            download_path = '/tmp/{}'.format(tmpkey)
            s3_client.download_file(bucket, key, download_path)
            try:
                
                cr = jsd.get_customer_request(issue_key)
                # Upload file as temporary attachment
                jsd.experimental_headers = temporary_attachment_headers
                temp_attachment_id = jsd.attach_temporary_file(cr['serviceDeskId'], download_path)
                logger.debug('Temporary Attachment Id: {}'.format(temp_attachment_id))
                # Set attachment as public for customer
                jsd.experimental_headers = add_attachment_headers
                response = jsd.add_attachment(issue_key,temp_attachment_id,public=True, comment=None)
                logger.debug('Set attachment to be public for customer: {}'.format(response))
            except Exception as ex:
                logger.error('Upload attachments to Jira failed: {}'.format(str(ex)))
            finally:
                s3_client.delete_object(Bucket=bucket, Key=key)