# Mikrotik RouterOS - Domoticz Python plugin

Bandwidth monitor of specified interface.

*See this [link](https://www.domoticz.com/wiki/Using_Python_plugins) for more information on the Domoticz plugins.*

## Installation

Go to plugins folder and clone plugin:
```
cd domoticz/plugins
git clone https://github.com/mrin/domoticz-routeros-plugin.git mikrotik
```
Then go to plugin folder and install dependencies:
```
cd mikrotik
pip3 install librouteros -t .vendors
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
| Interface | Interface name, ex. ```pppoe-out1```, ```ether2``` |
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

##Screenshots
![routeros_down](https://user-images.githubusercontent.com/93999/29780502-b4b75974-8c1e-11e7-9de1-bfd53f4347a9.png)
![routeros_up](https://user-images.githubusercontent.com/93999/29780501-b4b6bb54-8c1e-11e7-8999-de769cc67013.png)


##Configure API credentials

###Winbox

1. Enabling API.

Go to **IP** -> **Services** and enable "**api**" service.

2. Creating API user. 

Go to **System** -> **Users**, tab **Groups**. Create new group with permissions: ```api```, ```read```.

Then after group created go to tab ```Users``` and create new. Associate this user with group previously created.

Done.