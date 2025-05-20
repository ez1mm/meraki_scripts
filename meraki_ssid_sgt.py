#!/usr/bin/env python
import os

import meraki

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

def main():
    test_org = 112233 # your Org ID
    test_network = "RANDOMNETWORK" # test Network
    test_ssid = "Wireless80211" # test SSID
    test_sgt = 12 # SGT Number (will be converted to ID later - must exist already) 

    dashboard = meraki.DashboardAPI(
        api_key=os.getenv('APIKEY'), # don't hardcode API creds
        base_url='https://api.meraki.com/api/v1/',
        output_log=False,
        log_file_prefix=os.path.basename(__file__)[:-3],
        log_path='',
        print_console=False,
        inherit_logging_config=True,
    )


    ## get Organization networks 
    ## find test network ID
    networks = dashboard.organizations.getOrganizationNetworks(test_org)

    for network in networks:
        if network["name"] == test_network:
            net_id = network["id"]
            break

    # print(f"Matched network: {network}")
    # print(f"Network ID: {net_id}")
    ##


    ## get AdP groups
    adp_groups = dashboard.organizations.getOrganizationAdaptivePolicyGroups(test_org)

    # match adp group for sgt and set the adp_group_id
    for adp_group in adp_groups:
        if  adp_group["sgt"] == test_sgt:
            adp_group_id = adp_group["groupId"]
            break

    print(f"Matched AdP group {adp_group}")
    print(f"AdP group ID: {adp_group_id}")
    ##


    ## get Wireless SSIDs for Network
    ## and pull SSID configs
    ssids = dashboard.wireless.getNetworkWirelessSsids(net_id)

    for ssid in ssids:
        if ssid["name"] == test_ssid:
            ssid_config = ssid
            break
    
    print(f"Matched SSID: {ssid['name']}")
    print(f"SSID config: {ssid_config}")
    ##


    ## prepare new SSID config
    # boolean needs to be set for "wifiPersonalNetworkEnabled", 
    # value is "None" from the getSsid call generally
    if ssid_config["wifiPersonalNetworkEnabled"] == None:
        ssid_config["wifiPersonalNetworkEnabled"] = False
    
    # add our AdP group ID to the SSID
    ssid_config["adaptivePolicyGroupId"] = adp_group_id

    payload = ssid_config
    print(f"Payload: {BLUE}{BOLD}{payload}{ENDC}")
    ## Send new SSID config to Dashboard
    update_response = dashboard.wireless.updateNetworkWirelessSsid(net_id, **payload)

    print(f"Result: {GREEN}{BOLD}{update_response}{ENDC}")
    ##


if __name__ == '__main__':
    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
