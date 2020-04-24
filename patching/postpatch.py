#!/bin/env python

from patch_actions import check_status, update_status
from datetime import datetime, timedelta
import logging
import sys


def verify_patch_success():
    # Verify patch status
    f         = check_status()
    data      = f.readline()
    now       = datetime.now()
    then      = now - timedelta(days=1)
    t         = data[0:2]                                     # Return first 2 elements
    ts        = ("{} {}".format(t[0], t[1]))                  # Create string
    timestamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f") # Conver to datetime
    stage     = data[2]
    result    = data[3::]

    # Checks to see if patching was done in last day
    # This may need to be revisited if use is to
    #   verify more than one day later
    if  then > timestamp:
        logger.warning("Patch out of date.  Re-run Patch")
        sys.exit(5)
    # Checks to see if prepatch was a success
    #   or if we made it to patching but failed
    # Should rule out prepatch failures, patching success,
    #   and all postpatch  
    if stage == 'patch'  and result == 'success':
        logger.info('Successful patch verified. Continuing.')
        return 0
    else:
        logger.warning('Patching sucess not verified. {}: {}'.format(stage, result))
        sys.exit(6)


def verify_pkgs():
    # Verify uptime
    pass


def cleanup():
    # Re-trim kernels to number specified
    
    pass


def final_status():
    Final updates to logs and status file
    pass


def parser():
    # Process cmd line flags
    pass


def remove_cmd():
    # Cleanup of chaining cron
    pass


def main():
    pass


if __name__ == '__main__':
    logging.basicConfig(
        level    = logging.DEBUG,
        format   = '%(asctime)-10s %(levelname)s %(message)s',
        filename = '/var/log/patching.log'
    )

    logger = logging.getLogger(__name__)

    main()
