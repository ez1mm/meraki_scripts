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


async def aGetOrgDevices(aiodash, org_id, productTypes=None):
    result = await aiodash.organizations.getOrganizationDevices(
        org_id, perPage=1000, total_pages="all", productTypes=productTypes
    )
    logger.debug(f"org devices: {CYAN}{result}{ENDC}")
    return result


async def aGetWirelessStatus(aiodash, serial):
    result = await aiodash.wireless.getDeviceWirelessStatus(serial)
    logger.debug(f"aGetWirelessStatus: {CYAN}{result}{ENDC}")
    return serial, result
        

def csv_writer(devices, net_map):
    logdir = "report"
    if not os.path.exists(logdir):
        print("Creating report directory")
        os.makedirs(logdir)

    csvfile = f"{logdir}/report_{datetime.now():%Y%m%d-%H%M%S}.csv"

    print(f"Writing {csvfile}")

    with open(csvfile, 'w', newline='') as cf:
        fieldnames = ['name', 'serial', 'mac', 'model', 'networkName', 'tags', 'lanIp', 'enabled',
                      'band', 'ssid', 'bssid', 'channel', 'width', 'power', 'visible', 'broadcasting']
        
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        
        for dev in devices:
            detail = devices[dev]['detail']
            status = devices[dev]['status']['basicServiceSets']
            logger.debug(f"{GREEN}detail: {detail}{ENDC}")
            logger.debug(f"{GREEN}{BOLD}status: {status}{ENDC}")

            for s in status:
                if (not unconfigured_ssid and 'Unconfigured SSID' not in s['ssidName']) or unconfigured_ssid:
                    writer.writerow({
                        'name': detail['name'],
                        'serial': detail['serial'],
                        'mac': detail['mac'],
                        'model': detail['model'],
                        'networkName': net_map[detail['networkId']],
                        'tags': detail['tags'],
                        'lanIp': detail['lanIp'],
                        'enabled': s['enabled'],
                        'band': s['band'],
                        'ssid': s['ssidName'],
                        'bssid': s['bssid'],
                        'channel': s['channel'],
                        'width': s['channelWidth'],
                        'power': s['power'],
                        'visible': s['visible'],
                        'broadcasting': s['broadcasting']
                    })


async def aiomain():
    async with meraki.aio.AsyncDashboardAPI(
        api_key=os.getenv("APIKEY"),
        base_url="https://api.meraki.com/api/v1",
        output_log=output_log,
        log_path="log",
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
                if org_name == org["name"]:
                    org_id = org["id"]
        else:
            org_id = oid

        networks = await aGetNetworks(aiodash, org_id)
        net_map = {}
        for network in networks:
            net_map[network['id']] = network['name']

        devices = await aGetOrgDevices(aiodash, org_id, productTypes="wireless")
        
        appliance_details = {}
        tasks = []
        for device in devices:
            if device["serial"] not in appliance_details:
                appliance_details[device["serial"]] = {}

            tasks.append(aGetWirelessStatus(aiodash, device["serial"]))
            appliance_details[device["serial"]]["detail"] = device

        for task in asyncio.as_completed(tasks):
            serial, result = await task
            appliance_details[serial]["status"] = result

        if args.nocsv: # csv is the only output currently, no real need for this
            pass
        else:
            csv_writer(appliance_details, net_map)


if __name__ == "__main__":
    start_time = datetime.now()
    parser = ArgumentParser(description="Select options.")

    parser.add_argument("-o", type=str, help="Organization name for operation")
    parser.add_argument("-i", type=str, help="Organization ID for operation")
    parser.add_argument("-n", type=str, help="Network name for operation")
    parser.add_argument("--all", action="store_true", help="Include unconfigured SSIDs")
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

    if args.all:
        unconfigured_ssid = True
    else:
        unconfigured_ssid = False

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

