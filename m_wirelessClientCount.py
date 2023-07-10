#!/usr/bin/env python
import asyncio
import os
import logging
import sys
import meraki
import meraki.aio

from argparse import ArgumentParser
from collections import OrderedDict
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

def daysToSeconds(num):
    return num * 24 * 60 * 60 


async def aGetOrgs(aiodash, org_name=None, org_id=None):
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


async def aGetNetworks(aiodash, org_id):
    result = await aiodash.organizations.getOrganizationNetworks(org_id)
    logger.debug(f"networks: {CYAN}{result}{ENDC}")
    return result


async def aGetClientConnectionStats(aiodash, net, timespan=None, t0=None, t1=None, band=None):
    result = await aiodash.wireless.getNetworkWirelessClientsConnectionStats(net['id'], 
                                                                             band=band,
                                                                             timespan=timespan)
    logger.debug(f"getNetworkWirelessClientsConnectionStats: {CYAN}{result}{ENDC}")
    return net['id'], band, result


# async def aGetNetworkClients(aiodash, net, perPage=1000, timespan=None, t0=None, recentDeviceConnections=None):
#     result = await aiodash.networks.getNetworkClients(net['id'], 
#                                                       timespan=timespan,
#                                                       perPage=perPage,
#                                                       recentDeviceConnections=recentDeviceConnections) # 'None', 'Wired' or 'Wireless'
#     logger.debug(f"aGetNetworkClients: {CYAN}{result}{ENDC}")
#     return result


async def aiomain():
    async with meraki.aio.AsyncDashboardAPI(
        api_key=os.getenv("APIKEY"),
        base_url="https://api.meraki.com/api/v1",
        output_log=output_log,
        log_file_prefix=__file__[:-3],
        print_console=True,
        inherit_logging_config=False,
        use_iterator_for_get_pages=False,
        suppress_logging=suppress_logging,
        single_request_timeout=12,
    ) as aiodash:
        
        if not oid:
            orgs = await aGetOrgs(aiodash)

            for org in orgs:
                if org_name == org['name']:
                    org_id = org['id']
        else:
            org_id = oid

        eligible_networks = {}

        networks = await aGetNetworks(aiodash, org_id)
        for net in networks:
            if net_name:
                if net_name == net['name']:
                    eligible_networks[net['id']] = net
                    break
            elif 'wireless' in net['productTypes']:
                eligible_networks[net['id']] = net 
                
        statistics = {} 
        tasks = []

        for en in eligible_networks:
            tasks.append(aGetClientConnectionStats(aiodash, eligible_networks[en], timespan=timespan, band='2.4'))
            tasks.append(aGetClientConnectionStats(aiodash, eligible_networks[en], timespan=timespan, band='5'))
            tasks.append(aGetClientConnectionStats(aiodash, eligible_networks[en], timespan=timespan, band='6'))

        for task in asyncio.as_completed(tasks):
            nid, band, res = await task
            try:
                statistics[nid]
            except:
                statistics[nid] = {}
            statistics[nid][band] = res
        
        for stat in statistics:
            print(f"Network: {eligible_networks[stat]['name']}")
            print("Clients by band")
            for band in sorted(statistics[stat]):
                print(f"{band:>3}GHz: {len(statistics[stat][band])}")
            print()       


if __name__ == '__main__':
    start_time = datetime.now()
    parser = ArgumentParser(description = 'Select options.')

    parser.add_argument('-o', type = str,
                        help = 'Organization name for operation')
    parser.add_argument('-i', type = str,
                        help = 'Organization ID for operation')
    parser.add_argument('-n', type = str,
                        help = 'Network name for operation')
    parser.add_argument('-t', type = int,
                        help = 'Timespan (days) for operation, up to 7 (Default: 1)')
    parser.add_argument("--log", action = "store_true",
                        help = 'Log to file')
    parser.add_argument("-v", action = "store_true",
                        help = 'verbose')
    parser.add_argument("-d", action="store_true",
                        help="debug")
    args = parser.parse_args()

    logging.getLogger(__name__)
    logger = logging.getLogger(__name__)

    if args.o and args.i:
        print(f"{RED}Specify either -o or -i, not both{ENDC}")
        sys.exit()
    elif args.o:
        org_name = args.o
        oid = None
    elif args.i:
        oid = args.i
        org_name = None
    else:
        print(f"{RED}Must define an Org with -o or -i option{ENDC}")
        sys.exit()
        
    if args.n:
        net_name = args.n
    else:
        net_name = None

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

    if args.t:
        # might implement time slices later to use a longer lookback (up to 180 days)
        if args.t > 7:
            print("No more than 7 days lookback")
            sys.exit()
        else:
            timespan = daysToSeconds(args.t)
    else:
        timespan = 86400

    if args.log:
        suppress_logging = False
        output_log = True
    elif args.v or args.d:
        suppress_logging = False
        output_log = False
    else:
        suppress_logging = True
        output_log = False

    asyncio.run(aiomain())

    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
