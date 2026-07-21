import json
import os
import boto3
import pymysql

secrets_client = boto3.client("secretsmanager")
sns_client = boto3.client("sns")

DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
SECRET_NAME = os.environ["SECRET_NAME"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def get_db_credentials():
    response = secrets_client.get_secret_value(
        SecretId=SECRET_NAME
    )

    secret = json.loads(response["SecretString"])

    return secret["username"], secret["password"]


def lambda_handler(event, context):

    body = json.loads(event["body"])

    customer_name = body["customer_name"]
    product_name = body["product_name"]
    quantity = body["quantity"]

    username, password = get_db_credentials()

    connection = pymysql.connect(
        host=DB_HOST,
        user=username,
        password=password,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:

            sql = """
                INSERT INTO orders
                (customer_name, product_name, quantity)
                VALUES (%s, %s, %s)
            """

            cursor.execute(
                sql,
                (customer_name, product_name, quantity)
            )

            connection.commit()

            order_id = cursor.lastrowid

    finally:
        connection.close()

    sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Order Created",
        Message=json.dumps({
            "order_id": order_id,
            "customer_name": customer_name,
            "product_name": product_name,
            "quantity": quantity,
            "status": "CREATED"
        })
    )

    return {
        "statusCode": 201,
        "body": json.dumps({
            "message": "Order created successfully",
            "order_id": order_id
        })
    }
