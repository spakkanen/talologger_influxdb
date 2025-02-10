#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            sourceModbus.py
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
# Description:     TaloLogger configuration wrapper for Modbus source.
#                  
# Version history: ** 14.01.2015 v1.6e (Olli Lammi) **
#                  Added to taloLogger. 
#
###########################################################################

# Imports

import string, re, struct

from modules.core import log
from modules.core import configuration
from modules.core import dataSource

from modules.utils import modbus
from modules.utils import binary


###########################################################################

# Constants

MAX_READ_GROUP_SIZE = {'COIL': 2000 , 'IN': 2000, 'HOLDREG': 125, 'INREG': 125}

###########################################################################

# Classes

class ModbusConf(log.Logging, configuration.Configurable, dataSource.DataSource):
    def __init__(self, modname):
        log.Logging.__init__(self, 'ModbusConf')
        configuration.Configurable.__init__(self)
        self.setModuleName(modname)
        dataSource.DataSource.__init__(self)
        self.setID(modname)

        self.modbusClient = None
        self.modbusType = None
        self.dataPoints = {}
        self.portName = None
        self.hostName = None
        self.tcpPort = 502
        self.baudRate = 19200
        self.parity = 'EVEN'
        self.stopBits = '1'
        self.dataBits = '8'
        self.resTimeout = 2.0
        
    def getServiceName(self):
        return self.getModuleName()

    def handleConfiguration(self, conf):
        self.modbusType = string.upper(conf.getValue('TYPE', 'RTU', self.getModuleName()))
        if not self.modbusType in ['RTU', 'ASCII', 'TCP']:
            return (-1, 'Invalid TYPE configuration')
        
        self.portName = conf.getValue('SERIAL_PORT', '', self.getModuleName())
        self.hostName = conf.getValue('HOSTNAME', '', self.getModuleName())
        try: 
            self.tcpPort = int(conf.getValue('TCPPORT', '502', self.getModuleName()))
        except:
            return (-1, 'Invalid TCPPORT configuration')
        try: 
            self.baudRate = int(conf.getValue('BAUDRATE', '19200', self.getModuleName()))
        except:
            return (-1, 'Invalid BAUDRATE configuration')
        
        self.parity = string.upper(conf.getValue('PARITY', 'EVEN', self.getModuleName()))
        if not self.parity in ['E', 'O', 'N', 'M', 'S', 'EVEN', 'ODD', 'NONE', 'MARK', 'SPACE']:
            return (-1, 'Invalid PARITY configuration')
         
        self.stopBits = conf.getValue('STOPBITS', '1', self.getModuleName())
        if not self.stopBits in ['1', '2', '1.5']:
            return (-1, 'Invalid STOPBITS configuration')
        
        self.dataBits = conf.getValue('DATABITS', '8', self.getModuleName())
        if not self.dataBits in ['5', '6', '7', '8']:
            return (-1, 'Invalid DATABITS configuration')

        try: 
            self.resTimeout = float(conf.getValue('RESPONSETIMEOUT', '2.0', self.getModuleName()))
        except:
            return (-1, 'Invalid RESPONSETIMEOUT configuration')
        
        pointmap = {}
        
        for item in conf.getValue('COILSTATE', [], self.getModuleName()):
            temps = string.split(item, ':', 3)
            if len(temps) < 3:
                self.Log("ERROR: Invalid COILSTATE configuration: " + item)
                return (-1, 'Invalid COILSTATE configuration')
            else:
                try:
                    key = string.strip(temps[0])
                    unitid = int(string.strip(temps[1]))
                    address = int(string.strip(temps[2]))
                except:
                    key = ''
                if len(key) <= 0:
                    self.Log("ERROR: Invalid COILSTATE configuration: " + item)
                    return (-1, 'Invalid COILSTATE configuration')
                else:
                    tempitem = {}
                    tempitem['type'] = 'COIL'
                    tempitem['unitid'] = unitid
                    tempitem['address'] = address
                    tempitem['valuetype'] = 'bool'
                    tempitem['factor'] = 1
                    pointmap[key] = tempitem

        for item in conf.getValue('INPUTSTATE', [], self.getModuleName()):
            temps = string.split(item, ':', 3)
            if len(temps) < 3:
                self.Log("ERROR: Invalid INPUTSTATE configuration: " + item)
                return (-1, 'Invalid INPUTSTATE configuration')
            else:
                try:
                    key = string.strip(temps[0])
                    unitid = int(string.strip(temps[1]))
                    address = int(string.strip(temps[2]))
                except:
                    key = ''
                if len(key) <= 0:
                    self.Log("ERROR: Invalid INPUTSTATE configuration: " + item)
                    return (-1, 'Invalid INPUTSTATE configuration')
                else:
                    tempitem = {}
                    tempitem['type'] = 'IN'
                    tempitem['unitid'] = unitid
                    tempitem['address'] = address
                    tempitem['valuetype'] = 'bool'
                    tempitem['factor'] = 1
                    pointmap[key] = tempitem

        for item in conf.getValue('HOLDINGREGISTER', [], self.getModuleName()):
            temps = string.split(item, ':', 5)
            if len(temps) < 5:
                self.Log("ERROR: Invalid HOLDINGREGISTER configuration: " + item)
                return (-1, 'Invalid HOLDINGREGISTER configuration')
            else:
                try:
                    key = string.strip(temps[0])
                    unitid = int(string.strip(temps[1]))
                    address = int(string.strip(temps[2]))
                    valuetype = string.lower(string.strip(temps[3]))
                    factor = float(string.strip(temps[4]))
                except:
                    key = ''
                if len(key) <= 0:
                    self.Log("ERROR: Invalid HOLDINGREGISTER configuration: " + item)
                    return (-1, 'Invalid HOLDINGREGISTER configuration')
                else:
                    if not checkValueType(valuetype):
                        self.Log("ERROR: Invalid HOLDINGREGISTER configuration: " + item)
                        return (-1, 'Invalid HOLDINGREGISTER configuration')
                                        
                    tempitem = {}
                    tempitem['type'] = 'HOLDREG'
                    tempitem['unitid'] = unitid
                    tempitem['address'] = address
                    tempitem['valuetype'] = valuetype
                    tempitem['factor'] = factor
                    pointmap[key] = tempitem

        for item in conf.getValue('INPUTREGISTER', [], self.getModuleName()):
            temps = string.split(item, ':', 5)
            if len(temps) < 5:
                self.Log("ERROR: Invalid INPUTREGISTER configuration: " + item)
                return (-1, 'Invalid INPUTREGISTER configuration')
            else:
                try:
                    key = string.strip(temps[0])
                    unitid = int(string.strip(temps[1]))
                    address = int(string.strip(temps[2]))
                    valuetype = string.lower(string.strip(temps[3]))
                    factor = float(string.strip(temps[4]))
                except:
                    key = ''
                if len(key) <= 0:
                    self.Log("ERROR: Invalid INPUTREGISTER configuration: " + item)
                    return (-1, 'Invalid INPUTREGISTER configuration')
                else:
                    if not checkValueType(valuetype):                
                        self.Log("ERROR: Invalid INPUTREGISTER configuration: " + item)
                        return (-1, 'Invalid INPUTREGISTER configuration')
                                        
                    tempitem = {}
                    tempitem['type'] = 'INREG'
                    tempitem['unitid'] = unitid
                    tempitem['address'] = address
                    tempitem['valuetype'] = valuetype
                    tempitem['factor'] = factor
                    pointmap[key] = tempitem

        self.dataPoints = pointmap
            
        return (1, '')
            
    def initConfiguration(self):        
        if self.modbusType == 'TCP':
            self.modbusClient = modbus.ModbusClientTCP(self.hostName, self.tcpPort)
        elif self.modbusType == 'RTU':
            self.modbusClient = modbus.ModbusClientSerial(self.portName, modbus.MODBUS_SERIAL_RTU)
        elif self.modbusType == 'ASCII':
            self.modbusClient = modbus.ModbusClientSerial(self.portName, modbus.MODBUS_SERIAL_ASCII)
        else:
            return (0, 'Invalid Modbus protocol type.' + self.modbusType)
        
        # set serial parameters
        if self.modbusType in ['RTU', 'ASCII']:
            self.modbusClient.setBaudrate(self.baudRate)
            self.modbusClient.setParity(self.parity)
            self.modbusClient.setDataBits(self.dataBits)
            self.modbusClient.setStopBits(self.stopBits)
        
        self.modbusClient.setResponseTimeout(self.resTimeout)
                
        return (1, '')

    def releaseConfiguration(self):
        if self.modbusClient != None:
            self.modbusClient.close()
            self.modbusClient = None
        return (1, '')

    def runDataSourceQueryCommandImpl(self, cmds):
        dataresult = {}
        if not self.modbusClient.open():
            self.Log("ERROR: Cannot open modbus connection.")

        units = {}

        for cmd in cmds:
            if not self.dataPoints.has_key(cmd):
                self.Log("ERROR: Unconfigured datapoint: %s" % cmd)
                dataresult[cmd] = ''
                continue
            
            dp = self.dataPoints[cmd]
            
            if not units.has_key(dp['unitid']):
                units[dp['unitid']] = {}
            if not units[dp['unitid']].has_key(dp['type']):
                units[dp['unitid']][dp['type']] = []
            for addr in range(dp['address'], dp['address'] + getValueTypeLenWords(dp['valuetype'])):
                if not addr in units[dp['unitid']][dp['type']]:
                    units[dp['unitid']][dp['type']].append(addr)

        for uid in units.keys():
            for type in units[uid].keys():
                units[uid][type].sort()

                unittyperesults = {}
                for addr in groupAddresses(units[uid][type], MAX_READ_GROUP_SIZE[type]):
                    if type == 'COIL':
                        tempres = self.modbusClient.readCoils(uid, addr[0], len(addr))
                    elif type == 'IN':
                        tempres = self.modbusClient.readDiscreteInputs(uid, addr[0], len(addr))
                    elif type == 'HOLDREG':
                        tempres = self.modbusClient.readHoldingRegisters(uid, addr[0], len(addr))
                    elif type == 'INREG':
                        tempres = self.modbusClient.readInputRegisters(uid, addr[0], len(addr))

                    if tempres != None:
                        unittyperesults.update(tempres)
                
                units[uid][type] = unittyperesults
                
        for cmd in cmds:
            if not self.dataPoints.has_key(cmd):
                continue
            
            dp = self.dataPoints[cmd]
        
            tempres = []
            tempreslen = getValueTypeLenWords(dp['valuetype'])
            for addr in range(dp['address'], dp['address'] + tempreslen):
                if units[dp['unitid']][dp['type']].has_key(addr):
                    tempres.append(units[dp['unitid']][dp['type']][addr])
            if len(tempres) < tempreslen:
                self.Log("ERROR: Modbus query results do not contain value for unitid %d address %d" % (dp['unitid'], dp['address']))
                dataresult[cmd] = ''
                continue       

            self.Debug("Received data for unitid %d address %d: %s" % (dp['unitid'], dp['address'], repr(tempres)))
            dataresult[cmd] = handleResultValue(tempres, dp['valuetype'], dp['factor'])

        self.modbusClient.close()
        return dataresult

    @staticmethod
    def getModuleTypeName():
        return 'MODBUS'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['TYPE', 'SERIAL_PORT', 'HOSTNAME', 'TCPPORT', 'BAUDRATE', 'PARITY', 'STOPBITS', 'DATABITS', 'RESPONSETIMEOUT'], ['COILSTATE', 'HOLDINGREGISTER', 'INPUTREGISTER', 'INPUTSTATE'])

# Functions

def groupAddresses(addrList, maxGroupSize):
    res = []
    temp = []
    n = 0
    prevaddr = None
    for addr in addrList:
        if (prevaddr != None and addr > prevaddr + 1) or n >= maxGroupSize:
            if n > 0:
                res.append(temp)
            temp = [ addr ]
            n = 1
        else:
            temp.append(addr)
            n = n + 1
        prevaddr = addr    
    if n > 0:
        res.append(temp)
    return res

# 0 - invalid
# 1 - boolean
# 2 - integer
# 3 - float
def checkValueType(vtype):
    if re.match("^(bool)|(f?u?int(8|16|(32h?)|(64h?))|(float((32h?)|(64h?))))$", vtype) != None:
        if re.match("^bool$", vtype) != None:
            return 1
        elif re.match("^f?u?int(8|16|(32h?)|(64h?))$", vtype) != None:
            return 2
        elif re.match("^float((32h?)|(64h?))$", vtype) != None:
            return 3
    return 0

def getValueTypeLenWords(vtype):
    if vtype == 'bool':
        return 1
    
    mobj = re.match("^(f?u?int|float)(8|16|32|64)h?$", vtype)
    if mobj != None:
        bits = int(mobj.group(2))
        if bits == 8:
            return 1
        return bits / 16
    else:
        return 1

def handleResultValue(value, type, factor):
    vt = checkValueType(type)
    try:
        if vt == 1:  # boolean
            return "%d" % value[0]
        elif vt == 2:  # integer
            isF = False
            isU = False
            
            tt = type
            if tt[0] == 'f':
                tt = tt[1:]
                isF = True
            if tt[0] == 'u':
                tt = tt[1:]
                isU = True    
            
            tt = tt[3:]
            if tt[0] == '8':
                bits = tt[:1]
                tt = tt[1:]
            else:                        
                bits = tt[:2]
                tt = tt[2:]
            
            if bits == '8':
                val = value[0] & 0x00FF
                if not isU:
                    val = binary.twosComplementToInt(val, 8)            
                if isF:
                    return "%f" % (float(val) * factor)
                else:
                    return "%d" % int(val * factor)
            elif bits == '16':
                val = value[0]
                if not isU:
                    val = binary.twosComplementToInt(val, 16)            
                if isF:
                    return "%f" % (float(val) * factor)
                else:
                    return "%d" % int(val * factor)
            elif bits == '32':
                if tt == 'h':
                    val = value[1] + (value[0] << 16)
                else:
                    val = value[0] + (value[1] << 16)
                if not isU:
                    val = binary.twosComplementToInt(val, 32)            
                if isF:
                    return "%f" % (float(val) * factor)
                else:
                    return "%d" % int(val * factor)
            elif bits == '64':
                if tt == 'h':
                    val = value[3] + (value[2] << 16) + (value[1] << 32) + (value[0] << 48)
                else:
                    val = value[0] + (value[1] << 16) + (value[2] << 32) + (value[3] << 48)
                if not isU:
                    val = binary.twosComplementToInt(val, 64)            
                if isF:
                    return "%f" % (float(val) * factor)
                else:
                    return "%d" % long(val * factor)
            else:
                return ""
        elif vt == 3:  # float
            tt = type[5:]
            bits = tt[:2]
            tt = tt[2:]
        
            if bits == '32':
                if tt == 'h':
                    val = value[1] + (value[0] << 16)
                else:
                    val = value[0] + (value[1] << 16)
                val = struct.unpack('>f', struct.pack('>L', val))[0] * factor
                return "%f" % val
            elif bits == '64':
                if tt == 'h':
                    val = value[3] + (value[2] << 16) + (value[1] << 32) + (value[0] << 48)
                else:
                    val = value[0] + (value[1] << 16) + (value[2] << 32) + (value[3] << 48)
                val = struct.unpack('>d', struct.pack('>Q', val))[0] * factor
                return "%f" % val
        else:
            return ""
    except:
        return ""
        
