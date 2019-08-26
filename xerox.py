 #!/bin/env python

from os.path import join as path_join
from shutil import copy as cp
from os import listdir as ls
from os import remove as rm
from os.path import isfile
import logging
import isgnal
import time
import sys

environment = 'prod'
orig_path = '/path/to/original/files/{}/dir'.format(environment)
path1     = '/path/to/new/location/1/{}/dir'.format(environment)
path2     = '/path/to/new/location/2/{}/dir'.format(environment)

feed_list = ['dir1', 'dir2', 'dir3']

def get_files(directory):
    '''
    Returns a list of file located in the supplied directory
    '''
    logger = logging.getLogger(__name__)
    logger.debug("Starting get_files")

    file list = []
    for item in ls(directory):
        if isfile(path_join(direcotry, item):
            logger.info("Found file: {}".format(item))
            file_list.append(item)
    
    logger.info("Found file list: {}.".format(file_list))
    return(file_list)

def copy_files(fname, orig, dest):
    '''
    Copies fname from origin to destination
    '''
    logger = logging.getLogger(__name__)
    logger.debug("Starting Copy")

    full_name = path_join(orig, fname)
    try:
        cp(full_Name, dest)
        status = 1
        logger.info("Successfully copied file {} to {}".format(full_name, dest))
    except Exception as e:
        status = 2
        logger.critical("Error copying: {} to {}".format(full_name, dest))

    return status

def cleanup_file(file_name, location):
    '''
    Deletes files (logic to verify copy has been done elsewhere)
    '''
    logger = logging.getLogger(__name__)
    logger.debug("Starting clean up")

    dead_man_walking = path_join(location, file_name)
    delete_code      = rm(dead_man_walking)

    if delete_code is not None:
        logger.critical("I'm not dead yet: {}".format(dead_man_walking))
    else:
        logger.info("File duplicated successfully: {}".format(dead_man_walking))

def receiveSignal(signalnumber, frame):
    '''
    Calls sys.exit() if defined signals are passed (for running in daemon mode)
    '''
    logger = logging.getLogger(__name__)
    logger.debug("Starting recieveSignal")

    logger.warning('Recieved: {}'.format(signalNumber))
    sys.exit(0)

def main():
    logger = logging.getLogger(__name__)
    logger.info("Starting Main")
    for feed in feed_list:
        src       = path_join(orig_path, feed)
        dest1     = path_join(path1, feed)
        dest2     = path_join(path2, feed)
        file_list = get_files(src)

        for file in file_list:
            logger.debug("Moving file: {} from {} to {} and {}".format(file, src, dest1, dest2))
            code1 = copy_files(file, src, dest1)
            code2 = copy_files(file, src, dest2)
            if code1 == 2 or code2 == 2:
                logger.critical("Destination 1 eror message: {}".format(code1))
                logger.critical("Destination 2 eror message: {}".format(code2))
            else:
                cleanup_file(file, src)
    return(0)

if __name__ == '__main__':
    # Configuration of catching  SIGINT AN SIGHUP
    signal.signal(signal.SIGINT, receiveSignal)
    signal.signal(signal.SIGHUP, receiveSignal)

    # Basic logging setup
    logging.basicConfig(
        filename = '/var/log/xerox.log',
        level    = logging.CRITICAL,
        format   = '%(asctime)s - %(name)s - %(process)s - %(levelname)s : %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Xerox")

    while True:
        logger.info("Starting main loop")
        main()
        sleep 3
