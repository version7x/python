#!/bin/env python

from collections import defaultdict
import logging
import boto3

def get_instance_data(session, mission , filters):
    '''
    Retrieve instance data based on specified owner and mission
    REQUIRES: AWS session object(including auth object), filters (tbc)
    RETURNS:  nested dictionary with values as lists/sets:
        instance_id, tagged instance name, private_ip, buildStatus, state,
        instance_type,  ami_id, owner, creation_time
    '''
    instances = session.instances.filter(
        Filters=[
            {'Name': 'instance-state-name', 'Values':['running']}
        ]
    )

    # create instances dictionary
    inst_dict = defaultdict()
    for i in instances:
        # Populate instance dictionary
        inst_dict[i.iid]          = {}
        inst_dict[i.iid]['ami']   = i.image_id
        inst_dict[i.iid]['time']  = i.launch_time
        inst_dict[i.iid]['type']  = i.instance_type
        inst_dict[i.iid]['ip']    = i.private_ip_address
        inst_dict[i.iid]['state'] = i.state['Name']
        # Navigate through the tags and make assignments
        for tag in i.tags:
            if 'Name' in tag['Key']:
                inst_dict[i.iid]['name']   = tag['Value']
            elif 'Owner' in tag['Key']:
                inst_dict[i.iid]['owner']  = tag['Value']
            elif 'fqdn' in tag['Key']:
                inst_dict[i.iid]['fqdn']   = tag['Value']
            elif 'buildStatusReason' in tag['Key']:
                inst_dict[i.iid]['reason'] = tag['Value']
            elif 'buildStatus' in tag['Key']:
                inst_dict[i.iid]['status'] = tag['Value']
    
    return inst_dict

def manage_instance(session, instance_id, action):
    '''
    Kills and instance based on data provided
    REQUIRES: AWS Session object, instance_id, action
    PROVIDES: Terminates, stops, or starts provided instance
    '''
    if action == 'terminate':
        session.instance.filter(InstanceIds=[instance_id]).terminate()
    elif action == 'stop':
        session.instance.filter(InstanceIds=[instance_id]).stop()
    elif action == 'start':
        session.instance.filter(InstanceIds=[instance_id]).start()
    else:
        print("Unkown action: %s.  Should be termainate, stop, or start.") % (action)
        return 2
