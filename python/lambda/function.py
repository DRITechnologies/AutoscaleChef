# import libraries
import json
import logging

# 3rd party
import chef
from chef.exceptions import ChefServerNotFoundError
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# chef constants
CHEF_SERVER_URL = 'https://api.chef.io/organizations/foo'
USERNAME = 'admin'
PEM_KEY = 'client.pem'

# dynamodb constraints
REGION = 'us-west-2'
TABLE = 'testing'

# connect to dynamodb
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE)

# parse instance id from message details
def parse_id(details):
    try:
        return details['EC2InstanceId']
    except KeyError as err:
        logger.error(err)

# parse autoscale group from message
def parse_as_group(message):
    try:
        return message['AutoScalingGroupName']
    except KeyError as err:
        logger.error(err)

# parse sns event type
def parse_event_type(details):
    try:
        return details['Event']
    except KeyError as err:
        logger.error(err)

def delete_node(hostname):
    with chef.ChefAPI(CHEF_SERVER_URL, PEM_KEY, USERNAME):
        try:
            # remove client from chef server
            client = chef.Client(hostname)
            client.delete()
            logger.info('Successfully deleted client %s', hostname)
            # remove node from chef server
            node = chef.Node(hostname)
            node.delete()
            logger.info('Successfully deleted node %s', hostname)
        except ChefServerNotFoundError as err:
            logger.error(err)

def get_client_key(hostname):
    with chef.ChefAPI(CHEF_SERVER_URL, PEM_KEY, USERNAME):
        client = chef.Client.create(hostname)
        logger.info(client)
        logger.info(client.private_key)
        return client.private_key

# setup instance for launch
def launch_event(hostname, instance_id):
    logger.info('Launching instance %s', hostname)
    client_key = get_client_key(hostname)
    try:
        table.put_item(Item={
            'instance_id': instance_id,
            'client_key': client_key,
            'chef_host': CHEF_SERVER_URL
        })
    except ClientError as err:
        logger.error(err)

# cleanup instance on terminate event
def terminate_event(hostname, instance_id):
    logger.info('Terminating instance %s', hostname)
    delete_node(hostname)
    try:
        table.delete_item(Key={'instance_id': instance_id})
        logger.info('')
    except ClientError as err:
        logger.error(err)



# parse message for event type
def parse_message(message):
    logger.info(message['Description'])

    # parse message details
    instance_id = parse_id(message)
    as_group = parse_as_group(message)

    # generate hostname
    hostname = '-'.join([as_group, instance_id])

    # get event type
    event_type = parse_event_type(message)

    # determine message type
    if event_type == 'autoscaling:EC2_INSTANCE_TERMINATE':
        terminate_event(hostname, instance_id)
    elif event_type == 'autoscaling:EC2_INSTANCE_LAUNCH':
        launch_event(hostname, instance_id)
    else:
        logger.error('Unknown event type')

# aws lambda handler
def lambda_handler(event, context):
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        parse_message(message)
