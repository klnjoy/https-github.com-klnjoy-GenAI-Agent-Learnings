import json
import boto3
import logging
from botocore.exceptions import ClientError

# ---------------------------
# Logging Configuration
# ---------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------
# DynamoDB Setup
# ---------------------------
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "employe-details"
table = dynamodb.Table(TABLE_NAME)


# ---------------------------
# Common Response Formatter
# ---------------------------
def process_response(status_code, body):
    logger.info(f"Returning response | status={status_code} | body={body}")

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=str)
    }


# ---------------------------
# READ Item
# ---------------------------
def read_item(empid):
    logger.info(f"Reading employee | empid={empid}")

    try:
        result = table.get_item(Key={"empid": empid})
        logger.debug(f"DynamoDB raw response: {result}")

        if "Item" in result:
            logger.info(f"Employee found | empid={empid}")
            return process_response(200, result["Item"])
        else:
            logger.warning(f"Employee NOT found | empid={empid}")
            return process_response(404, f"No employee found with empid {empid}")

    except ClientError as e:
        logger.error(f"DynamoDB read failed | empid={empid} | error={str(e)}")
        return process_response(500, str(e))


# ---------------------------
# CREATE Item
# ---------------------------
def create_item(payload):
    logger.info(f"Creating employee | payload={payload}")

    try:
        table.put_item(Item=payload)
        return process_response(201, "Employee created successfully")

    except ClientError as e:
        logger.error(f"DynamoDB create failed | error={str(e)}")
        return process_response(500, str(e))


# ---------------------------
# UPDATE Item
# ---------------------------
def update_item(empid, update_data):
    logger.info(f"Updating employee | empid={empid} | update_data={update_data}")

    try:
        update_expression = "SET " + ", ".join(
            [f"{k} = :{k}" for k in update_data.keys()]
        )

        expression_values = {f":{k}": v for k, v in update_data.items()}

        response = table.update_item(
            Key={"empid": empid},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues="UPDATED_NEW"
        )

        logger.info(f"Update successful | response={response}")
        return process_response(200, "Employee updated successfully")

    except ClientError as e:
        logger.error(f"DynamoDB update failed | empid={empid} | error={str(e)}")
        return process_response(500, str(e))


# ---------------------------
# DELETE Item
# ---------------------------
def delete_item(empid):
    logger.info(f"Deleting employee | empid={empid}")

    try:
        table.delete_item(Key={"empid": empid})
        return process_response(200, f"Employee {empid} deleted successfully")

    except ClientError as e:
        logger.error(f"DynamoDB delete failed | empid={empid} | error={str(e)}")
        return process_response(500, str(e))


# ---------------------------
# Lambda Entry Point
# ---------------------------
def lambda_handler(event, context):

    request_id = context.aws_request_id
    logger.info(f"Lambda invoked | request_id={request_id}")
    logger.info(f"Incoming event: {json.dumps(event)}")

    try:
        path = event.get("path")
        method = event.get("httpMethod")

        body = json.loads(event["body"]) if event.get("body") else {}
        query_params = event.get("queryStringParameters") or {}
        empid = query_params.get("empid")

        logger.info(f"Routing request | path={path} | method={method}")

        # -------- READ --------
        if path == "/read" and method == "GET":
            if not empid:
                logger.warning("Missing empid in query params")
                return process_response(400, "empid query parameter is required")

            return read_item(empid)

        # -------- CREATE --------
        elif path == "/create" and method == "POST":
            if "empid" not in body:
                logger.warning("empid missing in request body")
                return process_response(400, "empid is required in request body")

            return create_item(body)

        # -------- UPDATE --------
        elif path == "/update" and method == "PUT":
            if not empid:
                logger.warning("Missing empid for update")
                return process_response(400, "empid query parameter is required")

            return update_item(empid, body)

        # -------- DELETE --------
        elif path == "/delete" and method == "DELETE":
            if not empid:
                logger.warning("Missing empid for delete")
                return process_response(400, "empid query parameter is required")

            return delete_item(empid)

        else:
            logger.warning(f"Invalid route | path={path} | method={method}")
            return process_response(404, "Route not found")

    except Exception as e:
        logger.exception("Unhandled Lambda exception")
        return process_response(500, str(e))