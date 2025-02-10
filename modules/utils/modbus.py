#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            modbus.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.1b
#
# Date:            04.02.2015
#
# Description:     Library to communicate with Modbus devices. Supports
#                  serial RTU and ASCII -modes and Modbus TCP.
#                  
# Supported devices: 
#                  Modbus RTU, Ascii and TCP capable devices
#
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
# 
#                  Python Serial Port Extension: pySerial  
#                  (http://pyserial.wiki.sourceforge.net/pySerial)
#
# Version history: ** 14.01.2015 v0.1a (Olli Lammi) **
#                  First version. 
#
#                  ** 04.02.2015 v0.1b (Olli Lammi) **
#                  Added capability to listen to serial RTU frames. 
#
###########################################################################

# Imports

import sys, os, string
import time
import socket

from modules.core import log

from modules.core import threads
from modules.utils import lockfile


# pySerial module, not loaded until init of Can232Serial class instance
serial = None

###########################################################################

# Constants

DEFAULT_BAUDRATE = 19200
RESPONSE_TIMEOUT = 2.0

# types of Modbus connections
MODBUS_SERIAL_RTU = 'RTU'
MODBUS_SERIAL_ASCII = 'ASCII'
MODBUS_TCP = 'TCP'

PROTOCOL_MODBUS = 0
MBAP_LEN = 7

###########################################################################

# Device configuration data


###########################################################################

# Classes


# interface class for all types of Modbus client connections
class ModbusClient(log.Logging):
    def __init__(self, clienttype = MODBUS_SERIAL_RTU):
        log.Logging.__init__(self, 'ModbusClient')
        self.type = clienttype
        self.responsetimeout = RESPONSE_TIMEOUT

    def open(self):
        return 0
    
    def close(self):
        pass

    def setResponseTimeout(self, tout):
        self.responsetimeout = tout
    
    def readCoils(self, unitId, startingAddress, numOfCoils):
        pass
    
    def readDiscreteInputs(self, unitId, startingAddress, numOfInputs):
        pass
    
    def readHoldingRegisters(self, unitId, startingAddress, numOfRegisters):
        pass
    
    def readInputRegisters(self, unitId, startingAddress, numOfRegisters):
        pass
    

class ModbusClientTCP(ModbusClient):
    def __init__(self, ipAddress, port = 502):
        ModbusClient.__init__(self, MODBUS_TCP)
        self.ipAddress = ipAddress
        self.port = port
        self.sock = None
        self.transactionId = 1

    def getTransactionId(self):
        temp = self.transactionId
        self.transactionId = self.transactionId + 1
        return temp

    def open(self):    
        try:    
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.connect((self.ipAddress, self.port))
            self.sock.settimeout(0.1)
        except Exception, e:
            self.Log("ERROR: Cannot open TCP connection to %s port %d" % (self.ipAddress, self.port))
            self.Debug("EXCEPTION: %s" % e.__str__())
            self.sock = None
            return 0
        
        return 1
    
    def close(self):
        if self.sock != None:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def readCoils(self, unitId, startingAddress, numOfCoils):
        return self.readModbusTCP(unitId, startingAddress, numOfCoils, 0x01)
                
    def readDiscreteInputs(self, unitId, startingAddress, numOfInputs):
        return self.readModbusTCP(unitId, startingAddress, numOfInputs, 0x02)
    
    def readHoldingRegisters(self, unitId, startingAddress, numOfRegisters):
        return self.readModbusTCP(unitId, startingAddress, numOfRegisters, 0x03)
    
    def readInputRegisters(self, unitId, startingAddress, numOfRegisters):
        return self.readModbusTCP(unitId, startingAddress, numOfRegisters, 0x04)

    def readModbusTCP(self, unitId, startingAddress, numOf, functionCode):
        if self.sock == None:
            if not self.open():
                return None
        
        temp = checkModbusValues(unitId, startingAddress, numOf, functionCode)
        if temp:
            self.Log("ERROR: Invalid modbus parameters for functionCode 0x%02X: %s" % (functionCode, temp))
            return None
 
        frame = createModbusFrameRead(functionCode, startingAddress, numOf)

        temptrid = self.getTransactionId()
        frame = createMBAPHeaderWithFrame(frame, temptrid, PROTOCOL_MODBUS, unitId)
                        
        try:
            self.sock.sendall(convertFrameToData(frame))
        except:
            self.close()
            return None
        
        data = receiveMBAPFrameFromSocket(self.sock, self.responsetimeout, temptrid, PROTOCOL_MODBUS, unitId)
        
        if data == None:
            self.Log("ERROR: Missing data or timed out reading TCP response.")
            self.close()
            return None
        
        temp = checkMBAPHeaderWithFrame(data, temptrid, PROTOCOL_MODBUS, unitId)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()           
            return None
        
        frame = data[MBAP_LEN:]

        temp = checkModbusFrameResponse(frame, functionCode, numOf)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()
            return None

        return getReadResult(frame, functionCode, startingAddress, numOf)
    


class ModbusClientSerial(ModbusClient):
    def __init__(self, port, clienttype = MODBUS_SERIAL_RTU):
        ModbusClient.__init__(self, clienttype)
        
        global serial
        serial = __import__('serial') 
        
        self.portname = port
        self.baudrate = DEFAULT_BAUDRATE
        self.parity = serial.PARITY_EVEN
        self.stopbits = serial.STOPBITS_ONE
        self.databits = serial.EIGHTBITS
        self.serio = None
        self.lastrecv = 0
        self.LOCK = lockfile.LockFile(self.portname)

    def setBaudrate(self, rate):
        self.baudrate = rate

    def setParity(self, par):
        par = string.strip(string.upper(par))
        if par == 'E' or par == 'EVEN':
            self.parity = serial.PARITY_EVEN
        elif par == 'O' or par == 'ODD':
            self.parity = serial.PARITY_ODD
        elif par == 'N' or par == 'NONE' or par == 'NO':
            self.parity = serial.PARITY_NONE
        elif par == 'S' or par == 'SPACE':
            self.parity = serial.PARITY_SPACE
        elif par == 'M' or par == 'MARK':
            self.parity = serial.PARITY_MARK
            
    def setDataBits(self, bits):
        if bits == '5':
            self.databits = serial.FIVEBITS
        elif bits == '6':
            self.databits = serial.SIXBITS
        elif bits == '7':
            self.databits = serial.SEVENBITS
        else:
            self.databits = serial.EIGHTBITS

    def setStopBits(self, bits):
        if bits == '2':
            self.stopbits = serial.STOPBITS_TWO
        elif bits == '1.5':
            self.stopbits = serial.STOPBITS_ONE_POINT_FIVE
        else:
            self.stopbits = serial.STOPBITS_ONE

    def open(self):  
        if not self.LOCK.lock():
            self.Log("ERROR: Unable to aquire lockfile for modbus port: " + self.LOCK.getName())
            return 0
        
        tout = 1.0 
        if self.type == MODBUS_SERIAL_RTU:
            tout = 11.0 / self.baudrate 
        try:        
            self.serio = serial.Serial(port=self.portname, baudrate=self.baudrate, \
                                bytesize=self.databits, \
                                parity=self.parity, stopbits=self.stopbits, \
                                xonxoff=0, rtscts=0, dsrdtr=0, timeout=tout)
            
            if not self.serio.isOpen():
                self.serio = None
                self.LOCK.free()
                return 0 
        except:
            self.Log("ERROR: Cannot open serial port: %s" % self.portname)
            self.serio = None
            self.LOCK.free()
            return 0

        self.lastrecv = time.time()        
        if self.type == MODBUS_SERIAL_RTU:
            self.waitFor35()
        else:
            temp = ' '
            while len(temp) > 0 and self.serio.inWaiting() > 0:
                temp = self.serio.read(1)
        
        return 1
    
    def close(self):
        if self.serio != None:
            try:
                self.serio.close()
            except:
                pass
            self.serio = None
        self.LOCK.free()

    def readCoils(self, unitId, startingAddress, numOfCoils):
        if self.type == MODBUS_SERIAL_ASCII: 
            return self.readModbusAscii(unitId, startingAddress, numOfCoils, 0x01)
        elif self.type == MODBUS_SERIAL_RTU:
            return self.readModbusRTU(unitId, startingAddress, numOfCoils, 0x01)
        else:
            return None
                
    def readDiscreteInputs(self, unitId, startingAddress, numOfInputs):
        if self.type == MODBUS_SERIAL_ASCII: 
            return self.readModbusAscii(unitId, startingAddress, numOfInputs, 0x02)
        elif self.type == MODBUS_SERIAL_RTU:
            return self.readModbusRTU(unitId, startingAddress, numOfInputs, 0x02)
        else:
            return None
    
    def readHoldingRegisters(self, unitId, startingAddress, numOfRegisters):
        if self.type == MODBUS_SERIAL_ASCII: 
            return self.readModbusAscii(unitId, startingAddress, numOfRegisters, 0x03)
        elif self.type == MODBUS_SERIAL_RTU:
            return self.readModbusRTU(unitId, startingAddress, numOfRegisters, 0x03)
        else:
            return None
    
    def readInputRegisters(self, unitId, startingAddress, numOfRegisters):
        if self.type == MODBUS_SERIAL_ASCII: 
            return self.readModbusAscii(unitId, startingAddress, numOfRegisters, 0x04)
        elif self.type == MODBUS_SERIAL_RTU:
            return self.readModbusRTU(unitId, startingAddress, numOfRegisters, 0x04)
        else:
            return None

    def readModbusAscii(self, unitId, startingAddress, numOf, functionCode):
        if self.serio == None:
            if not self.open():
                return None
        
        temp = checkModbusValues(unitId, startingAddress, numOf, functionCode)
        if temp:
            self.Log("ERROR: Invalid modbus parameters for functionCode 0x%02X: %s" % (functionCode, temp))
            return None
 
        frame = createModbusFrameRead(functionCode, startingAddress, numOf)

        # create ASCII message frame
        frame = createAsciiMessageFrame(frame, unitId)
                        
        try:
            self.serio.write(frame)
            self.serio.flush()
        except:
            self.close()
            return None
        
        data = receiveAsciiFrameFromSerialPort(self.serio, self.responsetimeout, unitId)
        
        if data == None:
            self.Log("ERROR: Missing data or timed out reading ASCII response.")
            self.close()
            return None
        
        data = convertAsciiToFrame(data)
        
        temp = checkASCIIHeaderWithFrame(data, unitId)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()           
            return None
        
        frame = data[1:]
        frame = frame[:len(frame)-1]

        temp = checkModbusFrameResponse(frame, functionCode, numOf)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()
            return None

        return getReadResult(frame, functionCode, startingAddress, numOf)

    def waitFor35(self):
        tout = 11.0 * 3.5 / self.baudrate 
        while (time.time() - self.lastrecv <= tout):            
            if len(self.serio.read(1)) > 0:
                self.lastrecv = time.time()

    def readModbusRTU(self, unitId, startingAddress, numOf, functionCode):
        if self.serio == None:
            if not self.open():
                return None
        
        temp = checkModbusValues(unitId, startingAddress, numOf, functionCode)
        if temp:
            self.Log("ERROR: Invalid modbus parameters for functionCode 0x%02X: %s" % (functionCode, temp))
            return None
 
        frame = createModbusFrameRead(functionCode, startingAddress, numOf)

        # create RTU message frame
        frame = createRTUMessageFrame(frame, unitId)

        frame = convertFrameToData(frame)
                        
        self.waitFor35()
                        
        try:
            self.serio.write(frame)
            self.serio.flush()
            self.lastrecv = time.time()
        except:
            self.close()
            return None
        
        data = self.receiveRTUFrameFromSerialPort(self.responsetimeout)
        
        if data == None:
            self.Log("ERROR: Missing data or timed out reading RTU response.")
            self.close()
            return None
        
        temp = checkRTUHeaderWithFrame(data, unitId)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()           
            return None
        
        frame = data[1:]
        frame = frame[:len(frame)-2]

        temp = checkModbusFrameResponse(frame, functionCode, numOf)
        if temp:
            self.Log("ERROR: Invalid response data: " + temp)
            self.close()
            return None

        return getReadResult(frame, functionCode, startingAddress, numOf)

    def receiveRTUFrameFromSerialPort(self, timeout):
        tout15 = 11.0 * 1.5 / self.baudrate
        tout35 = 11.0 * 3.5 / self.baudrate 
        hasdata = False
        isok = True
        is15 = False
        starttime = time.time()
        buff = []
        while 1:
            try:
                data = self.serio.read(1)
            except:
                return None
            if len(data) > 0:
                if is15:
                    isok = False
                else:
                    self.lastrecv = time.time()
                    buff.append(ord(data))
                    hasdata = True
            if hasdata and time.time() - self.lastrecv > tout35:
                if isok:
                    return buff
                else:
                    return None
            if hasdata and time.time() - self.lastrecv > tout15:
                is15 = True
            if hasdata and time.time() - self.lastrecv > timeout:
                return None
            if not hasdata and time.time() - starttime > timeout:
                return None


class ModbusDataListener(object):
    def dataReceived(self, unitid, coils, hregs): pass

class ModbusSlaveSerialRTUModbusListener(ModbusClientSerial, threads.Thread):
    def __init__(self, port):
        ModbusClientSerial.__init__(self, port, MODBUS_SERIAL_RTU)
        threads.Thread.__init__(self)
        self.setID('ModbusSlaveSerialRTUModbusListener')
        self.modbusDataListener = None

    def setModbusDataListener(self, listener):
        self.modbusDataListener = listener

    def startListener(self):
        if self.serio == None:
            if not self.open():
                self.setFail()
                self.setTerminated()
                return 0

        self.start()
        return 1
    
    def run(self):        
        try:              
            self.Log("Modbus serial RTU listener thread started.")

            while self.isRunning():                    
                data = self.receiveRTUFrameFromSerialPort(self.responsetimeout)
                
                if data != None:                
                    self.Debug("Received Modbus RTU frame: %s" % log.dumpBuffer(convertFrameToData(data)))
                    
                    temp = checkRTUHeaderWithFrame(data, None)
                    if temp:
                        self.Debug("ERROR: Invalid response data: " + temp)
                        continue
                    
                    unitId = getInt8(data, 0)        
                    frame = data[1:]
                    frame = frame[:len(frame)-2]
            
                    functionCode = getInt8(frame, 0)
                    if functionCode & 0x80 > 0:
                        self.Debug("ERROR: Frame has exception bit raised in function code. Ignoring")
                        continue
            
                    if functionCode in [0x05, 0x06, 0x0F, 0x10]:
                        self.handleWriteFrame(unitId, functionCode, frame)

        except Exception, e:
            self.Log("Exception: " + e.__str__())
            self.setFail()
        except IOError, ioe:
            self.Log("IOError: " + ioe.__str__())
            self.setFail()

        self.close()
       
        self.Log("Modbus serial RTU listener thread stopped.")
    
    def handleWriteFrame(self, unitId, functionCode, frame):
        if not self.modbusDataListener:
            return
    
        coils = {}
        hregs = {}
    
        flen = len(frame)
        if functionCode == 0x05:
            if flen != 5:
                self.Debug("ERROR: Invalid Write Single Coil frame length.")
                return
            addr = getInt16(frame, 1)
            val = getInt16(frame, 3)
            if val != 0x0000 and val != 0xFF00:
                self.Debug("ERROR: Invalid Coil Write value.")                
                return
            res = 0
            if val == 0xFF00:
                res = 1
            coils[addr + 1] = res
            self.Debug("Received value for coil %d: %d" % (addr + 1, res))
        elif functionCode == 0x06:
            if flen != 5:
                self.Debug("ERROR: Invalid Write Single Register frame length.")
                return
            addr = getInt16(frame, 1)
            val = getInt16(frame, 3)
            hregs[addr + 1] = val
            self.Debug("Received value for register %d: %d" % (addr + 1, val))
        if functionCode == 0x0F:
            if flen < 5:
                self.Debug("ERROR: Invalid Write Multiple Coils frame length.")
                return
            if flen == 5:
                self.Debug("Received 0x0F acknowledge frame, ignoring.")
                return
            addr = getInt16(frame, 1)
            numOf = getInt16(frame, 3)
            blen = getInt8(frame, 5) 
            if blen != (numOf-1) / 8 + 1:
                self.Debug("ERROR: Invalid coil write byte length.")                                
                return

            i = 0
            while i < numOf:
                val = (frame[6 + (i / 8)] >> (i % 8)) & 0x0001
                coils[addr + i + 1] = val
                self.Debug("Received value for coil %d: %d" % (addr + i + 1, val))
                i = i + 1        
        if functionCode == 0x10:
            if flen < 5:
                self.Debug("ERROR: Invalid Write Multiple Registers frame length.")
                return
            if flen == 5:
                self.Debug("Received 0x10 acknowledge frame, ignoring.")
                return
            addr = getInt16(frame, 1)
            numOf = getInt16(frame, 3)
            blen = getInt8(frame, 5) 
            if blen != (numOf*2):
                self.Debug("ERROR: Invalid register write byte length.")                                
                return

            i = 0
            while i < numOf:
                val = getInt16(frame, 6 + i * 2)
                hregs[addr + i + 1] = val
                self.Debug("Received value for register %d: %d" % (addr + i + 1, val))
                i = i + 1        

        self.modbusDataListener.dataReceived(unitId, coils, hregs)
    
    # ignore modbus master commands                
    def readCoils(self, unitId, startingAddress, numOfCoils):
        return None
                
    def readDiscreteInputs(self, unitId, startingAddress, numOfInputs):
        return None
    
    def readHoldingRegisters(self, unitId, startingAddress, numOfRegisters):
        return None
    
    def readInputRegisters(self, unitId, startingAddress, numOfRegisters):
        return None


###########################################################################

# Functions

def checkModbusValues(unitId, startingAddress, numOf, functionCode):
    if unitId < 0x00 or unitId > 0xFF:
        return "Invalid unitId"
    
    if startingAddress < 0x0001 or startingAddress > 0xFFFF:
        return "Starting address must be 0x0001 - 0xFFFF"
    if startingAddress + numOf > (0xFFFF + 1):
        return "Starting address + number of inputs/registers must be <= 0xFFFF"
    
    if functionCode == 0x01 or functionCode == 0x02:
        if numOf < 1 or numOf > 0x07D0:
            return "Number of inputs must be 1-2000"
    elif functionCode == 0x03 or functionCode == 0x04:
        if numOf < 1 or numOf > 0x007D:
            return "Number of registers must be 1-125"        
    else:
        return "Invalid functioncode"
    
    return None
    
def createModbusFrameRead(functionCode, startingAddress, numOf):
    temp = []
    appendInt8(temp, functionCode)
    appendInt16(temp, startingAddress - 1)
    appendInt16(temp, numOf)
    return temp

def checkModbusFrameResponse(frame, functionCode, numOf):
    fcode = getInt8(frame, 0)
    if fcode != functionCode and fcode != functionCode | 0x80:
        return "Invalid functioncode"
    
    if fcode == functionCode | 0x80:
        return "Exception in functioncode"
    
    blen = getInt8(frame, 1)
    if (functionCode in [0x01, 0x02] and blen != (numOf-1) / 8 + 1) or (functionCode in [0x03, 0x04] and blen != numOf * 2):
        return "Invalid number of response bytes"
    
    if len(frame) - 2 != blen:
        return "Invalid modbus frame length"
    
    return False

def getReadResult(frame, functionCode, startingAddress, numOf):
    res = {}
    i = 0
    while i < numOf:
        if functionCode in [0x01, 0x02]:
            res[startingAddress + i] = (frame[2 + (i / 8)] >> (i % 8)) & 0x0001
        elif functionCode in [0x03, 0x04]:
            res[startingAddress + i] = getInt16(frame, 2 + i * 2)
        i = i + 1        
    return res

def createMBAPHeaderWithFrame(frame, transactionId, protocolId, unitId):
    temp = []
    appendInt16(temp, transactionId)    
    appendInt16(temp, protocolId)
    appendInt16(temp, len(frame) + 1)
    appendInt8(temp, unitId & 0x00FF)
    temp = temp + frame
    return temp

def checkMBAPHeaderWithFrame(frame, transactionId, protocolId, unitId):
    if getInt16(frame, 0) != transactionId:
        return "Invalid transaction id"
    
    if getInt16(frame, 2) != protocolId:
        return "Invalid protocol id"
    
    if getInt16(frame, 4) != len(frame) - 6:
        return "Invalid modbus frame length"
    
    if getInt8(frame, 6) != unitId:
        return "Invalid unit id"
        
    return None

def createAsciiMessageFrame(frame, unitId):
    temp = []
    appendInt8(temp, unitId & 0x00FF)
    temp = temp + frame
    appendInt8(temp, calculateFrameLRC(temp))
    
    return ':' + convertFrameToAscii(temp) + '\x0D\x0A'

def checkASCIIHeaderWithFrame(frame, unitId):
    if getInt8(frame, 0) != unitId:
        return "Invalid unit id"

    if getInt8(frame, len(frame)-1) != calculateFrameLRC(frame[:len(frame)-1]):
        return "Invalid LRC field"
    
    return None

def createRTUMessageFrame(frame, unitId):
    temp = []
    appendInt8(temp, unitId & 0x00FF)
    temp = temp + frame
    appendInt16LO(temp, calculateFrameCRC(temp))
    
    return temp

def checkRTUHeaderWithFrame(frame, unitId):
    if unitId != None:
        if getInt8(frame, 0) != unitId:
            return "Invalid unit id"

    if getInt16LO(frame, len(frame)-2) != calculateFrameCRC(frame[:len(frame)-2]):
        return "Invalid CRC field"
    
    return None
    
def appendInt8(buff, value):
    buff.append(value & 0x00FF)
    
def appendInt16(buff, value):
    buff.append((value & 0xFF00) >> 8)
    buff.append((value & 0x00FF))

def appendInt16LO(buff, value):
    buff.append((value & 0x00FF))
    buff.append((value & 0xFF00) >> 8)

def getInt8(buff, pos):
    return buff[pos] & 0x00FF

def getInt16(buff, pos):
    temp = 0
    temp = temp | ((buff[pos] << 8) & 0xFF00)
    temp = temp | (buff[pos+1] & 0x00FF)
    return temp

def getInt16LO(buff, pos):
    temp = 0
    temp = temp | ((buff[pos+1] << 8) & 0xFF00)
    temp = temp | (buff[pos] & 0x00FF)
    return temp

def convertFrameToData(frame):
    temp = ''
    for val in frame:
        temp = temp + chr(val)
    return temp

def convertDataToFrame(data):
    temp = []
    for i in range(len(data)):
        temp.append(ord(data[i]))
    return temp

def convertFrameToAscii(frame):
    temp = ''
    for val in frame:
        temp = temp + "%02X" % val
    return temp

def convertAsciiToFrame(data):
    temp = []
    while len(data) >= 2:
        temp.append(int(data[:2], 16))
        data = data[2:]
    return temp

def calculateFrameLRC(frame):
    lrc = 0
    
    for val in frame:
        lrc = (lrc + val) & 0x00FF 
    lrc = ((0xFF - lrc) + 1) & 0xFF
    return lrc


# generate lookup table for CRC calculation
RTU_CRC_LOOKUP_TABLE = []
for i in range(256):
    crc = i
    i = 0
    while i < 8:
        st = crc & 0x0001
        if st:
            crc = (crc >> 1) ^ 0xA001
        else:
            crc = crc >> 1
        i = i + 1
    RTU_CRC_LOOKUP_TABLE.append(crc)

def calculateFrameCRC(frame):
    crc = 0xFFFF
    for c in frame:
        crc = (crc >> 8) ^ RTU_CRC_LOOKUP_TABLE[(crc ^ c) & 0x00FF]
    return crc

def receiveMBAPFrameFromSocket(sock, timeout, transactionId, protocolId, unitId):
    starttime = time.time()
    buff = []
    while 1:
        try:
            data = sock.recv(1)
        except:
            return None
        if len(data) > 0:
            starttime = time.time()
            buff.append(ord(data))
        stat = checkReceivedMBAPFrame(buff, transactionId, protocolId, unitId)
        if stat == 1:
            return buff
        elif stat == -1:
            return None
        if time.time() - starttime > timeout:
            return None

def checkReceivedMBAPFrame(buff, transactionId, protocolId, unitId):
    l = len(buff)
    if l < 2:
        return 0
    if getInt16(buff, 0) != transactionId:
        return -1
    
    if l < 4:
        return 0
    if getInt16(buff, 2) != protocolId:
        return -1

    if l < 6:
        return 0
    flen = getInt16(buff, 4)
        
    if l < flen + 6:
        return 0
        
    if flen > 0 and getInt8(buff, 6) != unitId:
        return -1
        
    return 1 
    
def receiveAsciiFrameFromSerialPort(serio, timeout, unitId):
    starttime = time.time()
    buff = ''
    while 1:
        try:
            data = serio.read(1)
        except:
            return None
        if len(data) > 0:
            starttime = time.time()
            if data == ':':
                buff = ''
            else:
                buff = buff + data
        stat = checkReceivedAsciiFrame(buff)
        if stat == 1:
            return buff[:len(buff)-2]
        elif stat == -1:
            return None
        if time.time() - starttime > timeout:
            return None

def checkReceivedAsciiFrame(buff):
    l = len(buff)
    if l < 2:
        return 0

    if buff[l-2] == '\x0D' and buff[l-1] == '\x0A':
        return 1
    
    return 0

