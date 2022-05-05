#!/usr/bin/env python
import logging
import os
import sys
from datetime import datetime

import meraki
from argparse import ArgumentParser

ALLOWLIST = "filterlists/allowlist.txt"
BLOCKLIST = "filterlists/blocklist.txt"

BOLD = '\033[1m'
ENDC = '\033[0m'

def getNetworks(dashboard, org_id):
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    print(f'Found {len(networks)} networks.')
    logging.debug(f'networks: {BOLD}{networks}{ENDC}')
    return networks


def getOrganizations(dashboard):
    organizations = dashboard.organizations.getOrganizations()
    print(f'Found {len(organizations)} organizations.')
    logging.debug(f'organizations: {BOLD}{organizations}{ENDC}')
    return organizations


def getContentFilter(dashboard, net_id):
    print(f'Getting Content Filter for network')
    filter = dashboard.appliance.getNetworkApplianceContentFiltering(net_id)
    logging.debug(f'filter: {BOLD}{filter}{ENDC}')
    return filter


def setContentFilter(dashboard, net_id, allowlist=None, blocklist=None, blockcategory=None, listsize='fullList'):
    response = dashboard.appliance.updateNetworkApplianceContentFiltering(
    net_id,
    #allowedUrlPatterns=['http://www.example.org', 'http://help.com.au'],
    allowedUrlPatterns=allowlist,
    #blockedUrlPatterns=['http://www.example.com', 'http://www.betting.com'],
    blockedUrlPatterns=blocklist,
    #blockedUrlCategories=['meraki:contentFiltering/category/C1', 'meraki:contentFiltering/category/C7'],
    blockedUrlCategories=blockcategory,
    # urlCategoryListSize cannot be "None", & must be set to one of: ['topSites', 'fullList']
    urlCategoryListSize=listsize
    )
    return response


def readAllowList():
    try:
        with open(ALLOWLIST, 'r') as allow:
            print('Reading Allow List file')
            allowlist = allow.read().splitlines()
        return allowlist
    except:
        print('Allow list file not found, using empty list, this will remove any existing Allow List')
        return []


def readBlockList():
    try:
        with open(BLOCKLIST, 'r') as block:
            print('Reading Block List file')
            blocklist = block.read().splitlines()
        return blocklist
    except:
        print('Block list file not found, using empty list, this will remove any existing Block List')
        return []


def compareList(listA, listB):
    # check to see if a site is in both the allow and block lists
    match = set(listA) & set(listB)
    if match:
        print('Allow and Block lists both have identical element, exiting:')
        for m in match:
            print(m)
        sys.exit()


def main():
    dashboard = meraki.DashboardAPI(
        api_key=os.getenv('APIKEY'),
        base_url='https://api.meraki.com/api/v1/',
        output_log=False,
        log_file_prefix=os.path.basename(__file__)[:-3],
        log_path='',
        print_console=False,
        inherit_logging_config=True,
    )

    orgs = getOrganizations(dashboard)

    control = (org for org in orgs if org["name"] == target_org)
    for org in control:
        if org["api"]["enabled"] == False:
            continue
        print(f'Analyzing organization {org["name"]}:')

        try:
            networks = getNetworks(dashboard, org["id"])
            for network in networks:
                print(f'Network: {network["name"]}')
                filter = getContentFilter(dashboard, network["id"])

                if net_tag in network["tags"]:
                    if clear_filter:
                        print('Clearing Content Filter for targets')
                        allowlist = []
                        blocklist = []
                    else:
                        print('Matched filter tag, applying filter')
                        allowlist = readAllowList()
                        blocklist = readBlockList()
                        compareList(allowlist, blocklist)
    
                    # TODO: we should check if filter matches before we 
                    # go ahead and set it again lets not waste API calls
                    
                    setfilter = setContentFilter(dashboard, network["id"], allowlist, blocklist)

        except meraki.APIError as e:
            print(f'Meraki API error: {e}')
            print(f'Status code = {e.status}')
            print(f'Reason = {e.reason}')
            print(f'Error = {e.message}')
            continue
        except Exception as e:
            print(f'SDK Error: {e}')
            continue

if __name__ == '__main__':
    parser = ArgumentParser(description = 'Select options.')

    parser.add_argument('-o', type = str,
                        help = 'Organization name for operation (required)')
    # parser.add_argument('-n', type = str,
    #                     help = 'Network name for operation')
    parser.add_argument('-t', type = str,
                        help = 'Tag name for operation (one tag only)')
    parser.add_argument('-c', action = 'store_true',
                        help = 'Clear ContentFilter for targets')
    parser.add_argument('-v', action = 'store_true',
                        help = 'verbose')
    parser.add_argument('-d', action = 'store_true',
                        help = 'debug')
    args = parser.parse_args()
    
    print_console = None
    target_org = None
    target_network = None
    net_tag = None
    clear_filter = False

    if args.v:
        print_console = True
        logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    if args.d:
        print_console = True
        logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    if not args.o:
        print('Specify an organization for operation')
        sys.exit()
    else:
        target_org = args.o

    # if args.n:
    #     target_network = args.n

    if args.t:
        net_tag = args.t

    if args.c:
        clear_filter = True

    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
