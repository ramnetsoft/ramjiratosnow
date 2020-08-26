import copy
import json
import logging
import os
import re

import boto3

from clients.jsd import get_request, update_issue
from clients.snow import create_incident, update_incident

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_param_value(name):
    client = boto3.client("ssm")
    parameter = client.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


def get_request(issue_id):
    request = {
        "requestFieldValues": {}
    }
    resp = get_request(issue_id)
    for field in resp["requestFieldValues"]:
        if field["fieldId"] in (
                "issueId", "issueKey", "requestTypeId", "serviceDeskId"):
            request[field["fieldId"]] = field["value"]
        if field["fieldId"] in ("summary", "description"):
            request["requestFieldValues"][field["fieldId"]] = field["value"]
    return request


def validate_priority(value):
    error = None
    if not value:
        error = "`priority` is empty"
    else:
        if isinstance(value, dict):
            priority_name = value.get("name")
        else:
            error = "`priority` is not a dictionary"
        if not error:
            result = re.match('^Severity [1-5]{1}$', priority_name)
            if not result:
                error = "`priority` is not valid: {}".format(priority_name)
    return error


def validate_summary(value):
    error = None
    if not value:
        error = "`summary` is empty"
    return error


def validate_description(value):
    error = None
    if not value:
        error = "`description` is empty"
    return error


def validate_comment(value):
    error = None
    if not value:
        error = "`comment` is empty"
    return error


allowed_fields = {
    "priority": validate_priority,
    "summary": validate_summary,
    "description": validate_description,
}


def validate_body(body, extra_fields=None, all_fields=True):
    all_allowed_fields = copy.copy(allowed_fields)
    if extra_fields:
        all_allowed_fields.update(extra_fields)
    error = None
    fields_to_validate = []
    if not body:
        error = "`body` is absent or empty: {}".format(body)
    body_fields = body.get("fields", {})
    if not error:
        if not body_fields:
            error = "`fields` is absent or empty: {}".format(body_fields)
    if not error:
        if all_fields:
            fields_to_validate = all_allowed_fields.keys()
        else:
            fields_to_validate = body_fields.keys()
    logger.debug("field to validate is %s", fields_to_validate)
    logger.debug("all_allowed_fields is %s", all_allowed_fields)

    if not error:
        for field in fields_to_validate:
            if error:
                break
            if field in all_allowed_fields:
                error = all_allowed_fields[field](body_fields.get(field))
    resp = {
        "ok": not error,
    }
    if error:
        resp["error"] = error
        logger.error(error)
    return 400 if error else 200, resp


def post_mapping(body):
    fields = body.get("fields", {})
    impact = "3 - Medium"
    urgency = "3 - Medium"
    if fields.get("priority", {}).get("name") in ("Severity 4", "Severity 5"):
        urgency = "4 - Low"
    incident = {
        "callingSystem": "FINEOS-SERVICE-DESK",
        "state": "Active",
        "reportedSource": "FINEOS",
        "category": "Application",
        "subCategory": "Failure",
        "configurationItem": "11835",
        "impact": impact,
        "urgency": urgency,
        "contactType": "Vendor referral",
        "caller": "FINEOS SERVICE DESK",
        "callerNumber": "1-899-898989",
        "shortDescription": fields.get("summary"),
        "description": fields.get("description", ""),
        "assignedTo": "",
        "vendorTicketNumber": body.get("key"),
    }
    return incident


def put_mapping(body):
    incident = {
        "callingSystem": "FINEOS-SERVICE-DESK",
    }
    fields = body.get("fields", {})
    priority = fields.get("priority", {})
    if priority:
        impact = "3 - Medium"
        urgency = "3 - Medium"
        if priority.get("name") in ("Severity 4", "Severity 5"):
            urgency = "4 - Low"
        incident["impact"] = impact
        incident["urgency"] = urgency
    if fields.get("summary"):
        incident["shortDescription"] = fields.get("summary")
    if fields.get("description"):
        incident["description"] = fields.get("description", "")
    if fields.get("comment"):
        incident["workNotes"] = fields.get("comment", "")
    return incident


def create_snow_incident(body):
    logger.debug("Creating a SNOW incident: %s", body)
    resp = create_incident(body)
    logger.debug("SNOW response: %s", resp)
    return resp["number"]


def update_snow_incident(incident_id, body):
    logger.debug("Updating a SNOW incident: [%s] %s", incident_id, body)
    resp = update_incident(incident_id, body)
    logger.debug("SNOW response: %s", resp)


def update_jsd_request(issue_id, snow_incident_number):
    data = {
        "fields": {},
    }
    custom_field_id = get_param_value(
        os.environ.get(
            "JIRA_CUSTOMER_REF_NO_FIELD_ID"))
    data["fields"][custom_field_id] = str(snow_incident_number)
    update_issue(issue_id, data)


def put_request_handler(incident_id, body):
    logger.debug("PUT HTTP request received, validating body: %s", body)

    # Validation
    extra_fields = {
        "comment": validate_comment,
    }
    status, resp = validate_body(
        body, extra_fields=extra_fields, all_fields=False)
    if status != 200:
        logger.debug("Body validation failed: %s", resp["error"])
        return status, resp
    else:
        logger.debug("Body validation passed")

    # Mapping
    body = put_mapping(body)
    logger.debug("PUT body after mapping: %s", json.dumps(body))

    # Updating SNOW incident
    update_snow_incident(incident_id, body)

    return status, resp


def post_request_handler(body):
    logger.debug("POST HTTP request received, validating body: %s", body)

    # Validation
    status, resp = validate_body(body)
    if status != 200:
        logger.debug("Body validation failed: %s", resp["error"])
        return status, resp
    else:
        logger.debug("Body validation passed")

    # Mapping
    body = post_mapping(body)
    logger.debug("POST body after mapping: %s", json.dumps(body))

    # Creating a SNOW incident
    incident_number = create_snow_incident(body)
    logger.debug("SNOW incident created: %s", incident_number)

    # Update JSD incident
    update_jsd_request(body["vendorTicketNumber"], incident_number)

    return status, {
        "number": incident_number,
    }


def validate_event(event):
    body = None
    error = None

    headers = event.get("headers", {})
    logger.debug("Headers: %s", json.dumps(headers))

    content_type_name = "content-type"
    content_type_value = None
    for name, value in headers.items():
        if name.lower() == content_type_name:
            content_type_value = value
            break

    status = 200
    httpMethod = event.get("httpMethod")
    if content_type_value.lower() != "application/json":
        status = 415
        error = "Unsupported Media Type: {}".format(content_type_value)
    elif httpMethod not in ("POST", "PUT"):
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
    print("Event: {}".format(json.dumps(event)))
    logger.debug("Event: %s", json.dumps(event))
    logger.info("HTTP request received, validating...")
    status, resp, body = validate_event(event)
    if resp["ok"]:
        method = event.get("httpMethod")
        if method == "POST":
            status, resp = post_request_handler(body)
        elif method == "PUT":
            incident_id = event.get("pathParameters", {}).get("incidentId")
            status, resp = put_request_handler(incident_id, body)
    return {
        "isBase64Encoded": False,
        "statusCode": status,
        "headers": {},
        "multiValueHeaders": {},
        "body": json.dumps(resp),
    }
