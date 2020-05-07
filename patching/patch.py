#!/bin/env python

from __future__ import print_function

from patch_actions import update_status, check_status, check_fs_size
from patch_actions import verify_root, verify_status
from subprocess import Popen, PIPE
from datetime import datetime, timedelta
from argparse import ArgumentParser
from time import sleep
from os import system, uname, chmod
import logging
import sys

cron_file  = '/etc/rc.d/rc.local'
script_dir = '/usr/local/bin/patching/'

# Set up logging
logger       = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter    = logging.Formatter('%(asctime)-10s %(name)s %(levelname)s %(message)s')

file_handler = logging.FileHandler('/var/log/patching.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.ERROR)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def update(flag=None):
    '''
    Sets up yum update options in 'cmd' variable
    REQUIRES: flag - Default none, if kernel specified, does kernel only update
    PROVIDES: system call to yum update.  Return code from yum command, error output if any
    '''
    dr         = '--disablerepo=* '
    ex         = '--exclude=mysql* --exclude=nrpe* --exclude=nagios* '
    other      = '--nogpgcheck --skip-broken '
    so         = '--setopt=protected_multilib=false '

    if flag    == 'kernel':
        update = 'yum -y update kernel '
        er     = '--enablerepo=base '
    else:
        update = 'yum -y update '
        er     = '--enablerepo=base --enablerepo=updates --enablerepo=monthly '

    cmd       = update + dr + er + ex + other + so
    update     = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err   = update.communicate()
    if update.returncode != 0:
        logger.warning('Problem with update.  Message: {0} Error: {1}'.format(out, err))
        update_status('patch', 'failed', err)
        if not silent:
            print('[{0}] Patching failed: {1}'.format(host, err))
        sys.exit(14)
    else:
        logger.info('Patches applied succssfully.  Output: {0}'.format(out))
        update_status('patch', 'success')
        if not silent:
            print('[{0}] Patching - success {1}'.format(host, err))
        return 0


def restart(message, delay, wall=False):
    '''
    Initates system reboot
    REQURIRES: message to display to users, reboot delay, True/False value for console message
    '''
    # WALL MESSAGE
    if wall:
        system('/usr/bin/wall {0}'.format(message))
    logger.info('Rebooting for patching')
    # REBOOT NOW/DELAY
    if delay:
        sleep(delay)
    system('/sbin/reboot now')
    
    
def get_packages():
    # Not implemented at this time
    # Packages marked for update are stored in /tmp/update_list-YYYY-MM.txt
    pass


def parse():
    '''
    Parse command line arguments
    - no delay    : do not sleep before reboot
    - kernelonly  : update kernel only
    - kernelfirst : run kernelonly first and then update all other packages
    - noreboot    : Will not reboot after patching.  Manual reboot needed
    - autopatch   : will install script to auto-run postpatch on reboot
    - silent      : no output on success.  only critical failure output
    - wall        : display reboot warning to all logged in users
    '''
    parser = ArgumentParser(description='Updates all packages on system based on flags selected')
    parser.add_argument('-n', '--nodelay',     action='store_true',  dest='nodelay',    help='Delay reboot by X seconds')
    parser.add_argument('-k', '--kernelonly',  action='store_true',  dest='kernel',     help='Update kernel only')
    parser.add_argument('-f', '--kernelfirst', action='store_true',  dest='first',      help='Run update twice. First time for kernel only')
    parser.add_argument('-R', '--noreboot',    action='store_false', dest='reboot',     help='Stop auto reboot after patching.')
    parser.add_argument('-a', '--autopatch',   action='store_true',  dest='auto_patch', help='Flag used for framework')
    parser.add_argument('-s', '--silent',      action='store_true',  dest='silent',     help='Silent - repress output')
    parser.add_argument('-w', '--wall',        action='store_true',  dest='wall',       help='Send warning message to logged in users before reboot')

    return parser.parse_args()


def get_status_details():
    '''
    Gets stage, result, details, timestamp, and time from 1 day ago
    Checks if time is within 1 day
    verifies previous status is correct and no unexpected errors
    '''
    stage, result, details, timestamp, then = verify_status(silent)

    # Checks to see if prepatch ran more than one day ago
    if  then > timestamp:
        message = 'Prepatch: Out of Date.  Re-run prepatch'
        logger.warning(message)
        if not silent:
            print('[{0}] {1}'.format(host, message))
        sys.exit(12)
    # Checks to see if prepatch was a success
    # or if we made it to patching but failed
    # Should rule out prepatch failures, patching success, and all postpatch
    if stage == 'prepatch' and result == 'success':
        logger.info('Status verified: successful prepatch')
        return 0
    elif stage == 'patch' and result == 'failed':
        logger.info('Status verified: patching retry')
        return 0
    elif stage == 'patch' and result == 'success':
        logger.info('Patch.py arleady ran successfully')
        return 0
    else:
        message = 'Prepatch not completed sucessfully.  Re-run prepatch'
        logger.warning(message)
        logger.warning(stage, result, details)
        if not silent:
           print('[{0}] {1}'.format(host, message))
        sys.exit(13)

def set_cron():
    # postpatch >> /etc/rc.d/rc.local
    entry = script_dir + 'postpatch.py\n'
    with open(cron_file, 'a+') as f:
        try:
            f.write(entry)
        except Exception as e:
            logger.warning('Could not update crontab for reboot.  Error: {0}'.format(e))
            logger.exception('Failed to write crontab traceback:')
            ret = 1
        else:
            logger.info('Crontab updated for auto run after reboot')
            ret = 0
    
    return ret
        
        
def set_systemd():
    '''
    rc.local does not run by default under centos 7 due to systemd.
    In order to enable it, we must mark the file executable and then enable the rc-local.service
    First check version of os to see if we're centos 6 or centos 7.
    If 7 then enable service and make file executable
    RETURNS: 0 on success of cent 6, cent 7 with updates to services, or failure codes otherwise
    '''
    os = Popen('rpm -q centos-release', shell=True, stdout=PIPE, stderr=PIPE)
    output, error = os.communicate()
    if os.returncode != 0:
        logger.critical('Error getting OS version: {0}'.format(error))
        return 15

    if output.lower().startswith('centos-release-6'):
        logger.info('Determined system to be Centos/Redhat version 6')
        return 0
    elif output.lower().startswith('centos-release-7'):
        logger.info('Determined system to be Centos/Redhat version 7')
        chmod(cron_file, 0755)
        enable    = Popen('systemctl enable rc-local.service', shell=True, stdout=PIPE, stderr=PIPE)
        e_out, e_err = enable.communicate()
        if enable.returncode != 0:
            logger.critical('Unable to enable rc.local service.  {0} Error: {1}'.format(e_out, e_err))
            return 16
        else:
            logger.info('rc.local good to go')
            return 0
    else:
        logger.critical('Unexpected CentOS variant: {0}'.format(output))
        exit(16)





def verify_kernel():
    # uname -r
    # didn't have time to implement
    pass


def main():
    global host
    flag   = None
    args   = parse()
    host   = uname()[1]
    reboot = True

    if args.reboot == False:
        reboot      = False

    # Need to be root to run
    verify_root()

    # Reboot now vs default 300 seconds/5 min reboot
    if args.nodelay:
        delay = None
    else:
        delay = 300

    # For running in groups, turn off output
    global silent
    if args.silent:
        silent = True
    else:
        silent = False

    # Verify prepatch ran recently
    get_status_details()
    
    # Sets kernel flag for doing an update kernel only pass
    if args.kernel:
        flag = 'kernel'

    # Verify whether or not there should be two updates runs (one for kernel only)
    if args.first == True:
        update('kernel')
        update(None)
    else:
        update(flag)

    # IF autopatch == True, entry will be added to cron to start postpatch on reboot
    if args.auto_patch:
        cron_success = set_cron()
        if not silent and cron_success != 0:
            print('[{0}] Warning:  Unable to auto run postpatch after reboot.  Check logs and run manually')

    # Verify centOS 7/systemd checks went ok or exit
    sysd_code = set_systemd()
    if sysd_code != 0:
        if not silent:
            print('{0} Patching failed: Issues with systemd checks'.format(host))
            logger.critical('Patching failed due to os level name or systemd update')
            update_status('patch', 'failed', 'centOS version/systemd error')
            exit(sysd_code)
        
    # Determines if console warning displayed
    if args.wall:
        wall = True
    else:
        wall = False
    # Are we doning a reboot now?
    if reboot == True:
        restart('All patches applied.  Rebooting as part of patch process in {0} seconds.'.format(delay), delay, wall)
    else:
        message = 'All patches applied.  No-reboot specified'
        logger.info(message)
        if not silent:
            print('[{0}] Patch - successful: {1}'.format(host, message))
        return 0



if __name__ == '__main__':
    main()
