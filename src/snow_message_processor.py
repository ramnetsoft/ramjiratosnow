import copy
import json
import logging
import os

import boto3

from clients.jsd import create_comment, create_request, get_request
from settings import Parameters


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_jirarequest(incident_id):
    request = {
        "requestFieldValues": {},
        "currentStatus": {},
    }
    resp = get_request(incident_id)
    for field in resp["requestFieldValues"]:
        if field["fieldId"] in (
                "issueId", "issueKey", "requestTypeId", "serviceDeskId"):
            request[field["fieldId"]] = field["value"]
        if field["fieldId"] in ("summary", "description", "priority"):
            request["requestFieldValues"][field["fieldId"]] = field["value"]
    request["currentStatus"] = resp.get("currentStatus", {})
    return request


def get_param_value(name):
    client = boto3.client("ssm")
    parameter = client.get_parameter(Name=name, WithDecryption=True)
    return parameter["Parameter"]["Value"]


def validate_snow_incident_number(value):
    error = None
    if not value:
        error = "`snow_incident_number` is empty"
    else:
        value = str(value)
    if not error and not value.isalnum():
        error = "Invalid `snow_incident_number`: {}".format(value)
    return error


def validate_reportedby(value):
    error = None
    if not value:
        error = "`reportedby` is empty"
    return error


def validate_priority(value):
    error = None
    if not value:
        error = "`priority` is empty"
    else:
        try:
            int(value)
        except ValueError:
            error = "`priority` is not numeric value"
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


def validate_status(value):
    error = None
    if not value:
        error = "`status` is empty"
    return error


def validate_comment(value):
    error = None
    if not value:
        error = "`comment` is empty"
    return error


allowed_fields = {
    "snow_incident_number": validate_snow_incident_number,
    "reportedby": validate_reportedby,
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
    if not error:
        if all_fields:
            fields_to_validate = all_allowed_fields.keys()
        else:
            fields_to_validate = body.keys()
    if not error:
        for field in fields_to_validate:
            if error:
                break
            error = all_allowed_fields[field](body.get(field))
    resp = {
        "ok": not error,
    }
    if error:
        resp["error"] = error
        logger.error(error)
    return 400 if error else 200, resp


def post_mapping(fields):
    custom_field_id = get_param_value(Parameters.JIRA_CUSTOMER_REF_NO_FIELD_ID.value)

    actual_result_field_id = get_param_value(Parameters.JIRA_ACTUAL_RESULT_FIELD_ID.value)

    expected_result_field_id = get_param_value(Parameters.JIRA_EXPECTED_RESULT_FIELD_ID.value)

    environment_field_id = get_param_value(Parameters.JIRA_ENVIRONMENT_FIELD_ID.value)

    description = "{}\n\nReported by: {}".format(
        fields["description"], fields["reportedby"]
    )
    return {
        "serviceDeskId": int(
            get_param_value(Parameters.JIRA_SERVICE_DESK_ID.value)),
        "requestTypeId": int(
            get_param_value(Parameters.JIRA_REQUEST_TYPE_ID.value)),
        "requestFieldValues": {
            custom_field_id: fields["snow_incident_number"],
            actual_result_field_id: "N/A",
            expected_result_field_id: "N/A",
            environment_field_id: {
                "value": "Production",
            },
            "priority": {
                "name": "Severity {}".format(fields["priority"]),
            },
            "summary": fields["summary"],
            "description": description,
        }
    }


def put_mapping(fields):
    values = {}
    if "snow_incident_number" in fields:
        custom_field_id = get_param_value(Parameters.JIRA_CUSTOMER_REF_NO_FIELD_ID.value)

        values[custom_field_id] = fields["snow_incident_number"]
    if "priority" in fields:
        values["priority"] = {
            "name": "Severity {}".format(fields["priority"]),
        }
    if "summary" in fields:
        values["summary"] = fields["summary"]
    if "description" in fields:
        values["description"] = fields["description"]
    if "status" in fields:
        values["status"] = fields["status"]
    if "comment" in fields:
        values["comment"] = fields["comment"]
    if "reportedby" in fields:
        values["reportedby"] = fields["reportedby"]
    return values


def create_jsd_incident(body):
    # Creating a Jira Service Desk Incident
    logger.debug("Creating an incident in Jira Service Desk...")
    issue = create_request(body)
    logger.debug("Response is... %s",issue)
    return issue["issueKey"]


def create_request_comment(incident_id, field, value, reported_by=None):
    reporter = f" ({reported_by})" if reported_by else ""
    field = field.capitalize() if field else None
    text = f" {field} updated to \"{value}\"" if field else value
    comment = f"Metlife ServiceNow Incident Update{reporter}: {text}"
    create_comment(incident_id, comment)


def update_jsd_incident(incident_id, body):
    # Updating a Jira Service Desk Incident
    logger.debug(f"Updating an incident in JSD: {incident_id}")

    reported_by = body.get("reportedby")
    request = get_jirarequest(incident_id)
    if "summary" in body:
        old_summary = request["requestFieldValues"]["summary"]
        new_summary = body["summary"]
        if old_summary != new_summary:
            create_request_comment(
                incident_id, "summary", new_summary, reported_by=reported_by)
    if "description" in body:
        old_description = request["requestFieldValues"]["description"]
        new_description = body["description"]
        if old_description != new_description:
            create_request_comment(
                incident_id,
                "description",
                new_description,
                reported_by=reported_by
            )
    if "priority" in body:
        old_priority = request["requestFieldValues"]["priority"]["name"]
        new_priority = body["priority"]["name"]
        if old_priority != new_priority:
            create_request_comment(
                incident_id, "priority", new_priority, reported_by=reported_by)
    if "status" in body:
        old_status = request["currentStatus"]["status"]
        new_status = body["status"]
        if old_status != new_status:
            create_request_comment(
                incident_id, "status", new_status, reported_by=reported_by)
    if "comment" in body:
        text = f"New Comment Added\n{body['comment']}"
        create_request_comment(incident_id, None, text, reported_by=reported_by)


def post_request_handler(body):
    logger.debug("POST HTTP request received, validating...")

    # Validation
    status, resp = validate_body(body)
    if status != 200:
        logger.debug("Body validation failed: %s", resp["error"])
        return status, resp
    else:
        logger.debug("Body validation passed")

    # Mapping
    body = post_mapping(body)

    # Creating a JSD incident
    resp["vendorticketnumber"] = create_jsd_incident(body)

    return status, resp


def put_request_handler(incident_id, body):
    logger.debug("PUT HTTP request received, validating...")

    # Validation
    extra_fields = {
        "status": validate_status,
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

    # Updating
    update_jsd_incident(incident_id, body)

    return status, resp


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
