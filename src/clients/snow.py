"""
The ServiceNow REST API client.
"""
import json
import logging
import os
import time

import boto3
import requests
from settings import Parameters, get_log_level


class ClientError(Exception):
    pass


ssm_client = boto3.client("ssm")
logger = logging.getLogger()
logger.setLevel(get_log_level())


def get_param_value(name):
    parameter = ssm_client.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


def put_param_value(name, value, param_type='SecureString'):
    ssm_client.put_parameter(
        Name=name, Value=value, Type=param_type, Overwrite=True)


# SNOW REST API URL
SNOW_API_URL = get_param_value(Parameters.SNOW_HOST.value)

# A parameter for storing token information (access token, expires and
# type):
SNOW_API_TOKEN_SSM_PARAM_NAME = Parameters.SNOW_API_TOKEN_SSM_2.value


def get_client_id():
    return get_param_value(Parameters.SNOW_CLIENT_ID.value)


def get_token():
    param_name = SNOW_API_TOKEN_SSM_PARAM_NAME
    try:
        token = get_param_value(param_name)
    except ssm_client.exceptions.ParameterNotFound:
        logger.info("Parameter not found: {}".format(param_name))
        return None
    else:
        if token:
            try:
                return json.loads(token)
            except (json.decoder.JSONDecodeError, TypeError) as e:
                logger.exception("JSON decode error: %s", e)


def store_token(token):
    put_param_value(SNOW_API_TOKEN_SSM_PARAM_NAME, json.dumps(token))


def request_token():
    auth_url = get_param_value(Parameters.SNOW_AUTH_URL.value)
    auth = (
        get_param_value(Parameters.SNOW_AUTH_USER_NAME.value),
        get_param_value(Parameters.SNOW_AUTH_PASSWORD.value),
    )
    headers = {
        "X-IBM-Client-Id": get_client_id(),
    }
    resp = requests.get(auth_url, auth=auth, headers=headers)
    if resp.ok:
        return resp.json()
    else:
        resp.raise_for_status()


def mk_session():
    token = get_token()
    logger.debug("Token: %s", token)
    if not token:
        token = request_token()
        store_token(token)
    elif (int(token["expires"]) - round(time.time())) < 30:
        # If there is 30 seconds (and less) left to the token
        # expiration time we consider that the token is almost expired
        # and requesting another one.
        token = request_token()
        store_token(token)
    session = requests.Session()
    session.headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-IBM-Client-Id": get_client_id(),
        "Authorization": f"{token['token_type']} {token['access_token']}",
    }
    return session


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


def snow_get_request(uri):
    session = mk_session()
    response = session.get(f"{SNOW_API_URL}{uri}")
    raise_not_ok_exception(response)
    return response.json()


def snow_post_request(uri, data):
    session = mk_session()
    response = session.post(f"{SNOW_API_URL}{uri}", json=data)
    raise_not_ok_exception(response)
    if response.text:
        return response.json()


def snow_put_request(uri, data):
    session = mk_session()
    response = session.put(f"{SNOW_API_URL}{uri}", json=data)
    raise_not_ok_exception(response)
    if response.text:
        return response.json()


def create_incident(body):
    return snow_post_request("/itsm-incident/process/incidents", body)


def update_incident(incident_id, body):
    return snow_put_request(f"/itsm-incident/process/incidents/{incident_id}", body)


def get_incidents():
    return snow_get_request("/itsm-incident/process/incidents")


def get_incident(incident_id):
    return snow_get_request(f"/itsm-incident/process/incidents/{incident_id}")
