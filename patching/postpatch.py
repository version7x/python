#!/bin/env python

from __future__ import print_function

from patch_actions import check_status, update_status, clean_kernels
from patch_actions import verify_root, verify_status
from datetime import datetime, timedelta
from argparse import ArgumentParser
from sys import exit
from os import uname
import logging

kern_num   =  2
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


def get_status_details():
    '''
    This function reads in the data from the patch status file
    - It looks to see (by file timestamp) if patching was done in last day
    - It then looks to see if there were errors returned from patching process
    - Finally, it updates the patch status file with "timestamp patch   success"
    RETURNS: 0 on success
    '''
    stage, result, details, timestamp, then = verify_status(silent)

    # Checks to see if patching was done in last day
    # This may need to be revisited if use is to
    #   verify more than one day later
    if  then > timestamp:
        logger.warning("Patch out of date.  Re-run Patch")
        return 'Patch out of date.  Re-run patching'


    #   Verifies patching was sucessful before continuing 
    if stage == 'patch'  and result == 'success':
        logger.info('Successful patch verified. Continuing.')
        return 0
    else:
        logger.warning('Patching sucess not verified. {0} - {1}: {2} '.format(stage, result, details))
        return 'Possible issue with patching'


#def verify_pkgs():
#    # Verify uptime
#    tday = datetime.now()
#    package_file = 'update_list-{1}.txt'.format(tday.strftime('%Y-%m'))
#    try:
#        with open('/tmp/{1}'.format(package_file), 'r') as f:
#            pkg_list = f.readlines()



def cleanup(kern_num):
    '''
    Re-trim kernels to number specified
    '''
    status, koutput = clean_kernels(kern_num)
    if status == 'pass':
        logger.info('Kernels cleaned - Postpatch.  Trimmed down to {0} kernels'.format(kern_num))
        logger.info('Yum Output: {0}'.format(koutput))
        return 0
    else:
        logger.warning('Unable to clean kernels - POSTPATCH. Error: {0}'.format(koutput))
        return 'cleanup fail'    



def final_status(status, error='No errors'):
    '''
    Final updates to logs and status file
    If pre/patch/post run successfully status will show Patching complete
    Otherwise something else will display
    '''
    code, status_error = update_status('postpatch', status)
    if code != 0:
        logger.warning('Could not update status file: {0}'.format(status_error))
        return 1
    else:
        return 0

def parser():
    '''
    Parse command line arguments:
    - autopatch : Currently not used at this phase
    - silent    : Suppress output to user on screen
    '''   
    parser = ArgumentParser(description='Verifies output from update commands and posts status')
    parser.add_argument('-a', '--autopatch',   action='store_true',  dest='auto_patch', help='Flag used for framework')
    parser.add_argument('-s', '--silent',      action='store_true',  dest='silent',     help='Silent - repress output')

    return parser.parse_args()


def remove_cmd():
    '''
    Cleanup of chaining cron from /etc/rc.d/rc.local
    '''
    cmd = script_dir + 'postpatch.py'
    try:    
        with open(cron_file, 'r') as f:
            output = f.readlines()
    except Exception as e:
        logger.warning('Failed to read crontab. Error: {0}'.format(e))
        rt = e
    else:
            logger.info('Postpatch: read in crontab')
            try:    
                with open (cron_file, 'w+') as f:
                    for line in output:
                        if not line.startswith(cmd):
                            f.write(line)
            except Exception as E:
                logger.warning('Failed to update crontab. Error: {0}'.format(E))
                logger.exception('Update error')
                rt = E
            else:
                logger.info('Postpatch: updated crontab')
                rt = 0
    
    return rt




def main():
    # Set global variable
    global host
    args = parser()
    host = uname()[1]

    # Suppress output if true
    global silent
    if args.silent:
        silent = True
    else:
        silent = False

    # Create an empty dictionary to track failures
    failures = {}
    
    # Need to be root to run
    verify_root()

    # Verify patch success will log and exit on error
    a = get_status_details()
    if a != 0:
        logger.warning('Patching process completed with errors')
        print('[{0}] postpatch failed'.format(host))
        exit(30)

    # Trims kernel down to kern_num as specified
    b = cleanup(kern_num)
    if b != 0:
        logger.warning('Postpatch completed with cleanup error')
        update_status('postpatch', 'complete-error', 'cleanup error')
        failures['cleanup'] = 'failed'

    #Remove cron entry from /etc/rc.d/rc.local
    c = remove_cmd()
    if c != 0:
        logger.warning('Error removing cron entry.  Error: {0}'.format(c))
        failures['rem_cron'] = 'failed'

    # Determine if there was an issues with kernel cleanup or removing cron entry 
    if b != 0 or c != 0:
        logger.warning('Postpatch - complete with errors: {0}'.format(failures))
        final_status('failed', failures)
        if not silent:
            print('[{0}] Patching complete, but minor errors occured during postpatch: {1}'.format(host, failures))
        exit(31) 
    else:
        logger.info('Postpatch - complete: successful')
        update_status('patching', 'complete')
        if not silent:
            print('[{0}] Patching Success'.format(host))
        exit(0)

if __name__ == '__main__':
    main()
