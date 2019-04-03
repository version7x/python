#!/bin/env python

from __future__ import print_function
from subprocess import check_call
from argparse   import ArgumentParser

def get_out():
    pass

def check_status(service):
    '''
    Takes service name as argument and checks it's check_status
    '''
    print("=====================")
    print(service)
    try:
        service_out = check_call(['/bin/systemctl', 'is-active'] + [service])
        if service_out == 3:
            print("%s not running" % (service))
    except Exception as e:
        get_out

def kill(service):
    '''
    Takes service name as an argument and kills the service
    '''
    kill_out = check_call(['/bin/sudo', '/bin/systemctl', 'stop'] + [service])
    if kill_out == 0:
        print("%s: successfully stopped" % (service))
    else:
        print("%s: Error stopping.   Check logs. %s" % (service, kill_out))

def start(service):
    '''
    Takes a service name as an argument and starts that service
    '''
    start_out = check_call(['/bin/sudo', '/bin/systemctl', 'stop'] + [service])
    if start_out == 0:
        print("%s: successfully started" % (service))
    else:
        print("%s: Error Starting.  Check logs. %s" % (service, start_out))

def re_start(service):
    '''
    Takes a service name as an argument and calls kill() and start() on that service
    '''
    kill(service)
    start(service)

def parse():
    parser = ArgumentParser()
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-r', '--restart', action='store_true', dest='restart', help='Restart Service')
    group1.add_argument('-s', '--start',   action='store_true', dest='start',   help='Start Service')
    group1.add_argument('-k', '--kill',    action='store_true', dest='kill',    help='Kill Service')
    group1.add_argument('-S', '--status',  action='store_true', dest='status',  help='Check Service Status')

    group2 = parser.add_argument_group()
    group2.add_argument('-f', '--frontent', action='store_true', dest='front', help='Front End Services')
    group2.add_argument('-b', '--backend',  action='store_true', dest='back',  help='Back End Services')
    group2.add_argument('-c', '--core',     action='store_true', dest='core',  help='Core Services')
    group2.add_argument('-a', '--all',      action='store_true', dest='stack', help='All Services')

    return parser.parse_args()

def main():
    '''
    Defines lists of services to take action on base on services lists, then takes action provided
    '''
    front_end = ['httpd', 'uchiwa', 'sensu-server', 'sensu-api']
    back_end  = ['sensu-server', 'rabbitmq-server', 'redis']
    core      = ['sensu-server', 'sensu-api', 'sensu-client']
    stack     = ['httpd', 'uchiwa', 'sensu-server', 'sensu-api', 'sensu-client', 'rabbitmq-server', 'redis']

    args = parse()

    if args.front:
        s_list = front_end
    elif args.back:
        s_list = back_end
    elif args.core:
        s_list = core
    elif args.stack:
        s_list = stack

    if args.start:
        for service in s_list:
            start(service)
    if args.kill:
        for service in s_list:
            kill(service)
    if args.restart:
        for service in s_list:
            re_start(service)
    if args.status:
        for service in s_list:
            check_status(service)
            print("=====================")

if __name__ == '__main__':
    main()
