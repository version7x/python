#!/bin/env python

from patch_actions import update_status, check_fs_size
from subprocess import Popen, PIPE
from os import getuid
from sys import exit


# Dictionary of filesystems to check along with size in MB
# Consider putting fs_list and net_host in config file
fs_list = { '/var': 500, '/var/log': 100, '/': 1000, '/boot': 60}

clean_yum():
    # package-cleanup -y --oldkernels --count=2
    # clean yum clean all
    clean = Popen('yum clean all', shell=True, stdout=PIPE, stderr=PIPE)
    out, err = clean.communicate()
    if clean.returncode != 0:
        yc_fail = 'fail'
        logger.critical('Unable to clean yum cache. Error: {0}'.format(err))
        update_status('yum_clean', yc_fail, err)
        exit(2)
    else:
        yc_fail = 'pass'
        logger.info('Yum cache cleaned successfully')

download_packages():
    # yum update --downloadonly
    download = Popen('yum update --downloadonly', shell=True, stdout=PIPE, stderr=PIPE)
    out, err = download.communicate()
    
    if download.returncode != 0:
        dl_fail = 'fail'
        logger.warning('Unable to download updates. Error: {0}'.format(err))
        return dl_fail, err
    else:
        dl_fail = 'pass'
        logger.info('Packages successfully downloaded and staged for update')
        return dl_fail, err
    

check_network(repo_host):
    # Will need cross domain hostname (e.g. kickstart)
    # Also need a host with good network to test from
    pass 

clean_kernels():
    # package-cleanup -y --oldkernels --count=${kern_num}
    kernels = Popen('/bin/package-cleanup -y --oldkernels --count=3, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = kernels.communicate()
    
    if kernels.returncode != 0:
        cc_fail = 'fail'
        logger.warning('Unable to clean kernels. Error: {0}'.format(err))
        return cc_fail, err
    else:
        cc_fail = 'pass'
        logger.info('Kernels cleaned.  Trimmed down to 3 kernels')
        return cc_fail, err

check_disks(fs_list):
    failures = {}
    for partition, mb in fs_list.iteritems():
        msg, size = check_fs_size(parition, mb)
        if msg == fail:
            failures[partition] = size
            fail = 'fail'
            logger.warning('Partition Check FAIL: {0}: {1}'.format(parition, mb))
        else:
            logger.info('Partition Check PASS: {0}'.format(partition))
            fail = 'pass'

    update_status('check_disks', fail, details=failures)    
    return fail, failures


def main ():
    logging.basicConfig(
    level    = logging.WARNING,
    format   = "%(asctime)-10s %(levelname)s %(message)",
    filename = '/var/log/patching.log'
    )

    logger = logging.getLogger(__name__)

    fail_status  = 'pass'
    fail_message = {}
    
    '''
    Pass/Fail Tests...
    These will exit immediately on fail
    '''
    # Verify user is root
    if os.getuid() != 0;
        logger.critical("Attempted to run as non-root user")
        print('You must be root to run this script')
        exit(2)

    # Clean yum
    clean_yum()

    '''
    Pass/Continue Tests...
    These will contiue on fail but append status
    '''
    # Check Filesystem sizes
    disk_status, disk_fails = check_disks(fs_list)
    if disk_status == 'fail':
        fail_message['disk'] = disk_fails

    yd_fail, yd_err = yum_download()
    if yd_fail     == 'fail':
        fail_message['yum_download'] = yd_err

    # clean_kernels won't append status as this is not a significant failure
    clean_kernels()

    if fail_message:
        update_status('prepatch', 'failed', fail_message)
    else:
        update_status('prepatch', 'completed')
)

if __name__ == '__main__':
    main()