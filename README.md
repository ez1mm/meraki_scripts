# Meraki Scripts

### Clone and setup

```bash
git clone https://github.com/ez1mm/meraki_scripts && cd meraki_scripts
python3 -m venv env
source env/bin/activate
python -m pip install -r requirements.txt
```
Edit config.py and add your API key. 
https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API

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
