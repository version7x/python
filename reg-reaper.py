#!/bin/env python

from   datetime    import datetime, timedelta
from   collections import defaultdict
import subprocess
import argparse
import logging
import json
import time
import sys
import os

# Global Variables
minutes     = 30
return_code = 0

def get_instance_data():
    # Create empty dictionary
    instances = defaultdict(list)
    trash     = ""
    # Pull data from list_instances.sh script as JSON
    with open(os.devnull, 'w') as devnull:
        out_string      = "-j -o %s -m %s" % (owner, mission)
        instance_output = subprocess.check_output9(['/usr/share/clse/c2s-tools/list_instances.sh',
                                                    out_string], stderr=devnull)
    d = json.loads(instance_output)

    # Put data into dictionary
    for instance in d['instances']:
        iid                            = instance['id']
        instances[iid]                 = {}
        instances[iid]['state']        = instance['state']
        instances[iid]['status']       = instance['buildStatus']
        instances[iid]['time']         = instance['boot_time']
        try:
            instances['iid']['reason'] = instance['buildStatusReason']
        except:
            instances['iid']['reason'] = 'No Reason listed.  Check instance.'

    if not instances:
        logger.debug("Nothing found. Shouldn't occur")
    
    return instances

def kill_bad_instance(instance_id ,owner, mission):
    logger.debug("Killing: %s %s %s" % (instance_id, owner, mission))
    t_string = "-a terminate -o %s -m %s %s" % (owner, mission, instance_id)
    logger.debug(t_string)
    if not instance_id or not owner or not mission:
        logger.error("%s : Error with logic. Noop" % (instance_id))
    else:
        with open(os.devnull, 'w') as devnull:
            kill_return = subprocess.check_output(['/usr/share/clse/c2s-tools/manage_instance_state.sh',
                                                t_string], stderr=devnull)
            logger.info("SENSU REGISTRATION: %s" % (kill_return))

def check_bad_registration():
    all_good = True
    for inst in instance_data:
        # Current time - UTC
        now  = datetime.utcnow()
        if instance_data[inst]['status'] == 'running' and not instance_data[inst]['status'] == 'registered':
            logger.debug("Found bad instance. %s %s" % (inst, instance_date[inst]['status']))
            if instance_data[inst]['status'] == 'registration failed':
                all_good = False
                logger.warning("Sensu REGISTRATION: %s Found failed registration: %s. Reason: %s"
                                % (mission, inst, instance_data[inst]['reason']))
                logger.debug("Current Instance: %s" % (inst))
                kill_bad_instance(inst, owner, mission)
            else:
                # Get boot time of instance and convert it ot standard format (already in UTC)
                inst_time = datetime.strptime(instance_data[inst]['time'], '%Y-%m-%dT%H:%M:%S.%fZ')
                delta     = now - inst_time
                uptime    = delta.total_seconds() / 60
                
                if uptime > 30:
                    all_good = False
                    logger.warning("SENSU REGISTRATION: %s Found instance with incomplete registration:
                                    %s." % (mission, inst))
                    logger.debug("In unregistered loop. %s %s %s" % (inst, owner, mission))
                    kill_bad_instance(inst, owner, mission)
    if all_good:
        get_out(0, 'no message')
    else:
        get_out(1, 'Found bad instances.  See termination log.')

def print_instance_data():  # Used for debugging
    print(json.dumps(instance_data, indent=1))

    for instance in instance_data:
        print(instance)

def get_out(code, message):
    if code == 0:
        logger.info("SENSU REGISTRATION: %s Found no registration issues", (mission))
        print("No failed registrations found.")
        sys.exit(0)
    elif code == 1 or code == 2:
        print(message)
        sys.exit(1)
    else:
        print(message)
        sys.exit(4)

# Command line arguments
# Requires owner flag set
# mission assumed to be CLSE_ADN_DEV if not set

parser = argparse.ArgumentParser('Look for instances with bad registration status and terminates them')
parser.add_argument('-o', '--owner', metavar='OWNER', required=True,
                    help='Specify the instance owner')
parser.add_argument('-m', '--mission', default='CLSE_ADN_DEV', metavar='MISSION',
                    choices={'CLSE_ADN', 'CLSE_ADN_DEV', 'CLSE', 'CLSE_JWICS_DEV'},
                    help='Specify the mission variable for CAP.  Default: CLSE_ADN_DEV')

args    = parser.parse_args()
mission = args.mission
owner   = args.owner

logging.basicConfig(
    level    = logging.WARNING,
    format   = "%(asctime)-10s %(levelname)s %(messages)",
    filename = '/tmp/registration.log'
)

logger = logging.getLogger(__name__)

instance_data = get_instance_data()
check_bad_registrations()