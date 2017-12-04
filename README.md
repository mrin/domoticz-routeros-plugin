# Mikrotik RouterOS - Domoticz Python plugin

Plugin supports:
* Bandwidth usage monitor for selected interface.
* View/Manage status of interface

*See this [link](https://www.domoticz.com/wiki/Using_Python_plugins) for more information on the Domoticz plugins.*

## Installation

Before installation plugin check the `python3` and `python3-dev` is installed for Domoticz plugin system:

```sudo apt-get install python3 python3-dev```

Also need to install setuptools and virtualenv:

```sudo pip3 install -U setuptools virtualenv```.

Then go to the plugins folder:
```
cd domoticz/plugins
git clone https://github.com/mrin/domoticz-routeros-plugin.git mikrotik

# installing dependencies:
virtualenv -p python3 .env
source .env/bin/activate
pip install git+https://github.com/mrin/miktapi
deactivate
```

Restart the Domoticz service
```
sudo service domoticz.sh restart
```

Now go to **Setup** -> **Hardware** in your Domoticz interface and add type with name **Mikrotik RouterOS**.

| Field | Information|
| ----- | ---------- |
| Data Timeout | Keep Disabled |
| IP address | Enter the IP address of Mikrotik RouterOS |
| API Port | default ```8728``` |
| API Username | routeros username (see Configure API credentials) |
| API Password | routeros password (see Configure API credentials) |
| Update interval | In seconds, this determines with which interval the plugin polls RouterOS stats |
| Bandwidth Interface | Interface name, ex. ```pppoe-out1```, ```ether2``` |
| Status Interface | Interface name, ex. ```pppoe-out1```, ```ether2``` |
| Debug | When set to true the plugin shows additional information in the Domoticz log |

After clicking on the Add button the new devices are available in **Setup** -> **Devices**.

## Update plugin

```
cd domoticz/plugins/mikrotik
git pull
```

Restart the Domoticz service
```
sudo service domoticz.sh restart
```

## Screenshots

![up](https://user-images.githubusercontent.com/93999/29917940-36cd4d54-8e4c-11e7-835f-9638d0171809.png)
![down](https://user-images.githubusercontent.com/93999/29917941-36d48240-8e4c-11e7-9a45-6d241c687753.png)
![status](https://user-images.githubusercontent.com/93999/33553637-9a16eed4-d90a-11e7-93f1-58e5411dc191.png)

## Configure API credentials

*RouterOS Winbox*

1. Enabling API.

Go to **IP** -> **Services** and enable **api** service.

2. Creating API user. 

Go to **System** -> **Users**, tab **Groups**. Create new group with permissions: ```api```, ```read```.

Then after group created go to tab ```Users``` and create new. Associate this user with group previously created.

Done.
