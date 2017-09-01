"""
<plugin key="mikrotik-routeros" name="Mikrotik RouterOS" author="mrin" version="0.0.3" wikilink="https://github.com/mrin/domoticz-routeros-plugin" externallink="">
    <params>
        <param field="Address" label="IP address" width="200px" required="true" default="192.168.1.1"/>
        <param field="Port" label="API Port" width="200px" required="true" default="8728"/>
        <param field="Username" label="API Username" width="200px" required="true" default="api"/>
        <param field="Password" label="API Password" width="200px" required="true" default="yourpassword"/>
        <param field="Mode1" label="Update interval (sec)" width="200px" required="true" default="2"/>
        <param field="Mode2" label="Interface" width="200px" required="true" default="ether1"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug" default="true"/>
                <option label="False" value="Normal"/>
            </options>
        </param>
    </params>
</plugin>
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '.', '.vendors'))

import Domoticz
from librouteros import connect
from librouteros.exceptions import TrapError, FatalError, ConnectionError, MultiTrapError
import math


class BasePlugin:
    bwOptions = {"Custom": "1;Mbit/s"}

    iconName = 'mikrotik-routeros-winbox'

    bwUpUnit = 1
    bwDownUnit = 2

    api = None

    def onStart(self):
        if Parameters['Mode6'] == 'Debug':
            Domoticz.Debugging(1)
            DumpConfigToLog()

        if self.iconName not in Images: Domoticz.Image('icons.zip').Create()
        iconID = Images[self.iconName].ID

        if self.bwUpUnit not in Devices:
            Domoticz.Device(Name='Bandwidth UP', Unit=self.bwUpUnit, TypeName='Custom', Options=self.bwOptions,
                            Image=iconID).Create()
        if self.bwDownUnit not in Devices:
            Domoticz.Device(Name='Bandwidth Down', Unit=self.bwDownUnit, TypeName='Custom', Options=self.bwOptions,
                            Image=iconID).Create()

        # todo remove it in future releases
        UpdateIcon(self.bwUpUnit, iconID)
        UpdateIcon(self.bwDownUnit, iconID)

        self.api = APIConnect(host=Parameters['Address'], port=int(Parameters['Port']),
                              username=Parameters['Username'], password=Parameters['Password'])

        Domoticz.Heartbeat(int(Parameters['Mode1']))

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        if not self.api:
            Domoticz.Error('onHeartbeat - no connection to %s' % Parameters['Address'])
            self.api = APIConnect(host=Parameters['Address'], port=int(Parameters['Port']),
                                  username=Parameters['Username'], password=Parameters['Password'])
            return

        try:
            result, = self.api(cmd='/interface/monitor-traffic', interface=Parameters['Mode2'], once=True)
            Domoticz.Debug('Traffic monitor: %s' % str(result))
            UpdateDevice(self.bwDownUnit, 1, str(bitToMbit(result.get('rx-bits-per-second', 0))))
            UpdateDevice(self.bwUpUnit, 1, str(bitToMbit(result.get('tx-bits-per-second', 0))))
        except ConnectionError as e:
            Domoticz.Error('onHeartbeat api exception [%s]: %s' % (e.__class__.__name__, str(e)))
            self.api = None
        except (TrapError, FatalError, MultiTrapError) as e:
            Domoticz.Error('onHeartbeat api exception [%s]: %s' % (e.__class__.__name__, str(e)))

def APIConnect(host, port, username, password):
    try:
        return connect(host=host, port=port, username=username, password=password)
    except (ConnectionError, TrapError, FatalError, MultiTrapError) as e:
        Domoticz.Error('Connect exception: %s' % str(e))
        return False

def bitToMbit(value):
    return math.ceil(value / 1000000 * 100) / 100

def UpdateDevice(Unit, nValue, sValue, AlwaysUpdate=False):
    if Unit not in Devices: return
    if Devices[Unit].nValue != nValue\
        or Devices[Unit].sValue != sValue\
        or AlwaysUpdate == True:

        Devices[Unit].Update(nValue, str(sValue))

        Domoticz.Debug("Update %s: nValue %s - sValue %s" % (
            Devices[Unit].Name,
            nValue,
            sValue
        ))

def UpdateIcon(Unit, iconID):
    if Unit not in Devices: return
    d = Devices[Unit]
    if d.Image != iconID: d.Update(d.nValue, d.sValue, Image=iconID)


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
