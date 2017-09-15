from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import os
import logging
import json

SLACK_CHANNEL = os.environ['channel']
HOOK_URL = os.environ['hook']
logger = logging.getLogger()
logger.setLevel(logging.INFO)
severity = 'warning'


def lambda_handler(event, context):
    protocols = []
    ports = []
    ranges = []
    message = {}
    for item in event['detail']['requestParameters']['ipPermissions']['items']:
        if item['ipProtocol'] == 17:
            protocols.append("UDP")
        elif item['ipProtocol'] == 6:
            protocols.append("TCP")
        else:
            protocols.append(item['ipProtocol'])
    
        if item['toPort'] == item['fromPort']:
            ports.append(item['toPort'])
        else:
            ranges.append(item['fromPort'] + '-' + item['toPort'])
        ranges.append(item['ipRanges']['items'][0]['cidrIp'])
    if 80 in ports or 443 in ports or 25 in ports or 465 in ports:
        severity = 'good'
        message['Description'] = 'Normal port changes'
    elif 20 in ports or 21 in ports or 1433 in ports:
        severity = 'danger'
        message['Description'] = 'Ports changed are from AWS Trusted Advisory Warnings'
    message = {
        'Name': event['detail']['userIdentity']['arn'].split(':').pop(),
        'Description': 'Warning: There were port changes made',
        'SecurityGroup': event['detail']['requestParameters']['groupId'],
        'Ports': ports,
        'Protocols': protocols,
        'Ranges': ranges
    }
    slack_message = {
        'channel': SLACK_CHANNEL,
        'username': 'AWS SNS via Lamda :: ChaoSlingr',
        'text': '*'+event['detail']['eventName']+'*',
        'icon_emoji': ':hear_no_evil:',
        'attachments': [{
            'color': severity,
            'text': json.dumps(message, indent=2, separators=(',', ': '))
        }]
    }
    
    req = Request(
        url=HOOK_URL,
        data=json.dumps(slack_message).encode('utf-8'),
        headers={'content-type': 'application/json'}
    )
    
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)
