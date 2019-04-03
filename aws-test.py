#!/bin/env python

from auth import get_auth
import actions
import boto3

cred = get_auth()
ec2  = get_session(cred, aws_service='ec2')

instances = actions.get_instance_data(ec2, 'CLSE_ADN_DEV', None)
print(instances)
