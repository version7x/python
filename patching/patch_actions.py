#!/bin/env python

from __future__ import print_function

from datetime import datetime, timedelta
from subprocess import Popen, PIPE
from os import statvfs, getuid, uname
from sys import exit
import logging


'''
Patch_actions is a group of functions that is used in more than one 
of the patching scripts to prevent code duplication.
'''

# Set up logging
logger       = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter    = logging.Formatter('%(asctime)-10s %(name)s %(levelname)s %(message)s')
file_handler = logging.FileHandler('/var/log/patching.log')

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Set variables
status_file = '/var/log/patching.status_file'
log_file    = '/var/log/patching.log'

def update_status(action, outcome, details=None):
    '''
    Updates status file based on supplied values
    REQUIRES:  action, outcome, details(optional)
    PROVIDES:  tab delimted entry overwrite
    RETURNS:   0 on sucess or '2, error' on failure
    '''
    tstamp  = datetime.now()
    logger.debug("Debug values - Time: {0}, action: {1},"
        "outcome: {2}, details: {3}".format(tstamp, action, outcome, details))
    try:
        f      = open(status_file, 'w+')
        f.write("{0}\t{1}\t{2}\t{3}\n".format(tstamp, action, outcome, details))
    except Exception as e:
        f.close()
        logger.exception("Failed to update status file.  Error - {0}.\n"
            "Values: {1}, {2}, {3}, {4}".format(e, tstamp, action, outcome, details))
        return 2, e
    finally:
        f.close
        logger.info("Status file updated: {0} {1} {2}".format(action, outcome, tstamp))
        return 0, 0

def check_status():
    '''
    Returns the contencs of the status file or error
    Returns contents of status file
    CONTENTS:  timestamp action result error(optional)
    RETURNS:   Status file or '2, error'
    '''
    logger.debug("Attempting ot read status file")
    try:
        with open(status_file, 'r') as f:
            status = f.read()
        return status, None
    except FileNotFoundError:
        logger.exception("Status file does not exist")
        return 2, "Status file does not yet exist"
    except Exception as e:
        logger.exception("Unknown filesystem error: {0}".format(e))
        return 2, e

def verify_status(silent):
    '''
    Gets contents of status file from check_status()
    Parses the fields
    Field 1: Time stamp... determines if time is within one day
    Field 2: Stage - prepatch, patch, postpatch
    Field 3: Result - failed, success, etc
    Field 4: (optional) - error output
    RETURNS: stage, result, details, timestamp, then
    '''
    sout, serr = check_status()
    if sout == 2:
        logger.warning('Unable to read status file.  {0}'.format(serr))
        if not silent:
            print('Unable to read status file.  {0}'.format(serr))
        exit(1)
        sout = str(sout)

    data       = sout.split()
    now        = datetime.now()                                # Get current time
    then       = now - timedelta(days=1)                       # Get difference between now and 24 hours ago
    t          = data[0:2]                                     # Return first 2 elements
    ts         = ("{0} {1}".format(t[0], t[1]))                # Create string from day and time
    timestamp  = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") # Convert to datetime
    stage      = data[2]
    result     = data[3]
    details    = ' '.join(data[4::])
    #details   = data[4::]
    # Old version commented out... current version triggers stack trace if called
    # BUG

    return stage, result, details, timestamp, then

def check_fs_size(partition, space):
    '''
    Checks partition space available.  Returns free block count
    REQUIRES: partition mount point, minimum space avai in MB
    PROVIDES: Your mom with a report on how your life turned out
    MB = blocks * block_size / 1024 / 1024 ## close but not exact
    NOTE: Using statvfs vs some better libraries due to age of hosts
    '''
    b_free  = statvfs(partition)[4]
    b_size  = statvfs(partition)[0]
    b_avail = b_free * b_size / 1024 / 1024  # Really rough math

    if b_avail > space:
        return "pass", b_avail
    else:
        return "fail", b_avail

def get_kernel_count():
    '''
    Returns number of kernels installed
    '''
    output = Popen('rpm -qa --qf "%{NAME}\n" |grep -w "kernel"|grep -v "-"|wc -l', shell=True, stdout=PIPE, stderr=PIPE)
    count, err = output.communicate()
    if err:
        logger.warning('Recieved Error when getting kernel count: {0}'.format(err))
    return count.strip()
    
def clean_kernels(num):
    '''
    Trims kernels to number provided
    Similar to:  package-cleanup -y --oldkernels --count=${kern_num}
    REQUIRES: number of kernels to keep
    PROVIDES: list out put of pass/fail and command output
    '''
    kernels = Popen('/usr/bin/package-cleanup -y --oldkernels --count={0}'.format(num), shell=True, stdout=PIPE, stderr=PIPE)
    ck_out, ck_err = kernels.communicate()
    
    if kernels.returncode != 0:
        ck_fail = 'fail'
        #logger.warning('Unable to clean kernels. Error: {0}'.format(ck_err))
        return ck_fail, ck_err
    else:
        ck_fail = 'pass'
        #logger.info('Kernels cleaned.  Trimmed down to {0}} kernels'.format(num))
        #logger.info('Yum Output: {0}'.format(ck_out))
        return ck_fail, ck_out

def verify_root(test=False):
        '''
        Verifies the user is root.  If not exits with status 2
        '''
        if getuid() != 0:
            logger.critical("Attempted to run as non-root user")
            print('You must be root to run this script')
            exit(2)
        else:
            return 0
