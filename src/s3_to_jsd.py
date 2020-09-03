import json
import boto3
import os
import sys
from log_cfg import logger
from urllib.parse import unquote_plus
from aws.ssm import get_ssm_value
from settings import Parameters
from clients import jsd


s3_client = boto3.client('s3')

JIRA_SEVER = None
JIRA_USER = None
JIRA_API_KEY = None

def validate_environment():
    error = ''
    global JIRA_SEVER, JIRA_USER, JIRA_API_KEY

    err, JIRA_SEVER = get_ssm_value(key=Parameters.JIRA_HOST.value)
    error += err
    err, JIRA_USER = get_ssm_value(key=Parameters.JIRA_USER_ID.value)
    error += err
    err, JIRA_API_KEY = get_ssm_value(key=Parameters.JIRA_APP_PASSWORD.value)
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
                
                cr = jsd.get_request(issue_key)
                # Upload file as temporary attachment
                temp_attachment_id = jsd.attach_temporary_file(cr['serviceDeskId'], download_path)
                logger.debug('Temporary Attachment Id: {}'.format(temp_attachment_id))
                # Set attachment as public for customer
                response = jsd.add_attachment(issue_key,temp_attachment_id,public=True, comment=None)
                logger.debug('Set attachment to be public for customer: {}'.format(response))
            except Exception as ex:
                logger.error('Upload attachments to Jira failed: {}'.format(str(ex)))
            finally:
                s3_client.delete_object(Bucket=bucket, Key=key)