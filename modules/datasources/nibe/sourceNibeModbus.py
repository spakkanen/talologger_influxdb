#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            sourceNibeModbus.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.6e
#
# Date:            14.01.2015
#
# Description:     TaloLogger configuration wrapper for Nibe Modbus source.
#                  
# Version history: ** 14.01.2015 v1.6e (Olli Lammi) **
#                  Added to taloLogger. 
#
###########################################################################

# Imports

import string

from modules.core import log
from modules.core import configuration
from modules.core import dataSource

from modules.datasources.modbus import sourceModbus 

import nibeBusRS485

###########################################################################

# Constants

NIBE_TYPE_MAP = { \
                 nibeBusRS485.TYPE_INT8: ['INT8', '1'], \
                 nibeBusRS485.TYPE_INT16: ['INT16', '1'], \
                 nibeBusRS485.TYPE_INT32: ['INT32', '1'], \
                 nibeBusRS485.TYPE_UINT8: ['UINT8', '1'], \
                 nibeBusRS485.TYPE_UINT16: ['UINT16', '1'], \
                 nibeBusRS485.TYPE_UINT32: ['UINT32', '1'], \
                 nibeBusRS485.TYPE_INT16_10: ['FINT16', '0.1'], \
                 nibeBusRS485.TYPE_INT8_10: ['FINT8', '0.1'], \
                 nibeBusRS485.TYPE_INT32_10: ['FINT32', '0.1'], \
                 nibeBusRS485.TYPE_UINT32_10: ['FUINT32', '0.1'], \
                 nibeBusRS485.TYPE_UINT8_10: ['FUINT8', '0.1'], \
                 nibeBusRS485.TYPE_INT16_100: ['FINT16', '0.01'] }

###########################################################################

# Classes

class NibeModbusConf(log.Logging, configuration.Configurable, dataSource.DataSource):
    def __init__(self, modname):
        log.Logging.__init__(self, 'NibeModbusConf')
        configuration.Configurable.__init__(self)
        self.setModuleName(modname)
        dataSource.DataSource.__init__(self)
        self.setID(modname)
        
        self.privateConf = None
        self.modbusSource = None
        self.portName = None
        self.modbusUnitId = 1
        
    def getServiceName(self):
        return self.getModuleName()

    def handleConfiguration(self, conf):
        self.portName = conf.getValue('SERIAL_PORT', '', self.getModuleName())
        try:
            self.modbusUnitId = int(conf.getValue('UNITID', '1', self.getModuleName()))
        except:
            return (-1, 'Cannot convert UNITID to integer.')

        self.privateConf = configuration.Configuration()
        self.privateConf.setValue('TYPE', 'RTU', self.getModuleName())
        self.privateConf.setValue('SERIAL_PORT', self.portName, self.getModuleName())
        self.privateConf.setValue('BAUDRATE', '9600', self.getModuleName())
        self.privateConf.setValue('PARITY', 'NONE', self.getModuleName())
        self.privateConf.setValue('STOPBITS', '1', self.getModuleName())
        self.privateConf.setValue('DATABITS', '8', self.getModuleName())
        self.privateConf.setValue('RESPONSETIMEOUT', '3.0', self.getModuleName())

        holdingregisters = []        
        for register in nibeBusRS485.NIBE_DEVICES['DEFAULT']:
            try:
                nibeType = NIBE_TYPE_MAP[register[2]]
                holdingregisters.append("%s:%d:%d:%s:%s" % (register[1], self.modbusUnitId, register[0], nibeType[0], nibeType[1]))
            except:
                print("Not found register: ", str(register[2]))
        
        self.privateConf.setValue('HOLDINGREGISTER', holdingregisters, self.getModuleName())

        return (1, '')
            
    def initConfiguration(self):        
        self.modbusSource = sourceModbus.ModbusConf(self.getModuleName())

        (stat, msg) = self.modbusSource.handleConfiguration(self.privateConf)
        if stat != 1:
            return (stat, msg)
        
        (stat, msg) = self.modbusSource.initConfiguration()
        if stat != 1:
            return (stat, msg)
                
        return (1, '')

    def releaseConfiguration(self):
        if self.modbusSource != None:
            self.modbusSource.releaseConfiguration()
            self.modbusSource = None
        return (1, '')

    def runDataSourceQueryCommandImpl(self, cmds):
        return self.modbusSource.runDataSourceQueryCommandImpl(cmds)

    @staticmethod
    def getModuleTypeName():
        return 'NIBEMODBUS'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['SERIAL_PORT', 'UNITID'], [])

