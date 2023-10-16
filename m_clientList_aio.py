#!/usr/bin/env python
import asyncio
import csv
import logging
import os
import sys

import meraki.aio

from argparse import ArgumentParser
from datetime import datetime

BOLD = '\033[1m'
ENDC = '\033[0m'
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
PURPLE = '\033[35m'
LGRAY = '\033[97m'
DGRAY = '\033[90m'

def csv_writer(clients):
    csvdir = os.path.join(os.getcwd(), "output")
    if not os.path.exists(csvdir):
        os.makedirs(csvdir)

    csvfile = f"{csvdir}/report_{datetime.now():%Y%m%d-%H%M%S}.csv"

    print(f"** Writing {csvfile}")

    with open(csvfile, 'w', newline='') as cf:
        fieldnames = ['network', 'device_name', 'switch_port', 'client_mac', 'ip', 'status', 'last_seen']
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for name in clients:
            net_name = name
            clients = clients[name]

            for c in clients:
                writer.writerow({
                    'network': net_name,
                    'device_name': c['recentDeviceName'],
                    'switch_port': c['switchport'],
                    'client_mac': c['mac'],
                    'ip': c['ip'],
                    'status': c['status'],
                    'last_seen': c['lastSeen'],
                })


async def getOrgs(aiodash, org_name=None, org_id=None):
    if org_id:
        result = await aiodash.organizations.getOrganization(org_id)
        logger.debug(f"organizations: {CYAN}{result}{ENDC}")
        return result
    elif org_name:
        organizations = await aiodash.organizations.getOrganizations()
        for result in organizations:
            if result['name'] == org_name and result['api']['enabled']:
                logger.debug(f"organizations: {CYAN}{result}{ENDC}")
                return result
    else:
        organizations = await aiodash.organizations.getOrganizations()
        result = [ org for org in organizations if org['api']['enabled']]
        logger.debug(f"organizations: {CYAN}{result}{ENDC}")
        return result
    

async def getNetworks(aiodash, org_id, net_name=None, tag=None):
    product_filter = "systemsManager"
    networks = await aiodash.organizations.getOrganizationNetworks(org_id,
                                                             perPage=1000,
                                                             total_pages='all')

    if net_name:
        for result in networks:
            if result['name'] == net_name:
                logger.debug(f"networks: {CYAN}{result}{ENDC}")
                return result
    else:
        result = []
        for net in networks:
            if product_filter not in net['productTypes']:
                result.append(net)
        logger.debug(f"networks: {CYAN}{result}{ENDC}")
        return result


async def getTemplates(aiodash, org_id):
    templates = await aiodash.organizations.getOrganizationConfigTemplates(org_id)
    logger.debug(f"templates: {CYAN}{templates}{ENDC}")
    return templates


async def getOrgClients(aiodash, org_id, mac):
    ''' returns a specific client by mac, no fuzzy search
    '''
    clients = await aiodash.organizations.getOrganizationClientsSearch(org_id, mac)
    logger.debug(f'Found {len(clients)} clients')
    logger.debug(f'clients: {BOLD}{clients}{ENDC}')
    return clients


async def getNetClients(aiodash, net_id, mac=''):
    ''' returns a list of client for a network, allows fuzzy search
    '''
    clients = await aiodash.networks.getNetworkClients(net_id,
                                                            mac=mac,
                                                            perPage=1000,
                                                            total_pages='all')
    logger.debug(f'Found {len(clients)} clients')
    logger.debug(f'clients: {BOLD}{clients}{ENDC}')
    return clients


async def main():
    async with meraki.aio.AsyncDashboardAPI(
        api_key=os.getenv("APIKEY"),
        base_url="https://api.meraki.com/api/v1",
        output_log=output_log,
        log_file_prefix=os.path.basename(__file__)[:-3],
        log_path=log_path,
        print_console=True,
        inherit_logging_config=False,
        use_iterator_for_get_pages=False,
        suppress_logging=suppress_logging,
        # single_request_timeout=12,
        maximum_concurrent_requests=50,
        maximum_retries=100,
        wait_on_rate_limit=True,
    ) as aiodash:
        print("** Gathering clients")

        try:
            org = await getOrgs(aiodash, org_name=org_name, org_id=org_id)

            net_tasks = []
            net_tasks.append(getNetworks(aiodash, org['id'], net_name=net_name))

            for n in asyncio.as_completed(net_tasks):
                networks = await n
                client_dict = {}
                for net in networks:
                    print(f"** Checking network: {PURPLE}{net['name']}{ENDC}")
                    c_tasks = []
                    check_net = set(products) & set(net['productTypes'])
                    if check_net:
                        print(f"** {GREEN}Getting clients{ENDC}")
                        c_tasks.append(getNetClients(aiodash, net['id'], mac=mac))
                    else:
                        print(f"** {YELLOW}Network does not include product type{ENDC}")

                    for c in asyncio.as_completed(c_tasks):
                        clients = await c
                        if len(clients) > 0:
                            client_dict[net['name']] = clients
                        else:
                            print(f"** {RED}No Clients in network {net['name']}{ENDC}")
            
            if SCREEN_OUTPUT:
                print()
                for name in client_dict:
                    network = name
                    clients = client_dict[name]
                    for client in clients:
                        device_name = client['recentDeviceName']
                        switch_port = client['switchport']
                        client_mac = client['mac']
                        ip = client['ip']
                        status = client['status']
                        last_seen = client['lastSeen']
                        
                        print(f"{network}, {device_name}, {switch_port}, {client_mac}, {ip}, {status}, {last_seen}")

            if WRITE_CSV:
                if len(client_dict) > 0:
                    csv_writer(client_dict)
                else:
                    print(f"{RED}** Nothing to write{ENDC}")

        except meraki.APIError as e:
            print(f'Meraki API error: {e}')
            print(f'Status code = {e.status}')
            print(f'Reason = {e.reason}')
            print(f'Error = {e.message}')
        
        except Exception as e:
            print(f'SDK Error: {e}')


if __name__ == '__main__':
    start_time = datetime.now()
    parser = ArgumentParser(description = 'Select options.')

    parser.add_argument("-o", type = str,
                        default=None,
                        help = "Organization name for operation")
    parser.add_argument("-i", type = str,
                        default=None,
                        help = "Organization ID for operation")
    parser.add_argument("-n", type = str,
                        default=None,
                        help = "Network name for operation")
    parser.add_argument("-t", type = str,
                        help = "Tag name for operation (one tag only)")
    parser.add_argument("--type", nargs="*", type = str,
                        default=['switch'],
                        choices=['switch', 'wireless', 'appliance'],
                        help = "Meraki device type")
    parser.add_argument("--mac", type = str,
                        help = "MAC address to search"),
    parser.add_argument("--noout", action = "store_true",
                        help = "Turn off terminal output of client list")
    parser.add_argument("--csv", action = "store_true",
                        help = "Write CSV file")
    parser.add_argument("--log", action = "store_true",
                        help = 'Log to file')
    parser.add_argument("-v", action = "store_true",
                        help = "verbose")
    parser.add_argument("-d", action = "store_true",
                        help = "debug")
    args = parser.parse_args()
    
    logging.getLogger(__name__)
    logger = logging.getLogger(__name__)

    print_console = None

    if args.v or args.d:
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            fmt="%(asctime)s %(name)12s: %(levelname)8s > %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter)

        if args.v:
            handler_console.setLevel(logging.INFO)
        else:
            handler_console.setLevel(logging.DEBUG)

        logger.addHandler(handler_console)
        logger.propagate = False

    products = args.type

    if args.mac:
        mac = args.mac
    else:
        mac = ''

    if args.noout:
        SCREEN_OUTPUT = False
    else:
        SCREEN_OUTPUT = True
        
    if args.csv:
        WRITE_CSV = True
    else:
        WRITE_CSV = False

    log_path = os.path.join(os.getcwd(), "log")
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    if args.log:
        suppress_logging = False
        output_log = True
    elif args.v or args.d:
        suppress_logging = False
        output_log = False
    else:
        suppress_logging = True
        output_log = False

    if not (args.o or args.i):
        print('Specify an organization name or id for operation')
        sys.exit()
    else:
        if args.o:
            org_name = args.o
            org_id = None
        elif args.i:
            org_id = args.i
            org_name = None

    if args.n:
        net_name = args.n
        net_id = None
    else:
        net_name = None
        net_id = None
    
    if args.t:
        net_tag = args.t

    # main()
    asyncio.run(main())
    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
