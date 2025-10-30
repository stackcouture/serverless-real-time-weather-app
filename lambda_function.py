import json
import urllib.request
import os
import boto3
import uuid
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("WeatherHistory")

def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    try:
        method = event.get("requestContext", {}).get("http", {}).get("method")

        if method == "OPTIONS":
            return build_response(200, {"message": "CORS preflight OK"})

        if method == "GET":
            response = table.scan()
            items = response.get("Items", [])
            return build_response(200, items)

        if method == "POST":
            if "body" not in event or not event["body"]:
                return build_response(400, {"error": "Missing body"})

            body = json.loads(event["body"])
            city = body.get("city")
            if not city:
                return build_response(400, {"error": "Missing city"})

            api_key = os.environ.get("OPENWEATHER_API_KEY")
            if not api_key:
                return build_response(500, {"error": "Missing API key"})

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())

            if data.get("cod") != 200:
                return build_response(400, {"error": data.get("message", "Invalid city")})

            temp = Decimal(str(data["main"]["temp"]))
            desc = data["weather"][0]["description"]
            timestamp = datetime.utcnow().isoformat()

            table.put_item(Item={
                "id": str(uuid.uuid4()),
                "city": city,
                "temperature": temp,
                "description": desc,
                "timestamp": timestamp
            })

            return build_response(200, {"alert": f"✅ Saved weather info for {city.title()}!"})

        return build_response(405, {"error": "Method not allowed"})

    except Exception as e:
        print("Error:", str(e))
        return build_response(500, {"error": str(e)})

def build_response(status, body):
    """Helper to attach CORS headers every time"""
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body, default=str)
    }
