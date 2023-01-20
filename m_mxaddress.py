#!/usr/bin/env python
import ipaddress
import logging
import meraki
import os
import sys

from argparse import ArgumentParser
from datetime import datetime

BOLD = '\033[1m'
ENDC = '\033[0m'

def getOrganizations(dashboard):
    organizations = dashboard.organizations.getOrganizations()
    logging.info(f'Found {len(organizations)} organizations.')
    logging.debug(f'organizations: {BOLD}{organizations}{ENDC}')
    return organizations


def getNetworks(dashboard, org_id):
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    logging.info(f'Found {len(networks)} networks.')
    logging.debug(f'networks: {BOLD}{networks}{ENDC}')
    return networks


def getSpoke(dashboard, nId):
    devices = dashboard.networks.getNetworkDevices(nId)
    logging.info(devices)
    return devices


def getSubnets(dashboard, nId):
    subnets = dashboard.appliance.getNetworkApplianceVlans(nId)
    logging.info(subnets)
    return subnets


def updateSubnets(dashboard, nId, vlanId, mxIp, mxSubnet):
    response = dashboard.appliance.updateNetworkApplianceVlan(
            nId,
            vlanId,
            subnet=mxSubnet,
            applianceIp=mxIp
        )
    return response


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
    try:
        orgId = [org['id'] for org in orgs if org['name'] == orgname][0]
    except:
        print(f"{BOLD}Organization name {orgname} not found{ENDC}")
        sys.exit()

    networks = getNetworks(dashboard, orgId)
    try:
        netId = [network['id'] for network in networks if network['name'] == netname][0]
    except:
        print(f"{BOLD}Network name {netname} not found{ENDC}")
        sys.exit()

    spoke = getSpoke(dashboard, netId)[0]
    print(f"\nNetwork: {spoke['name']}   Model: {spoke['model']}   NetworkID: {spoke['networkId']}   Serial: {spoke['serial']}   MAC: {spoke['mac']}\n")
    
    subnets = getSubnets(dashboard, netId)
    print("Addressing & VLANS\nSubnets\n")
    for subnet in subnets:
        print(f"VlanID: {subnet['id']:4} Vlan Name: {subnet['name']:15} MX IP: {subnet['applianceIp']:16} Subnet: {subnet['subnet']:20}")

    if rewrite:
        print()
        print(f"{BOLD}*** WARNING - THERE IS CURRENTLY MINOR VALIDATION FOR ADDRESSING INPUT ***{ENDC}")
        for subnet in subnets:
            while True:
                q = input(f"Would you like to rewrite VLAN {subnet['id']}? (Y/N): ")
                try:
                    (q == 'Y' or q == 'N')
                except ValueError:
                    raise ValueError("Enter Y or N")
                    continue
                
                if q == "Y":
                    while True:
                        aIp = input("Enter MX IP: ")
                        try:
                            ip = ipaddress.ip_address(aIp)
                            break
                        except ValueError:
                            print(f"IP address is invalid: {ip}")
                            continue
                        except:
                            print("Enter a valid IP address")

                    while True:
                        aSubnet = input("Enter Subnet: ")
                        try:
                            subnet = ipaddress.ip_network(aSubnet)
                            break
                        except ValueError:
                            print(f"Subnet is invalid: {subnet}")
                            continue
                        except:
                            print("Enter a valid subnet")

                    result = updateSubnets(dashboard, spoke['networkId'], subnet['id'], aIp, aSubnet)
                    print(f"\nVlanID: {result['id']:4} Vlan Name: {result['name']:15} MX IP: {result['applianceIp']:16} Subnet: {result['subnet']:20}\n")
                    break
                elif q == "N":
                    break
                else:
                    print("Enter Y or N")

if __name__ == "__main__":
    parser = ArgumentParser(description="Select options.")
    parser.add_argument('-o', type = str,
                        help = 'Organization name for operation (required)')
    parser.add_argument('-n', type = str,
                        help = 'Network name for operation (required)')
    parser.add_argument("-rw", action="store_true",
                        help="Re-write subnet addresses")                  
    parser.add_argument("-v", action="store_true",
                        help="verbose")  
    parser.add_argument("-d", action="store_true",
                        help="debug")
    args = parser.parse_args()

    apikey = os.getenv("APIKEY")
    
    org = None
    orgname = None
    netname = None
    rewrite = False

    if not args.o:
        print('Specify an organization (-o) for operation')
        sys.exit()
    else:
        orgname = args.o

    if not args.n:
        print('Specify an network (-n) for operation')
        sys.exit()
    else:
        netname = args.n

    if args.rw:
        rewrite = True

    if args.v:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s - %(levelname)s - %(message)s")

    if args.d:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s - %(levelname)s - %(message)s")

    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f"\nScript complete, total runtime {end_time - start_time}")
