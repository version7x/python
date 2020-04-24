#!/bin/env python

from patch_actions import update_status, check_status, check_fs_size
from subprocess import Popen, PIPE
from datetime import datetime, timedelta
from argparse import ArgumentParser
from time import sleep
from os import system
import logging
import sys


def update(flag=None):
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
        logger.warning('Problem with update.  Message: {} Error: {}'.format(out, err))
        update_status('patch', 'failed', err)
        sys.exit(4)
    else:
        logger.info('Patches applied succssfully.  Output: {}'.format(out))
        update_status('patch', 'success', out)
        return 0


def reboot(message, delay=None):
    # WALL MESSAGE
    system('/bin/wall {}'.format(message))
    # REBOOT NOW/DELAY
    if delay:
        sleep(delay)
    logger.info('Rebooting for patching')
    system('/sbin/reboot now')
    
    
def get_packages():
    pass


def parse():
    parser = ArgumentParser()
    parser.add_argument('-q', '--nodelay',    action='store_true', dest='nodelay',    help='Delay reboot by X seconds')
    parser.add_argument('-k', '--kernelonly', action='store_true', dest='kernel',     help='Update kernel only')
    #parser.add.argument('-a', '--autopatch',  action='store_true', dest='auto_patch', help='Flag used for framework')

    return parser.parse_args()


def verify_status():
    #with open('/var/log/patch.status', 'r') as f:
        f = check_status()
        data = f.readline()
        
        now       = datetime.now()
        then      = now - timedelta(days=1)
        t         = data[0:2]                                     # Return first 2 elements
        ts        = ("{} {}".format(t[0], t[1]))                  # Create string
        timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") # Conver to datetime
        stage     = data[2]
        result    = data[3::]

        # Checks to see if prepatch ran more than one day ago
        if  then > timestamp:
            logger.warning("Prepatch out of date.  Re-run prepatch")
            sys.exit(5)

        # Checks to see if prepatch was a success
        # or if we made it to patching but failed
        # Should rule out prepatch failures, patching success, and all postpatch
        if stage == 'prepatch' and result == 'success':
            logger.info('Status verified: successful prepatch')
            return 0
        elif stage == 'patch' and result == 'failed':
            logger.info('Status verified: patching retry')
            return 0
        else:
            logger.warning("Prepatch not completed sucessfully.  Re-run prepatch")
            sys.exit(6)

def set_cron():
    pass

def main():
    flag = None
    args = parse()

    if args.nodelay:
        delay = args.nodelay
    if args.kernel:
        flag = 'kernel'

    verify_status()
    update(flag)

    #if args.auto_patch:
    #    set_cron()

    reboot('All patches applied.  Rebooting as part of patch process.', delay)



if __name__ == '__main__':
    logging.basicConfig(
        level    = logging.DEBUG,
        format   = '%(asctime)-10s %(levelname)s %(message)s',
        filename = '/var/log/patching.log'
    )

    logger = logging.getLogger(__name__)

    main()
