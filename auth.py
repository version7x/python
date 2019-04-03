#!/bin/env python

from cap.manager import Manager
from cap.api     import API
import boto3
import os

def get_auth(
    cap_cert  = '/data/1/server_management/C2S/certs/cld-clse.pem',
    data_path = '/usr/share/awscli/lib/python2.7/site-packages/botocore/data',
    cap_acct  = 'CLSE_ADN_DEV'
):
    '''
    Returns Credential Object using cap-client libraries
    REQUIRES: cap_cert, data_path, cap_acct and 
            Optional Arguments include:
            data_path: Path to endpoints.json. Sane default
            cap_acct:  Account name to use. Def=CLSE_ADN_DEV
            cap_cert:  Path to CAP_CERTIFICATE.  Sane default
    PROVIDES: credential object for use with AWS Session
    '''
    global api, user, manager

    os.environ['CAP_CA_CERTIFICATE'] = '/etc/pki/tls/certs/ca-bundle.crt'
    os.environ['CAP_CERTIFICATE']    = cap_cert
    os.environ['AWS_DATA_PATH']      = data_path
    api                              = API()
    user                             = api.get_user()
    manager                          = Manager(api=api)
    credential                       = manager.create_credential('CIA', cap_acct, 'SRVCADMIN')

    return credential

def get_session(cred, aws_service='ec2'):
    '''
    Sets up AWS Session
    REQUIRES:  credential object
    PROVIDES:  session object for use with ec2 session
    '''
    # Creates a connection to AWS via boto with supplied cred object
    connection = boto3.session.Session(region_name='us-iso-east-1', **cred.to_boto3())

    # Creates a session with the supplied connection to specified services
    session = connection.resource(aws_service)

    return session
