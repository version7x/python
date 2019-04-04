#!/bin/env python

import argparse
import datetime
import socket
import sys

def check_tcp(host, port):
    '''
    checks and times tcp response time for specified server and port
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # Sets timeout for connecction to prevent hanging

    try:
        start = datetime.datetime.now()
        sock.connect((host, int(port)))
        end   = datetime.datetime.now()
    except Exception as e:
        sock.close()
        print(e)
        print('TCP FAIL on port %', % (port))
        sys.exit(2)
    else:
        sock.close()
        total_time = end - start
        print('TCP OK - %s', % (str(total_time.microseconds)))
        sys.exit(0)

def main():
    '''
    parse args and set variables
    pass them to check_tcp
    '''
    parser = argparse.ArgumentParser()
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--domain', action='store_true', dest='dom', default=False,
                        help='Hostname to check')
    group.add_argument('-s', '--server', action='store', dest='host',
                        help='Hostname to check')
    parser.add_argument('-p', '--port', action='store', dest='port', required=True,
                        help='Port to check')
    
    results = parser.parse_args()

    if results.dom == True:
        domain = socket.getfqdn().split('.', 1)[1]
        print('Checking domain: %s' % (domain))
        check_tcp(results.host, results.port)\

if __name__ == '__main__':
    main()