"""
<plugin key="mikrotik-routeros" name="Mikrotik RouterOS" author="mrin" version="0.1.1" wikilink="https://github.com/mrin/domoticz-routeros-plugin" externallink="">
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
import Domoticz
import math

import os
import sys
module_paths = [x[0] for x in os.walk( os.path.join(os.path.dirname(__file__), '.', '.env/lib/') ) if x[0].endswith('site-packages') ]
for mp in module_paths:
    sys.path.append(mp)

from miktapi.sentence import sentence_pack, SentenceUnpacker
from miktapi.helper import SentenceParser, password_encode
from miktapi.exceptions import UnpackerException, ParseException, PackException


class BasePlugin:
    bwOptions = {"Custom": "1;Mbit/s"}

    iconName = 'mikrotik-routeros-winbox'

    bwUpUnit = 1
    bwDownUnit = 2
    statusUnit = 3

    statusOptions = {
        "LevelActions": "||",
        "LevelNames": "Disabled|Running|Enabled",
        "SelectorStyle": "0"
    }

    def __init__(self):
        self.miktLoggedIn = False
        self.miktAuthError = False
        self.miktConn = None
        self.miktUnpacker = SentenceUnpacker()
        self.statusInterfaceId = None
        self.statusRunning = None
        self.statusDisabled = None

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
            Domoticz.Device(Name='Status', Unit=self.statusUnit, TypeName='Selector Switch', Image=iconID,
                            Options=self.statusOptions).Create()

        self.miktConn = Domoticz.Connection(Name='Mikrotik', Transport='TCP/IP', Protocol='None',
                                            Address=Parameters['Address'], Port=Parameters['Port'])
        self.miktConn.Connect()

        Domoticz.Heartbeat(int(Parameters['Mode1']))

    def onStop(self):
        if Parameters['Mode3'] and self.miktConn.Connected() and self.miktLoggedIn:
            self._miktCommand([
                '/cancel',
                '=tag=interface_status_update'
            ])
        self._miktResetLoginFlags()

    def onConnect(self, Connection, Status, Description):
        self._miktResetLoginFlags()
        if Status == 0:
            Domoticz.Log('Mikrotik connected. Login...')
            self.miktConn.Send(sentence_pack(['/login', '.tag=initial_login']))
        else:
            Domoticz.Error("Mikrotik connection error.  Status [%s] [%s]" % (Status, Description))

    def onMessage(self, Connection, Data):
        try:
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

                elif tag == 'authorize' and reply == '!done' and not self.miktAuthError:
                    Domoticz.Log('Mikrotik logged in successfully')
                    self.miktLoggedIn = True
                    if Parameters['Mode3']:
                        self._miktCommand([
                            '/interface/listen',
                            '=.proplist=.id,name,running,disabled',
                            '?name=%s' % Parameters['Mode3'],
                            '.tag=interface_status_update'
                        ])
                        self._miktCommand([
                            '/interface/print',
                            '=.proplist=.id,name,running,disabled',
                            '?name=%s' % Parameters['Mode3'],
                            '.tag=interface_status'
                        ])

                elif tag in ('interface_status', 'interface_status_update') and reply == '!re':
                    if not self.statusInterfaceId:
                        self.statusInterfaceId = words.get('.id', None)
                    if words.get('running', None) is not None:
                        self.statusRunning = words.get('running')
                    if words.get('disabled', None) is not None:
                        self.statusDisabled = words.get('disabled')

                    if self.statusRunning:
                        UpdateDevice(self.statusUnit, 1, '10', ShowInLog=True)
                    elif self.statusDisabled:
                        UpdateDevice(self.statusUnit, 0, '0', ShowInLog=True)
                    else:
                        UpdateDevice(self.statusUnit, 1, '20', ShowInLog=True)

                elif tag == 'bw' and reply == '!re':
                    UpdateDevice(self.bwDownUnit, 1, str(bitToMbit(words.get('rx-bits-per-second', 0))))
                    UpdateDevice(self.bwUpUnit, 1, str(bitToMbit(words.get('tx-bits-per-second', 0))))

                elif tag == 'authorize' and reply == '!trap':
                    self.miktAuthError = True
                    Domoticz.Error('Mikrotik login error [%s]' % words.get('message', None))

                elif reply in ('!fatal', '!trap'):
                    Domoticz.Error(
                        'Mikrotik error. Reply [%s]. Message [%s]. Tag [%s].' % (
                        reply, words.get('message', None), tag))

        except UnpackerException as e:
            Domoticz.Error('UnpackerException [%s]' % str(e))

        except ParseException as e:
            Domoticz.Error('ParseException [%s]' % str(e))

    def onCommand(self, Unit, Command, Level, Hue):
        if self.statusUnit == Unit:
            if self.statusInterfaceId is None:
                Domoticz.Error('No interface ID')
                return

            if self.statusDisabled is None or self.statusRunning is None:
                Domoticz.Error('No current interface status')
                return

            # disable
            if Level == 0 and not self.statusDisabled:
                self._miktChangeInterfaceStatus(disabled=True)
            # run
            elif Level == 10 and not self.statusRunning:
                self._miktChangeInterfaceStatus(disabled=True)
                self._miktChangeInterfaceStatus(disabled=False)
            # enable
            elif Level == 20 and self.statusDisabled and not self.statusRunning:
                self._miktChangeInterfaceStatus(disabled=False)

    def onDisconnect(self, Connection):
        self._miktResetLoginFlags()

    def onHeartbeat(self):
        if not self.miktConn.Connected() and not self.miktConn.Connecting():
            Domoticz.Log('Mikrotik re-connecting...')
            self.miktConn.Connect()
        else:
            self._miktCommand([
                '/interface/monitor-traffic',
                '=interface=%s' % Parameters['Mode2'],
                '=once=yes',
                '=.proplist=rx-bits-per-second,tx-bits-per-second',
                '.tag=bw'
            ])

    def _miktCommand(self, words_list):
        if self.miktLoggedIn and self.miktConn.Connected():
            try:
                self.miktConn.Send(sentence_pack(words_list))
            except PackException as e:
                Domoticz.Error('PackException [%s]' % str(e))

    def _miktChangeInterfaceStatus(self, disabled):
        self._miktCommand([
            '/interface/set',
            '=disabled=%s' % ('yes' if disabled else 'no'),
            '=.id=%s' % self.statusInterfaceId,
            '.tag=interface_set'
        ])

    def _miktResetLoginFlags(self):
        self.miktAuthError = False
        self.miktLoggedIn = False


def bitToMbit(value):
    return math.ceil(value / 1000000 * 100) / 100


def UpdateDevice(Unit, nValue, sValue, AlwaysUpdate=False, ShowInLog=False):
    if Unit not in Devices: return
    if Devices[Unit].nValue != nValue or Devices[Unit].sValue != sValue or AlwaysUpdate == True:
        Devices[Unit].Update(nValue, str(sValue))
        if ShowInLog:
            Domoticz.Log("%s: nValue %s - sValue %s" % (
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


def onMessage(Connection, Data, Status=None, Extra=None):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
