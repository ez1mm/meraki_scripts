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


def getNetworks(dashboard, orgId):
    networks = dashboard.organizations.getOrganizationNetworks(orgId)
    logging.info(f'Found {len(networks)} networks.')
    logging.debug(f'networks: {BOLD}{networks}{ENDC}')
    return networks


def getNetwork(dashboard, netId):
    network = dashboard.networks.getNetwork(netId)
    logging.info(network)
    return network


def getOrgTemplates(dashboard, orgId):
    templates = dashboard.organizations.getOrganizationConfigTemplates(orgId)
    logging.info(templates)
    return templates


def getOrgTemplate(dashboard, orgId, templateId):
    template = dashboard.organizations.getOrganizationConfigTemplate(orgId, templateId)
    logging.info(template)
    return template


def getNetworkApplianceVlans(dashboard, templateId):
    applianceVlans = dashboard.appliance.getNetworkApplianceVlans(templateId)
    logging.info(applianceVlans)
    return applianceVlans


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


def ipInSubnet(ip, subnet):
    if ipaddress.ip_address(ip) in ipaddress.ip_network(subnet):
        return True
    else:
        print("IP address not in template defined subnet")
        return False


def testIp(ip):
    try:
        ip = ipaddress.ip_address(ip)
        return True
    except ValueError:
        print(f"IP address is invalid: {ip}")
        return False
    except:
        print(f"IP address is invalid: {ip}")
        return False


def testSubnet(subnet):
    try:
        subnet = ipaddress.ip_network(subnet)
        return True
    except ValueError:
        print(f"IP subnet is invalid: {subnet}")
        return False
    except:
        print(f"IP subnet is invalid: {subnet}")
        return False


def subnetInCidr(subnet, cidr):
    if ipaddress.ip_network(subnet).subnet_of(cidr):
        return True
    else:
        print("IP subnet not in template defined subnet")
        return False


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

    templates = getOrgTemplates(dashboard, orgId)
    template = {t['id']: t for t in templates}

    networkDetail = getNetwork(dashboard, netId)
    templateId = networkDetail['configTemplateId']
    
    tVlans = getNetworkApplianceVlans(dashboard, templateId)
    templateVlans = {tv['id']: tv for tv in tVlans}

    spoke = getSpoke(dashboard, netId)[0]
    print(f"\nNetworkID:  {spoke['networkId']}   Network:  {netname}")
    print(f"TemplateID: {templateId}   Template: {template[templateId]['name']}")
    print()
    print(f"MX Name: {spoke['name']}")
    print(f"Serial:  {spoke['serial']}   MAC: {spoke['mac']}\n")

    subnets = getSubnets(dashboard, netId)
    print("Addressing & VLANS\nSubnets\n")
    for subnet in subnets:
        cidr = ipaddress.ip_network(templateVlans[subnet['id']]['cidr'])
        mask = templateVlans[subnet['id']]['mask']

        print(f"Vlan {subnet['id']} Template Subnet Definition: /{mask} in {str(cidr)}")
        print(f"VlanID:    {subnet['id']:<10}     MX IP:  {subnet['applianceIp']:<16}")
        print(f"Vlan Name: {subnet['name']:<10}     Subnet: {subnet['subnet']:<16}\n")

    if rewrite:
        print()
        for subnet in subnets:
            cidr = ipaddress.ip_network(templateVlans[subnet['id']]['cidr'])
            mask = templateVlans[subnet['id']]['mask']
            
            while True:
                q = input(f"Would you like to rewrite VLAN {subnet['id']}? (Y/N): ")
                try:
                    (q == 'Y' or q == 'N')
                except ValueError:
                    raise ValueError("Enter Y or N")
                
                if q == "Y":
                    while True:
                        aIp = input("Enter MX IP: ")
                        try:
                            if (testIp(aIp) and ipInSubnet(aIp, cidr)):
                                break
                        except ValueError:
                            continue
                        except:
                            print("IP address needs to be valid and within template defined subnet")

                    while True:
                        aSubnet = input("Enter Subnet: ")
                        try:
                            if testSubnet(aSubnet) and subnetInCidr(aSubnet, cidr):
                                break
                        except ValueError:
                            continue
                        except:
                            print("Subnet needs to be valid and within template defined supernet")

                    result = updateSubnets(dashboard, spoke['networkId'], subnet['id'], str(aIp), str(aSubnet))
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
