#!/bin/env python

from patch_actions import update_status, check_status, check_fs_size
from subprocess import Popen, PIPE
from datetime import datetime, timedelta
import sys


def update(flag):
    dr         = '--disablerepo=*'
    ex         = '--exclude=mysql* --exclude=nrpe* --exclude=nagios*'
    other      = '--nogpgcheck --skip-broken'
    so         = '--setopt=protected_multilib=false'

    if flag    == 'kernel':
        update = 'yum -y install kernel*'
        er     = '--enablerepo=base'
    else:
        update = 'yum -y update'
        er     = '--enablerepo=base --enablerepo=updates --enablerepo=monthly'
    
    update     = Popen([update, dr, er, ex, other, so], shell=True, stdout=PIPE, stderr=PIPE)
    out, err   = update.communicate()
    if update.returncode != 0:
        logger.warning('Problem with update.  Message: {0} Error: {1}'.format(out, err))
        sys.exit(4)


def get_packages():
    pass

def verify_status():
    with open('/var/log/patch.status', 'r'):
        data = f.readline()
    
    now       = datetime.now()
    then      = now - timedelta(days=1)
    t         = data[0:2]                                     # Return first 2 elements
    ts        = ("{0} {1}".format(t[0], t[1]))                # Create string
    timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") # Conver to datetime
    stage     = data[2]
    result    = data[3::]

    if  then > timestamp:
        logger.warning("Prepatch out of date.  Re-run prepatch")
        sys.exit(5)
    
    if stage != 'prepatch' or result != 'success'
        logger.warning("Prepatch not completed sucessfully.  Re-run prepatch")
        sys.exit(6)


def main():
    logging.basicConfig(
    level    = logging.WARNING,
    format   = "%(asctime)-10s %(levelname)s %(message)",
    filename = '/var/log/patching.log'
    )

    logger = logging.getLogger(__name__)

    update('all')



if __name__ == '__main__':
    main



