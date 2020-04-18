#!/bin/env python

from datetime import datetime
from os import statvfs
from subprocess import check_output

status_file = '/var/log/patching.status_file'
log_file    = '/var/log/patching.log'

def update_status(action, outcome, details=None):
    '''
    Updates status file based on supplied values
    REQUIRES:  action, outcome, details(optional)
    PROVIDES:  tab delimted entry overwrite
    '''
    tstamp  = datetime.now()
    #logger.debug("Debug values - Time: {0}, action: {1},"
    #    "outcome: {2}, details: {3}".format(tstamp, action, outcome, details))
    try:
        f      = open(status_file, 'w+')
        f.write("{0}\t{1}\t{2}\t{3}".format(tstamp, action, outcome, details))
    except Exception as e:
        f.close()
        #logger.warning("Failed to update status file.  Error - {0}.\n"
        #    "Values: {1}, {2}, {3}, {4}".format(e, tstamp, action, outcome, details))
        return 2, e
    finally:
        f.close
        #logger.info("Status file updated: {0} {1} {2}".format(action, outcome, tstamp))
        return 0

def check_status():
    '''
    Returns the contencs of the status file or error
    '''
    #logger.debug("Attempting ot read status file")
    try:
        f      =  open(status_file, 'r')
        status = f.read()
        return status
    except FileNotFoundError:
        #logger.debug("Status file does not exist")
        return 2, "File does not exist"
    except Exception as e:
        #logger.warning("Unknown filesystem error: {0}".format(e))
        f.close()
        return 2, e

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
    count = check_output('rpm -qa --qf "%{NAME}\n" |grep -w "kernel"|grep -v "-"|wc -l', shell=True)
    return count.strip()