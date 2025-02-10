#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            sourceNibeBusRS485.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.6f
#
# Date:            16.01.2015
#
# Description:     TaloLogger configuration wrapper for Nibe Bus/RS485 
#                  source. Connects to Nibe device using RS485 adapter
#                  or OpenHab NibeGW and network (UDP traffic).
#                  
# Version history: ** 16.01.2015 v1.6f (Olli Lammi) **
#                  Added to taloLogger. 
#
###########################################################################

# Imports

import string

from modules.core import log
from modules.core import configuration
from modules.core import dataSource

import nibeBusRS485

###########################################################################

# Classes

class NibeBusRS485Conf(log.Logging, configuration.Configurable, dataSource.DataSource):
    def __init__(self, modname):
        log.Logging.__init__(self, 'NibeBusRS485Conf')
        configuration.Configurable.__init__(self)
        self.setModuleName(modname)
        dataSource.DataSource.__init__(self)
        self.setID(modname)
        
        self.nibeComm = None
        self.clientType = None
        self.deviceName = None
        self.portName = None
        self.listenAddress = '0.0.0.0'
        self.udpPort = 9999
        self.queryAddress = None
        self.queryPort = 9999

        
    def getServiceName(self):
        return self.getModuleName()

    def handleConfiguration(self, conf):
        self.clientType = string.upper(conf.getValue('TYPE', '', self.getModuleName()))
        if not self.clientType in ['SERIAL', 'UDP']:
            return (-1, "Unknown or no TYPE parameter for Nibe Bus module.")

        self.deviceName = string.upper(conf.getValue('DEVICE', 'DEFAULT', self.getModuleName()))
        self.portName = conf.getValue('SERIAL_PORT', '', self.getModuleName())
        self.listenAddress = conf.getValue('LISTENADDRESS', '0.0.0.0', self.getModuleName())
        try:
            self.udpPort = int(conf.getValue('UDPPORT', '9999', self.getModuleName()))
        except:
            return (-1, "Invalid UDPPORT for Nibe Bus module.")
        self.queryAddress = conf.getValue('QUERY_ADDRESS', '', self.getModuleName())
        try:
            self.queryPort = int(conf.getValue('QUERY_UDPPORT', '9999', self.getModuleName()))
        except:
            return (-1, "Invalid QUERY_UDPPORT for Nibe Bus module.")

        return (1, '')
            
    def initConfiguration(self):
        if self.clientType == 'SERIAL':
            self.nibeComm = nibeBusRS485.NibeRS485Serial(self.portName, self.deviceName)
        elif self.clientType == 'UDP':
            self.nibeComm = nibeBusRS485.NibeRS485UDP(self.listenAddress, self.udpPort, self.deviceName)
            if self.queryAddress != None and len(string.strip(self.queryAddress)) > 0:
                self.nibeComm.setQueryPeer(self.queryAddress, self.queryPort)

        if not self.nibeComm.startModule():
            return (0, 'Error starting Nibe Bus communication controller.')
        else:
            self.Log('Started Nibe Bus communication controller in mode: ' + self.clientType)
        return (1, '')

    def releaseConfiguration(self):
        if self.nibeComm != None:
            self.nibeComm.terminate()
            if not self.nibeComm.hasTerminated():
                self.nibeComm.wait_sleeping()
            self.nibeComm = None
            return (1, '')
        return (1, '')

    def runDataSourceQueryCommandImpl(self, cmds):
        if self.nibeComm != None:
            res = self.nibeComm.runQueryCommands(cmds)
        else:
            res = {}
            for cmd in cmds:
                res[cmd] = ''
        return res

    @staticmethod
    def getModuleTypeName():
        return 'NIBERS485'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['TYPE', 'DEVICE', 'SERIAL_PORT', 'LISTENADDRESS', 'UDPPORT', 'QUERY_ADDRESS', 'QUERY_UDPPORT'], [])

