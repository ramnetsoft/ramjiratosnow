import json
import os
import boto3
from log_cfg import logger
from aws.ssm import get_ssm_value


s3 = boto3.client('s3')


BUCKET = os.environ['S3_BUCKET']
S3PresignUrlTtlId = os.environ['S3PresignUrlTtlId']


def validate_environment():
    error = ''
    s3_presigned_url_ttl = None
    status = 200

    error, s3_presigned_url_ttl = get_ssm_value(key=S3PresignUrlTtlId)
    resp = {
        "ok": not error,
    }
    if error:
        resp["error"] = error
        status = 500
        logger.error(error)
    
    return status, resp, s3_presigned_url_ttl


def validate_event(event):
    error = None
    status = 200

    queries = event.get("queryStringParameters", {})
    logger.debug("Query Parameters: %s", json.dumps(queries))
    httpMethod = event.get("httpMethod")
    if queries is None or 'issue_key' not in queries or 'file_name' not in queries:
        status = 400
        error = "`issue_key` and `file_name` must be defined in querystring"
    elif httpMethod != "GET":
        status = 405
        error = "Method not allowed: {}".format(httpMethod)

    resp = {
        "ok": not error,
    }

    if error:
        resp["error"] = error
        logger.error(error)
    return status, resp, queries

def generate_presigned_url(issue_key, file_name, ttl):
    error = None
    status = 200

    resp = {
        "ok": not error,
    }
    try:
        upload_url = s3.generate_presigned_post(
            Bucket=BUCKET,
            Key=f'{issue_key}/{file_name}',
            ExpiresIn=int(ttl)
        )
        logger.debug('S3 presigned upload URL: {}'.format(upload_url))
        resp["upload_url"] = upload_url
        resp["issue_key"] = issue_key
    except Exception as e:
        logger.error('Could not generate S3 presigned upload URL failed: {}'.format(str(e)))
        error = str(e)
        status = 500

    if error:
        resp["error"] = error
        logger.error(error)
    return status, resp

def handler(event, context):
    """
    Generate S3 presigned url for uploading
    issue_key: issue id or key on JSD and must be on query string
    file_name: file name will put on S3 bucket and must be on query string
    """
    logger.debug("Event: %s", json.dumps(event))
    logger.info("HTTP request received, validating...")
    status, resp, queries = validate_event(event)
    if resp["ok"]:
        status, resp, s3_presigned_url_ttl = validate_environment()
        if resp["ok"]:
            status, resp = generate_presigned_url(queries['issue_key'], queries['file_name'], s3_presigned_url_ttl)

    return {
        "statusCode": status,
        "body": json.dumps(resp)
    }