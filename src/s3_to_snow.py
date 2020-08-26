import json
import boto3
import os
import sys
import requests
import calendar
import time
import base64
from log_cfg import logger
from urllib.parse import unquote_plus
from aws.ssm import get_ssm_value




s3_client = boto3.client('s3')
ssm = boto3.client('ssm')

SnowApiEndpointId = os.environ['SnowApiEndpointId']
SnowClientId = os.environ['SnowClientId']
SnowBasicAuthId = os.environ['SnowBasicAuthId']

# Service now configuration
SNOW_AUTH_ENDPOINT = None
SNOW_ATTACHMENT_ENDPOINT = None
SNOW_X_IBM_CLIENT_ID = None
SNOW_BASIC_AUTH = None


SSM_API_TOKEN_KEY='SNOW_API_TOKEN_KEY'

def validate_environment():
    error = ''
    snow_endpoint = None
    global SNOW_X_IBM_CLIENT_ID, SNOW_BASIC_AUTH, SNOW_AUTH_ENDPOINT, SNOW_ATTACHMENT_ENDPOINT
    err, snow_endpoint = get_ssm_value(key=SnowApiEndpointId)
    error += err
    err, SNOW_X_IBM_CLIENT_ID = get_ssm_value(key=SnowClientId)
    error += err
    err, SNOW_BASIC_AUTH = get_ssm_value(key=SnowBasicAuthId)
    error += err
    SNOW_AUTH_ENDPOINT = f'{snow_endpoint}/authorization/token'
    SNOW_ATTACHMENT_ENDPOINT = f'{snow_endpoint}/itsm-incident/process/incidents'
    return error

def get_api_token():
    parameter = None
    error, parameter = get_ssm_value(key=SSM_API_TOKEN_KEY, with_decryption=True)    
    if error:
        data = request_access_token()
        return data['access_token']
    else:
        data = json.loads(parameter)
        if check_if_token_is_valid(data['expires']) == False:
            data = request_access_token()
        return data['access_token']


def request_access_token():
    headers = {
        "X-IBM-Client-ID" : SNOW_X_IBM_CLIENT_ID,
        "Authorization" : f'Basic {SNOW_BASIC_AUTH}'
    }
    res = requests.request(method='GET',url=SNOW_AUTH_ENDPOINT,headers=headers)
    data = json.loads(res.text)
    ssm.put_parameter(Name=SSM_API_TOKEN_KEY,Value=json.dumps(data),Type='SecureString',Overwrite=True)
    return data

def check_if_token_is_valid(exp_time):
    # Check if the token does not expire
    current_ts = calendar.timegm(time.gmtime())
    return int(exp_time) > current_ts

def upload_file_to_snow(download_path, cutomer_ref, file_name):
    logger.debug('Fetch snow api token')
    api_token = get_api_token()
    logger.debug(f'API TOKEN: {api_token}')
    headers = {
        "X-IBM-Client-ID" : SNOW_X_IBM_CLIENT_ID,
        "Authorization" : f'Bearer {api_token}'
    }
    logger.debug(f'Starting uploading to snow')
    with open(download_path, 'rb') as out:
        encoded_string = base64.b64encode(out.read())
        payload = json.dumps({
                "callingSystem" : "FINEOS-SERVICE-DESK",
                "attachments" : [
                    {
                        "attachment" : encoded_string.decode('utf-8'),
                        "contentType" : "",
                        "fileName" : file_name
                    }
                ]
        })
        logger.debug(payload)
        res = requests.request(method='PUT',url=f'{SNOW_ATTACHMENT_ENDPOINT}/{cutomer_ref}',headers=headers,data=payload,timeout=25)
        logger.debug(f'Upload to SNOW: {res.text}')


def handler(event, context):
    
    logger.debug("Event: %s", json.dumps(event))
    error = validate_environment()
    
    if error:
        logger.error(error)
    else:
        try:
            for record in event['Records']:
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                logger.debug(f'bucket key: {key}')
                customer_ref_key = key.split('/')[0]
                jsd_attachment_id = key.split('/')[1]
                logger.debug(f'CustomerRefNo: {customer_ref_key}')
                tmpkey = key.replace(f'{customer_ref_key}/{jsd_attachment_id}/', '')
                logger.debug(f'filename: {tmpkey}')
                download_path = '/tmp/{}'.format(tmpkey)
                s3_client.download_file(bucket, key, download_path)
                try:
                    upload_file_to_snow(download_path, customer_ref_key, tmpkey)
                except Exception as ex:
                    logger.error(f'Failed:  {str(ex)}')
                finally:
                    logger.debug(f'Deleting s3 object:  {key}')
                    s3_client.delete_object(Bucket=bucket, Key=key)
        except Exception as exc:
            logger.error(f'Failed:  {str(exc)}')

