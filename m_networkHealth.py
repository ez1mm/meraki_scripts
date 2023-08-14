#!/usr/bin/env python
import asyncio
import csv
import os
import logging
import sys
import meraki
import meraki.aio

from argparse import ArgumentParser
from datetime import datetime

BOLD = "\033[1m"
ENDC = "\033[0m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
PURPLE = "\033[35m"
LGRAY = "\033[97m"
DGRAY = "\033[90m"


async def aGetOrgs(aiodash, org_name=None, org_id=None):
    if org_id:
        result = await aiodash.organizations.getOrganization(org_id)
        logger.debug(f"organizations: {CYAN}{result}{ENDC}")
        return result
    elif org_name:
        organizations = await aiodash.organizations.getOrganizations()
        for result in organizations:
            if result["name"] == org_name and result["api"]["enabled"]:
                logger.debug(f"organizations: {CYAN}{result}{ENDC}")
                return result
    else:
        organizations = await aiodash.organizations.getOrganizations()
        result = [org for org in organizations if org["api"]["enabled"]]
        logger.debug(f"organizations: {CYAN}{result}{ENDC}")
        return result


async def aGetNetworks(aiodash, org_id):
    result = await aiodash.organizations.getOrganizationNetworks(org_id)
    logger.debug(f"networks: {CYAN}{result}{ENDC}")
    return result
        

async def aGetNetworkHealthAlerts(aiodash, net_id):
    result = await aiodash.networks.getNetworkHealthAlerts(net_id)
    logger.debug(f"aGetNetworkHealthAlerts: {CYAN}{result}{ENDC}")
    return net_id, result


def csv_writer(alerts, net_map):
    logdir = "report"
    if not os.path.exists(logdir):
        print("Creating report directory")
        os.makedirs(logdir)

    csvfile = f"{logdir}/alerts_{datetime.now():%Y%m%d-%H%M%S}.csv"

    print(f"Writing {csvfile}")
                
    with open(csvfile, 'w', newline='') as cf:
        fieldnames = ['networkName', 'networkId', 'category', 'type', 'severity', 
                      'productType', 'deviceName', 'mac', 'serial', 'url']

        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()

        for alert in alerts:
            if alerts[alert]:
                print(f"Processing network alerts: {net_map[alert]}")
                for a in alerts[alert]:
                    devices = a['scope']['devices']
                    for dev in devices:
                        writer.writerow({
                            'networkName': net_map[alert],
                            'networkId': alert,
                            'category': a['category'],
                            'type': a['type'],
                            'severity': a['severity'],
                            'productType': dev['productType'],
                            'deviceName': dev['name'],
                            'mac': dev['mac'],
                            'serial': dev['serial'],
                            'url': dev['url']
                        })
            else:
                print(f"{net_map[alert]} has no alerts.")


async def aiomain():
    async with meraki.aio.AsyncDashboardAPI(
        api_key=os.getenv("APIKEY"),
        base_url="https://api.meraki.com/api/v1",
        output_log=output_log,
        log_path="log",
        log_file_prefix=os.path.basename(__file__)[:-3],
        print_console=True,
        inherit_logging_config=False,
        use_iterator_for_get_pages=False,
        suppress_logging=suppress_logging,
        single_request_timeout=12,
    ) as aiodash:
        
        if not oid:
            orgs = await aGetOrgs(aiodash)

            for org in orgs:
                if org_name == org["name"]:
                    org_id = org["id"]
        else:
            org_id = oid

        eligible_networks = {}
        net_map = {}

        networks = await aGetNetworks(aiodash, org_id)
        
        for net in networks:
            if net_name:
                if net_name == net['name']:
                    eligible_networks[net['id']] = net
                    net_map[net['id']] = net['name']
                    break
            else:
                if "systemsManager" not in net['productTypes']:
                    eligible_networks[net['id']] = net
                    net_map[net['id']] = net['name']
            
        nh_report = {}
        tasks = []

        for en in eligible_networks:
            tasks.append(aGetNetworkHealthAlerts(aiodash, en))

        for task in asyncio.as_completed(tasks):
            nid, result = await task
            nh_report[nid] = result
        
        if args.nocsv: # csv is the only output currently, no real need for this
            pass
        else:
            csv_writer(nh_report, net_map)


if __name__ == "__main__":
    start_time = datetime.now()
    parser = ArgumentParser(description="Select options.")

    parser.add_argument("-o", type=str, help="Organization name for operation")
    parser.add_argument("-i", type=str, help="Organization ID for operation")
    parser.add_argument("-n", type=str, help="Network name for operation")
    parser.add_argument("--nocsv", action="store_true", help="Output CSV to file")
    parser.add_argument("--log", action="store_true", help="Log to file")
    parser.add_argument("-v", action="store_true", help="verbose")
    parser.add_argument("-d", action="store_true", help="debug")
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
    print(f"\nScript complete, total runtime {end_time - start_time}")
