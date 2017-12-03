"""
<plugin key="mikrotik-routeros" name="Mikrotik RouterOS" author="mrin" version="0.0.3" wikilink="https://github.com/mrin/domoticz-routeros-plugin" externallink="">
    <params>
        <param field="Address" label="IP address" width="200px" required="true" default="192.168.1.1"/>
        <param field="Port" label="API Port" width="200px" required="true" default="8728"/>
        <param field="Username" label="API Username" width="200px" required="true" default="api"/>
        <param field="Password" label="API Password" width="200px" required="true" default="yourpassword"/>
        <param field="Mode1" label="Update interval (sec)" width="200px" required="true" default="5"/>
        <param field="Mode2" label="Bandwidth Interface" width="200px" required="true" default="ether1"/>
        <param field="Mode3" label="Status Interface" width="200px" required="true" default="ether1"/>
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
module_paths = [x[0] for x in os.walk( os.path.join(os.path.dirname(__file__), '.', '.env/lib/') ) if x[0].endswith('site-packages') ]
for mp in module_paths:
    sys.path.append(mp)

import Domoticz
from miktapi.sentence import sentence_pack, SentenceUnpacker
from miktapi.helper import SentenceParser, password_encode
import math


class BasePlugin:
    bwOptions = {"Custom": "1;Mbit/s"}

    iconName = 'mikrotik-routeros-winbox'

    bwUpUnit = 1
    bwDownUnit = 2
    statusUnit = 3

    def __init__(self):
        self.miktLoggedIn = False
        self.miktConn = None
        self.miktUnpacker = SentenceUnpacker()

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
        if self.statusUnit not in Devices:
            Domoticz.Device(Name='Status', Unit=self.statusUnit, TypeName='Switch', Image=iconID).Create()

        self.miktConn = Domoticz.Connection(Name='Mikrotik', Transport='TCP/IP', Protocol='None',
                                            Address=Parameters['Address'], Port=int(Parameters['Port']))

        Domoticz.Heartbeat(int(Parameters['Mode1']))

    def onStop(self):
        pass

    def onConnect(self, Connection, Status, Description):
        self.miktLoggedIn = False
        if Status == 0:
            self.miktConn.Send(sentence_pack(['/login', '.tag=initial_login']))
        else:
            Domoticz.Error("Mikrotik connection error.  Status [%s] [%s]" % (Status, Description))


    def onMessage(self, Connection, Data):
        self.miktUnpacker.feed(Data)
        for sentence in self.miktUnpacker:
            reply, tag, words = SentenceParser.parse_sentence(sentence)

            if tag == 'initial_login' and reply == '!done':
                self.miktConn.Send(sentence_pack([
                    '/login',
                    '=name=%s' % Parameters['Username'],
                    '=response=%s' % password_encode(Parameters['Password'], words['ret']),
                    '.tag=authorize'
                ]))
            elif tag == 'authorize' and reply == '!done':
                self.miktLoggedIn = True
                if Parameters['Mode3']:
                    self.miktCommand([
                        '/interface/listen',
                        '=.proplist=id,running,disabled'
                        '?name=%s' % Parameters['Mode3'],
                        '.tag=interface_status'
                    ])
            elif tag == 'interface_status' and reply == '!re':
                pass



    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        # if self.statusUnit == Unit:
        #     iface = self.apiGetInterfaceStatus(self.statusInterfaceName)
        #     if not iface: return
        #
        #     if 'On' == Command:
        #         if iface['disabled'] == True:
        #             self.changeInterfaceStatus(iface, enabled=True)
        #
        #         # reconnect interface
        #         elif iface['running'] == False:
        #             self.changeInterfaceStatus(iface, enabled=False)
        #             self.changeInterfaceStatus(iface, enabled=True)
        #
        #     elif 'Off' == Command and iface['disabled'] == False:
        #         if isinstance(self.changeInterfaceStatus(iface, enabled=False), tuple):
        #             UpdateDevice(self.statusUnit, 0, '0')


    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        self.miktLoggedIn = False

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")

        # if not self.miktConn:
        #     Domoticz.Error('onHeartbeat - no connection to %s. Re-connect...' % Parameters['Address'])
        #     self.miktConn = APIConnect(host=Parameters['Address'], port=int(Parameters['Port']),
        #                                username=Parameters['Username'], password=Parameters['Password'])
        #     return
        #
        # stats = self.apiCommand(cmd='/interface/monitor-traffic', interface=Parameters['Mode2'], once=True)
        # if stats:
        #     bw, = stats
        #     Domoticz.Debug('Traffic monitor: %s' % str(bw))
        #     UpdateDevice(self.bwDownUnit, 1, str(bitToMbit(bw.get('rx-bits-per-second', 0))))
        #     UpdateDevice(self.bwUpUnit, 1, str(bitToMbit(bw.get('tx-bits-per-second', 0))))
        #
        # if not Parameters['Mode3']: return
        #
        # iface = self.apiGetInterfaceStatus(self.statusInterfaceName)
        # if iface:
        #     if iface['running']:
        #         UpdateDevice(self.statusUnit, 1, '100')
        #     else:
        #         UpdateDevice(self.statusUnit, 0, '0')

    def miktCommand(self, words_list):
        if self.miktConn.Connected() and self.miktLoggedIn:
            self.miktConn.Send(sentence_pack(words_list))

    # def changeInterfaceStatus(self, iface, enabled):
    #     self.miktCommand(cmd='/interface/set', **{'disabled': (not enabled), '.id': iface['.id']})


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
