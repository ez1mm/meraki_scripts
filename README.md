# Meraki Scripts

### Clone and setup

```bash
git clone https://github.com/ez1mm/meraki_scripts && cd meraki_scripts
python3 -m venv env
source env/bin/activate
python -m pip install -r requirements.txt
```

# m_contentFilter.py

Meraki Content Filter tool

## Usage
### Setup filter lists
```bash
cd filterlists
```
Edit allowlist.txt and blocklist.txt in filterlists, one URL per line.

### set API key
```bash
export APIKEY=<apikey>
```

### Options
`m_contentFilter.py` example code to get, set or clear Meraki Network Content Filters
```
usage: m_contentFilter.py [-h] [-o O] [-t T] [-c] [-v] [-d]

Select options.

optional arguments:
  -h, --help  show this help message and exit
  -o O        Organization name for operation (required)
  -t T        Tag name for operation (one tag only)
  -c          Clear ContentFilter for targets
  -v          verbose
  -d          debug
```

# m_mxaddress.py

Meraki MX VLAN Address and Subnet Reader and Re-Writer

## Usage
### set API key
```bash
export APIKEY=<apikey>
```

### Options
`m_mxaddress.py` example code to get or set Meraki MX Address and Subnet per VLAN
```
usage: m_mxaddress.py [-h] [-o O] [-n N] [-rw] [-v] [-d]

Select options.

optional arguments:
  -h, --help  show this help message and exit
  -o O        Organization name for operation (required)
  -n N        Network name for operation (required)
  -rw         Re-write subnet addresses
  -v          verbose
  -d          debug
```

# m_wirelessClientCount.py

Meraki Wireless Client count by band (async)

## Usage
### set API key
```bash
export APIKEY=<apikey>
```
Define organization by name with -o or by ID number with -i
If you want to get one network use -n <network name>
Without -n all eligible networks will be returned.

### Options
`m_wirelessClientCount.py` example code to get client counts by band
```
usage: m_wirelessClientCount.py [-h] [-o O] [-i I] [-n N] [-t T] [--log] [-v] [-d]

Select options.

options:
  -h, --help  show this help message and exit
  -o O        Organization name for operation
  -i I        Organization ID for operation
  -n N        Network name for operation
  -t T        Timespan (days) for operation, up to 7 (Default: 1)
  --log       Log to file
  -v          verbose
  -d          debug
