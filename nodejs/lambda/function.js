/*jshint esversion: 6 */
'use strict';

// dependencies
const Promise = require('bluebird');
const AWS = require('aws-sdk');
const chef = require('chef');
const fs = require('fs');

// dynamodb library
const dynamodb = Promise.promisifyAll(new AWS.DynamoDB({ region: 'us-west-2' }));

// constants
const CHEF_URL = 'https://api.chef.io/organizations/foo';
const CHEF_USERNAME = 'admin';
const PEM_FILE = fs.readFileSync('client.pem');

// connect to chef server
const client = chef.createClient(CHEF_USERNAME, PEM_FILE, CHEF_URL);
const chefClient = Promise.promisifyAll(client);

// terminate function
function terminateInstance(message) {

  const groupName = message.AutoScalingGroupName;
  const nodeName = [groupName[0], message.EC2InstanceId].join('-');

  console.info(`Terminating instance: ${nodeName}`);

  return chefClient.deleteAsync(`/nodes/${nodeName}`)
  .then(() => dynamodb.deleteAsync({ Key: {
          instance_id: message.EC2InstanceId,
        },
  })
    );
}

function launchInstance(message) {

  const groupName = message.AutoScalingGroupName;
  const nodeName = [groupName, message.EC2InstanceId].join('-');

  // setup the db object
  const instance = {
      instance_id: message.EC2InstanceId,
      node_name: nodeName,
      chef_url: CHEF_URL,
      environment: groupName,
    };

  const clientBody = {
      name: nodeName,
      admin: false,
      create_key: true,
    };

  console.info(`Launching instance: ${clientName}`);

  return chefClient.postAsync(`/clients/${clientName}`, clientBody)
      .then(response => {
          server.key = response.body.private_key;
          return dynamodb.putAsync(instance);
        });
}

function parseMessages(message) {

  if (message.Event === 'autoscaling:EC2_INSTANCE_TERMINATE') {
    // run shutdown tasks
    return terminateInstance(message);

  } else if (message.Event === 'autoscaling:EC2_INSTANCE_LAUNCH') {
    // run startup tasks
    return launchInstance(message);

  } else {
    // unrecognized event type
    console.info(`Unrecognized message event: ${message.Event}`);
  }
}

exports.handler = function (event, context, callback) {
    return Promise.map(event.Records, record => {
        const message = record.Sns.Message;
        return parseMessages(message);
      });
  };
