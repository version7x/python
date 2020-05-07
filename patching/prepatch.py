#!/bin/env python

from __future__ import print_function

from patch_actions import update_status, check_fs_size, clean_kernels
from patch_actions import verify_root, get_kernel_count
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from datetime import datetime
from sys import exit
from os import uname
import logging
import socket


# Dictionary of filesystems to check along with size in MB
fs_list      = { '/var': 500, '/var/log': 100, '/': 1000, '/boot': 60}
kern_num     = 2
check_server = 'kickstart'
check_port   = 80

# Set up logging
logger       = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter    = logging.Formatter('%(asctime)-10s %(name)s %(levelname)s %(message)s')

file_handler = logging.FileHandler('/var/log/patching.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.CRITICAL)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def clean_yum():
    '''
    Runs yum clean all command.
    RETURNS: pass/fail and logs output
    '''
    # package-cleanup -y --oldkernels --count=2
    # clean yum clean all
    clean = Popen('yum clean all', shell=True, stdout=PIPE, stderr=PIPE)
    out, err = clean.communicate()
    if clean.returncode != 0:
        yc_fail = 'fail'
        logger.critical('Unable to clean yum cache. Error: {0}'.format(err))
        update_status('yum_clean', yc_fail, err)
        if not args.silent:
           print('[{0}] Prepatch: failure - unable to clean cache'.format(host))
        exit(2)
    else:
        yc_fail = 'pass'
        logger.info('Yum cache cleaned successfully')
        logger.info('Yum Output: {0}'.format(out))


def get_pkg_list():
    '''
    Gets list of packages marked for upgrade
    RETURNS: list of packages marked for upgrade or fail, error message
    '''
    exclude  = ('Load', 'base', 'updates', 'Update')
    yum      = 'yum -q list updates '
    repo     = '--disablerepo=* --enablerepo=base --enablerepo=updates '
    extra    = '--nogpgcheck --skip-broken --exclude=mysql* --exclude=nrpe* --exclude=nagios*'
    cmd      = yum + repo + extra
    updates  = {}  # initiate empty dictionary

    pkgs     = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = pkgs.communicate()

    if pkgs.returncode != 0:
        logger.warning('Error getting package list: {0}'.format(err))

        return {'fail': err}

    else:
        for line in out.splitlines():
            if line.startswith(exclude):
                continue
            else:
                output         = line.split()
                pkg, ver, repo = output
                updates[pkg]   = ver
            
        return updates


def download_packages():
    '''
    Downloads packages for update phase.  Ensures working yum service
    RETURNS: pass/fail, output of error message if exists
    '''
    # yum update --downloadonly
    update         = 'yum -y -q update --downloadonly '
    repo           = '--disablerepo=* --enablerepo=base --enablerepo=updates '
    extra          = '--nogpgcheck --skip-broken --exclude=mysql* --exclude=nrpe* --exclude=nagios*'
    cmd            = update + repo + extra
    download       = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    dp_out, dp_err = download.communicate()
    
    if download.returncode != 0:
        dl_fail = 'fail'
        logger.warning('Unable to download updates. \n \tError: {0}'.format(dp_err))
        dl_fail, dl_error
    else:
        dl_fail = 'pass'
        logger.info('Packages successfully downloaded and staged for update')
        logger.debug('Yum Output: {0}'.format(dp_out))
        return dl_fail, None
    

def check_network(repo_host, port):
    '''
    checks and times tcp response time for specified server and port
    REQUIRES:  hostname to check and port
    PROVIDES:  return status of zero on success and exit with error code 2 on failure
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # Sets timeout for connecction to prevent hanging

    try:
        sock.connect((repo_host, int(port)))
    except Exception as e:
        sock.close()
        logger.critical('TCP FAIL to host {0} on port {1}'.format(repo_host, port))
        logger.exception('Connectivity check fail')
        print('[{0}] Network check failed to {1}'.format(host, e))
        exit(3)
    else:
        sock.close()
        logger.info('TCP OK - {0}'.format(repo_host))

    return 0 


def check_disks(fs_list):
    '''
    For partition and free space specified, return pass or fail if that partion has available space remaining
    REQUIRES: dictionary of filesystems and minimum space
    PROVIDES: Returns pass/failure status and list of failed devices
    '''
    failures = {}
    for partition, mb in fs_list.iteritems():
        msg, size = check_fs_size(partition, mb)
        if msg == 'fail':
            failures[partition] = size
            fail = 'fail'
            logger.warning('Partition Check FAIL: {0}: {1}'.format(partition, mb))
        else:
            logger.info('Partition Check PASS: {0}'.format(partition))
            fail = 'pass'

    update_status('check_disks', fail, details=failures)    
    return fail, failures

def parse():
    '''
    Parse command line arguments
    - check only : runs checks but does not set status file
    - force      : only sets status file.  Run this as a last resort if you need to skip prepatch
    - silent     : no output on success.  only critical failure output
    - fail       : used for testing.  updates status file with failure status
    '''
    parser = ArgumentParser(description='Run a series of tests to ensure system is ready for patching.')
    parser.add_argument('-c', '--check_only', action='store_true', dest='check',  help='Run quick health check only')
    parser.add_argument('-f', '--force',      action='store_true', dest='force',  help='Force successful prepatch status.  Not advised')
    parser.add_argument('-a', '--autopatch',  action='store_true', dest='auto',   help='Flag used for automation')
    parser.add_argument('-s', '--silent',     action='store_true', dest='silent', help='Silent mode.  No output to terminal')
    parser.add_argument('-F', '--fail',       action='store_true', dest='fail',   help='Show failure status for testing')

    return parser.parse_args()


def main ():
    # Declare global variables
    global host
    global args

    # Get hostname
    host = uname()[1]

    # Parse arguments
    args = parse()

    # Initialize fail_message dictionary
    fail_message = {}

    # Need to be root to run (not atcually needed)
    verify_root()

    # Write status and exit without checks if force == True
    if args.force:
        update_status('prepatch', 'success')
        print('[{0}] Prepatch - completed: success'.format(host))
        exit(0)

    # Write failure status without checking 
    if args.fail:
        update_status('prepatch', 'failure', 'Failure via flag: testing')
        print('[{0}] Prepatch - completed: failure'.format(host))
        exit(1)



    '''
    Pass/Fail Tests...
    These will exit immediately on fail
    '''

    # Check connectivity to yum server
    # This will exit on failure
    check_network(check_server, check_port)

            
    #Clean yum
    if not args.check: 
        clean_yum()


    '''
    Pass/Continue Tests...
    These will contiue on fail but append status
    '''

    # Check Filesystem sizes
    disk_status, disk_fails = check_disks(fs_list)
    if disk_status == 'fail':
        fail_message['disk'] = disk_fails

    # Download packages for later install
    dp_fail, dp_err = download_packages()
    if dp_fail     == 'fail':
        fail_message['yum_download'] = dp_err

    # write list of pending updates to tmp file
    # /tmp/update_list-YYYY-MM.txt
    pkg_list = get_pkg_list()
    if 'fail' in pkg_list.keys():
        logger.warning('Error returning update list. {0}'.format(pkg_list['fail']))
    else:
        # get date
        tday = datetime.now()
        package_file = 'update_list-{0}.txt'.format(tday.strftime('%Y-%m'))
        with open('/tmp/{0}'.format(package_file), 'w') as f:
            f.write(str(pkg_list))
    
    # check installed kernel count
    k = get_kernel_count()
    if args.check:
        logger.info('Running in check only mode.  Kernel count: {0}'.format(k))
    else:
        if k < 2:
            logger.warning('Currently there are only {0} installed kernels'.format(k))
        elif k == 2:
            logger.info('There are 2 kernels installed.  No need to trim.')
        else:
            # clean_kernels won't append status as this is not a significant failure
            status, koutput = clean_kernels(kern_num)
            if status == 'pass':
                logger.info('Kernels cleaned - Prepatch.  Trimmed down to {0} kernels'.format(kern_num))
                logger.info('Yum Output: {0}'.format(koutput))
            else:
                logger.warning('Unable to clean kernels. Error: {0}'.format(koutput))

    # If any critical functions have failed, fail_message will eval to True
    if args.check:
        logger.info('Running in check only mode.  Completed')
        logger.info(fail_message)
        if not args.silent:
           print('[{0}] Check only mode failures: \n{1}'.format(host, fail_message))
    elif fail_message:
        update_status('prepatch', 'failed', fail_message)
        if not args.silent:
           print('[{0}] Prepatch - failed: {1}'.format(host, fail_message))
    else:
        update_status('prepatch', 'success')
        if not args.silent:
            print('[{0}] Prepatch - completed: success'.format(host))
        
        exit(0)
    

if __name__ == '__main__':
    main()
