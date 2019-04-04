#/bin/env python

'''
Makes a TCP connection to a service running on localhost
if no connection is made, we attempt to restart service
'''

from common import check_tcp
import subprocess
import logging
import sys

hostname    = 'localhost'
port        = 5671
servicename = 'rabbitmq-server'

logging.basicConfig(
    level    = logging.DEBUG,
    format   = '%(asctime)-10s %(levelname)s %(message)s',
    filename = '/var/log/rabbit-check.log'
)

logger = logging.getLogger(__name__)

# Call check_tcp method to test daemon
rc, output, response_time, text = check_tcp(hostname, port)

if rc == 0:
    logger.info(text)
    sys.exit(0)
else:
    command = ['/bin/systemctl', 'restart', service_name]
    ret     = subprocess.call(command)
    if ret == 0:
        lstring = '%s restarted successfully. Output: %s' % (servicename, text)
        logger.debug(lstring)
    else:
        lstring = '%s failed restart.  Output: %s' % (servicename, text)