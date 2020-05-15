#!/bin/env python

from __future__ import print_function

from patch_actions import verify_status
from argparse import ArgumentParser
from subprocess import Popen, PIPE
from os import uname, system
from time import sleep
from sys import exit
import logging


'''
EXIT CODE MAP
01 == 'Actions   - Unable to read status file'
02 == 'Actions   - Must be run as root'
10 == 'Actions   - Unable to preform yum clean'
11 == 'Prepatch  - Unable to contact yum service'
12 == 'Prepatch  - test (failure requested)'
13 == 'Prepatch  - Various errors -disk, yum repo, kernel count'
20 == 'Patching  - Prepatch not completed successfully'
21 == 'Patching  - Prepatch not preformed recently'
22 == 'Patching  - Unable to read redhat-release file'
23 == 'Patching  - Unable to set cron execute bit'
24 == 'Patching  - CentOS release variable not expected'
25 == 'Patching  - Yum update error - patching failure'
30 == 'Postpatch - Previous status does not show patch success'
31 == 'Postpatch - Patching successful, but cleanup failed'
'''

global script_dir
script_dir = '/usr/local/bin/patching/'
#cron_file = '/etc/rc.d/rc.local'

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
    parser.add_argument('-K', '--kernelonly',  action='store_true',  dest='kernel',  help='Update kernel only')
    parser.add_argument('-k', '--kernelfirst', action='store_true',  dest='first',   help='Run update twice. First time for kernel only')
    parser.add_argument('-v', '--verbose',     action='store_true',  dest='verbose', help='Display all output')
    parser.add_argument('-w', '--wall',        action='store_true',  dest='wall',    help='Send warning message to logged in users before reboot')
    parser.add_argument('-f', '--force',       action='store_true',  dest='force',   help='Force successful prepatch status.  Not advised')
    parser.add_argument('-F', '--fail',        action='store_true',  dest='fail',    help='Show failure status for testing')
    parser.add_argument('-s', '--silent',      action='store_true',  dest='silent',  help='Silent - repress output')
    parser.add_argument('-V', '--verify',      action='store_true',  dest='verify',  help='Verify patching status after patching has been attempted')
    parser.add_argument('-n', '--nodelay',     action='store_true',  dest='nodelay', help='Do not delay reboot by default 300 seconds')
    parser.add_argument('-R', '--noreboot',    action='store_false', dest='reboot',  help='Stop auto reboot after patching.')
    #parser.add_argument('-c', '--check_only', action='store_true',  dest='check',   help='Run quick health check only')
    

    return parser.parse_args()

def code_mapper(code):
    if code   == 1:
        msg   = 'Actions   - Unable to read status file'
    elif code == 2:
        msg   = 'Actions   - Must be run as root'
    elif code == 10:
        msg   = 'Actions   - Unable to preform yum clean'
    elif code == 11:
        msg   = 'Prepatch  - Unable to contact yum service/network error'
    elif code == 12:
        msg   = 'Prepatch  - test (failure requested)'
    elif code == 13:
        msg   = 'Non-critical precheck validation error (disk, yum repo, kernel count). See logs'
    elif code == 20:
        msg   = 'Patching  - Prepatch not completed successfully'
    elif code == 21:
        msg   = 'Patching  - Prepatch not preformed recently'
    elif code == 22:
        msg   = 'Patching  - Unable to read redhat-release file'
    elif code == 23:
        msg   = 'Patching  - Unable to set cron execute bit'
    elif code == 24:
        msg   = 'Patching  - CentOS release variable not expected'
    elif code == 25:
        msg   = 'Patching  - Yum update error - patching failure'
    elif code == 30:
        msg   = 'Postpatch - Previous status does not show patch success'
    elif code == 31:
        msg   = 'Postpatch - Patching successful, but cleanup failed'
    else:
        msg   = 'Script writer missed something - check logs'
    
    return msg


def run_stage(stage, args):
    cmd       = script_dir + stage + '.py' + ' ' + args
    action    = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err  = action.communicate()

    if action.returncode == 0:
        return 0, None
    else:
        if err:
            logger.warning('Function: run_stage ' + err)
        return action.returncode, out

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


def main():
    global host
    global verbose

    host        = uname()[1]
    pre_fail    = 'Prepatch Failed'
    patch_fail  = 'Patching Failed'
    args        = parse()

    if not args.silent:
        silent = False
        

    # Start with verify if called and then exit
    if args.verify:
        stage, result, details, timestamp, then = verify_status(silent)
        if then > timestamp:
            message = 'Not run recently.  Re-Run update'
            logger.warning(message)
            logger.debug('Timestamp: {0}, Then: {1}'.format(timestamp, then))
            print('[{0}] Patching out of date.  Re-Run update.py'.format(host))
            exit(40)
        elif stage != 'patching':
            logger.info('Incomplete patch run - {0}: {1} - {2}'.format(stage, result, details))
            print('[{0}] INCOMPLETE patch run - {1}: {2} - {3}'.format(host, stage, result, details))
            exit(41)
        elif stage == 'patching' and result == 'complete':
            logger.info('Patch run successfully verified')
            print('[{0}] Patching Complete'.format(host))
            exit(0)
        elif stage == 'patching' and result != 'complete':
            logger.critical('Possible patching failure. Patching: {0} - {1}'.format(stage, result))
            print('[{0}] Patching FAILED - {1}:{2}'.format(host, result, details))
            exit(41)
        elif stage == 'postpatch':
            logger.warning('Postpatch failure= {0} : {1}'.format(result, details))
            print('[{0}] Postpatch FAILED: Investigation needed.  {1}-{2}: {3}'.format(host, stage, result, details))
            exit(42)
        else:
            logger.critical("Unknown error.  STAGE: {0}, RESULT: {1}, DETAILS: {2}".format(stage, result, details))
            print('[{0}] INVESTIGATION REQUIRED.  See logs and status file')
            exit(43)

    
    if args.verbose:
        verbose = ''
    else:
        verbose = '--silent '
    
    if args.force:
        force   = '--force '
    else:
        force   = ''
    
    if args.fail:
        fail    = '--fail '
    else:
        fail    = ''
    
    # Prepatch Run
    pre         = force + ' ' + verbose + fail #+ ' ' + check 
    pre_string  = ''.join(pre)
    #prepatch   = script_dir +'prepatch.py ' + pre_string

    pre_code, status     = run_stage('prepatch', pre_string)
    if pre_code != 0:
        out = code_mapper(pre_code)
        logger.critical('{0} - {1}. Details: {2}'.format(pre_fail, pre_code, out))
        logger.critical('Command Output: {0}'.format(status))
        if verbose:
            print('[{0}] {1} - {2}. Details: {3}'.format(host, pre_fail, pre_code, out))
        exit(pre_code)
    

    # Patch Run
    # Determine upgrade type
    if args.kernel:
        kernel = '--kernelonly '
    elif args.first:
        kernel = '--kernelfirst '
    else:
        kernel = ''
    
    # Set Silent flag
    if args.silent:
        silent = True
    # Reboot now vs default 300 seconds/5 min reboot
    if args.nodelay:
        delay  = None
    else:
        delay  = 300
    # Set wall flag (reboot warning)
    if args.wall:
        wall   = '--wall '
    else:
        wall   = ''

    patch          = '--autopatch --noreboot --silent ' + kernel + verbose + wall
    patch_string   = ''.join(patch)
    patch_code, output = run_stage('patch' , patch_string)
    if patch_code != 0:
        out = code_mapper(patch_code)
        logger.critical('[{0}] - {1}. Details: {2}'.format(patch_fail, patch_code, out))
        logger.critical('Command output: {0}'.format(output))
        if verbose:
            print('[{0}] {1} - {2}. Details: {3}'.format(host, patch_fail, patch_code, out))
        exit(patch_code)
    else:
        if verbose:
            print('[{0}] Patch Success.'.format(host))
        #if not silent:
        #    print('[{0}] Patch Success.  Rebooting'.format(host))

    # Restart system
    if args.reboot  == False:
        reboot      = False
    else:
        reboot      = True
    if reboot       == True:
        restart('All patches applied.  Rebooting as part of patch process in {0} seconds.'.format(delay), delay, wall)
    else:
        message     = 'All patches applied.  No-reboot specified'
        logger.info(message)
        if not silent:
            print('[{0}] Patch - successful: {1}'.format(host, message))
  

if __name__ == '__main__':
    main()
