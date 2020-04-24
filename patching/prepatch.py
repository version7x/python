#!/bin/env python

from patch_actions import update_status, check_fs_size
from subprocess import Popen, PIPE
from argparse import ArgumentParser
from os import getuid
from sys import exit
import logging


# Dictionary of filesystems to check along with size in MB
# Consider putting fs_list and net_host in config file
fs_list = { '/var': 500, '/var/log': 100, '/': 1000, '/boot': 60}

def clean_yum():
    # package-cleanup -y --oldkernels --count=2
    # clean yum clean all
    clean = Popen('yum clean all', shell=True, stdout=PIPE, stderr=PIPE)
    out, err = clean.communicate()
    if clean.returncode != 0:
        yc_fail = 'fail'
        logger.critical('Unable to clean yum cache. Error: {}'.format(err))
        update_status('yum_clean', yc_fail, err)
        exit(2)
    else:
        yc_fail = 'pass'
        logger.info('Yum cache cleaned successfully')
        logger.info('Yum Output: {}'.format(out))


def get_pkg_list():
    exclude  = ('Load', 'base', 'updates', 'Update')
    cmd      = 'yum list updates'
    repo     = '--disablerepo=* --enablerepo=base --enablerepo=updates'
    extra    = '--nogpgcheck --skip-broken --exclude=mysql* --exclude=nrpe* --exclude=nagios*'
    updates  = {}

    pkgs     = Popen([cmd, repo, extra], shell=True, stdout=PIPE, stderr=PIPE)
    out, err = pkgs.communicate()

    if pkgs.returncode != 0:
        logger.warning('Error getting package list: {}'.format(err))

    for line in out.splitlines():
        if line.startswith(exclude):
            continue
        else:
            output         = line.split()
            pkg, ver, repo = output
            updates[pkg]   = ver
    
    return updates


def download_packages():
    # yum update --downloadonly
    download = Popen('yum update --downloadonly', shell=True, stdout=PIPE, stderr=PIPE)
    dp_out, dp_err = download.communicate()
    
    if download.returncode != 0:
        dl_fail = 'fail'
        logger.warning('Unable to download updates. Error: {}'.format(dp_err))
        return dl_fail, dp_err
    else:
        dl_fail = 'pass'
        logger.info('Packages successfully downloaded and staged for update')
        logger.info('Yum Output: {}'.format(dp_out))
        return dl_fail, dp_err
    

def check_network(repo_host):
    # Will need cross domain hostname (e.g. kickstart)
    # Also need a host with good network to test from
    return 0 

def clean_kernels():
    # package-cleanup -y --oldkernels --count=${kern_num}
    kernels = Popen('/bin/package-cleanup -y --oldkernels --count=3', shell=True, stdout=PIPE, stderr=PIPE)
    ck_out, ck_err = kernels.communicate()
    
    if kernels.returncode != 0:
        ck_fail = 'fail'
        logger.warning('Unable to clean kernels. Error: {}'.format(ck_err))
        return ck_fail, ck_err
    else:
        ck_fail = 'pass'
        logger.info('Kernels cleaned.  Trimmed down to 3 kernels')
        logger.info('Yum Output: {}'.format(ck_out))
        return ck_fail, ck_err

def check_disks(fs_list):
    failures = {}
    for partition, mb in fs_list.iteritems():
        msg, size = check_fs_size(partition, mb)
        if msg == 'fail':
            failures[partition] = size
            fail = 'fail'
            logger.warning('Partition Check FAIL: {}: {}'.format(partition, mb))
        else:
            logger.info('Partition Check PASS: {}'.format(partition))
            fail = 'pass'

    update_status('check_disks', fail, details=failures)    
    return fail, failures

def parse():
    parser = ArgumentParser()
    parser.add_argument('-c', '--check_only', action='store_true', dest='check',      help='Run quick health check only')
    #parser.add_argument('-a', '--autopatch',  action='store_true', dest='auto_patch', help='Flag used for automation')

    return parser.parse_args()


def main ():
    fail_message = {}
    
    #args = parse()

    '''
    Pass/Fail Tests...
    These will exit immediately on fail
    '''
    # Verify user is root
    if getuid() != 0:
        logger.critical("Attempted to run as non-root user")
        print('You must be root to run this script')
        exit(2)

    # Check connectivity to yum server
    #net_check = check_network('kickstart')
    #if net_check != 0:
    #    logger.critical("Cannot verify connectivity.  Error: {}".format(net_check))
    #    exit(8)

            
    #Clean yum
    clean_yum()

    '''
    Pass/Continue Tests...
    These will contiue on fail but append status
    '''


    # Check Filesystem sizes
    disk_status, disk_fails = check_disks(fs_list)
    if disk_status == 'fail':
        fail_message['disk'] = disk_fails

    dp_fail, dp_err = download_packages()
    if dp_fail     == 'fail':
        fail_message['yum_download'] = dp_err

    # clean_kernels won't append status as this is not a significant failure
    clean_kernels()

    if fail_message:
        update_status('prepatch', 'failed', fail_message)
    else:
        update_status('prepatch', 'completed')


if __name__ == '__main__':
    logging.basicConfig(
        level    = logging.WARNING,
        format   = "%(asctime)-10s %(levelname)s %(message)",
        filename = '/var/log/patching.log'
    )

    logger = logging.getLogger(__name__)

    main()
