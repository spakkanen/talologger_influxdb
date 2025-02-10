#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            can232Serial.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.1a
#
# Date:            26.11.2012
#
# Description:     Library to communicate with Can busses using CAN232 based
#                  interface devices.
#                  
# Supported devices: 
#                  CAN232 based interface devices that provide a serial
#                  interface directly or through an USB virtual serial
#                  port.
#
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
#                  Python Serial Port Extension: pySerial  
#                  (http://pyserial.wiki.sourceforge.net/pySerial)
#
# Version history: ** 26.11.2012 v0.1a (Olli Lammi) **
#                  First version. 
#
###########################################################################

# Imports

import sys, os 
import string, time

from modules.core import log
from modules.core import threads
from modules.utils import lockfile

# pySerial module, not loaded until init of Can232Serial class instance
serial = None

###########################################################################

# Constants

DEFAULT_BAUDRATE = 57600
TIMEOUT = 2


###########################################################################

# Device configuration data

# CAN bus speed classes for CAN232 (in kbits)
CAN232_SPEED_INVALID = -1
CAN232_SPEEDS = {0: 10, 1: 20, 2: 50, 3: 100, 4: 125, 5: 250, 6: 500, 7: 800, 8: 1024 }

###########################################################################

# Classes

class CANFrameListener:
    def frameReceived(self, id, data): pass


class Can232Serial(threads.Thread, log.Logging):
    def __init__(self, port, canspeedkbps, baudrate=None):
        threads.Thread.__init__(self)
        log.Logging.__init__(self, 'Can232Serial')
        
        global serial
        serial = __import__('serial') 
                       
        self.framelistener = None
        self.BAUDRATE = DEFAULT_BAUDRATE
        if baudrate:
            self.BAUDRATE = baudrate
        self.SERPORT = port
        self.CANSPEED = self.handleCanSpeed(canspeedkbps)
        self.DEVICEVERSION = ''
        self.serio = 0
          
        self.LOCK = lockfile.LockFile(self.SERPORT)
    
    def setFrameListener(self, listener):
        self.framelistener = listener
    
    def openPort(self):
        # check CAN bus speed class
        if self.CANSPEED == CAN232_SPEED_INVALID:
            self.Log("ERROR: Invalid can speed setup. Configured speed is not available.")
            return 0
        
        if not self.LOCK.lock():
            self.Log("ERROR: Unable to aquire lockfile for can232Serial port: " + self.LOCK.getName())
            return 0

        try:
            self.serio = serial.Serial(port=self.SERPORT,baudrate=self.BAUDRATE, \
                                bytesize=serial.EIGHTBITS, \
                                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, \
                                xonxoff=0, rtscts=0, dsrdtr=0, timeout=TIMEOUT)
            if not self.serio.isOpen():
                self.serio = 0
                self.LOCK.free()
                return 0 
        except:
            self.serio = 0
            self.LOCK.free()
            return 0
        
        self.Debug("Opened can232Serial port: " + self.SERPORT)    
        
        if self.initPort():
            self.Debug("Initialized can232Serial port: " + self.SERPORT)
            return 1    
        
        self.closePort()
        return 0
        
    def initPort(self):
        self.closeChannel()

        # get device version
        i = 3
        while i > 0:
            (status, data) = can232Command(self.serio, 'V')
            if status == 1:
                self.DEVICEVERSION = data
                break
            i = i - 1
        if not i:
            self.Log("ERROR: Unable to get response to CAN232 version query.")
            return 0
        self.Debug("CAN232 version " + self.DEVICEVERSION)
                
        # init bus speed
        (status, data) = can232Command(self.serio, 'S%d' % (self.CANSPEED,) )
        if status != 1:
            self.Log("ERROR: Unable to set Can bus speed.")
            return 0
        
        # open channel
        (status, data) = can232Command(self.serio, 'O')
        if status != 1:
            self.Log("ERROR: Unable to open CAN channel.")
            return 0

        self.start()
                
        return 1
        
    def closeChannel(self):
        if self.serio:
            can232Command(self.serio, 'C')
            
            self.Debug("Flushing serial input buffer.")
            temp = ' '
            while len(temp) > 0 and self.serio.inWaiting() > 0:
                temp = self.serio.read(1)
        
    def closePort(self):
        if self.serio:
            if self.isRunning():
                self.terminate()
                self.wait()
            try:
                self.closeChannel()
            except:
                pass
            try:
                self.serio.close()
            except:
                pass
            self.serio = 0
        self.DEVICEVERSION = ''
        self.LOCK.free()
        self.Debug("Closed can232Serial port: " + self.SERPORT)

    def isOpen(self):
        if self.serio and self.serio.isOpen():
            return 1
        return 0

    def getDeviceVersion(self):
        return self.DEVICEVERSION

    def handleCanSpeed(self, canspeedkbps):
        for k in CAN232_SPEEDS.keys():
            if CAN232_SPEEDS[k] == canspeedkbps:
                return k
        return CAN232_SPEED_INVALID

    def run(self):
        res = ""
        errcnt = 0
        while self.isRunning():
            try:
                blocktime = time.time()
                temp = self.serio.read()
                if len(temp) <= 0 and time.time() - blocktime < (TIMEOUT / 2.0):
                    errcnt = errcnt + 1
                    if errcnt > 5:
                        self.Log("Repeating error while reading Can232 serial data. Terminating thread.")
                        self.setFail()

                if len(temp) > 0:
                    errcnt = 0
                    res = res + temp
                (stat, msg, res) = checkMessage(res)
                if stat == 1:
                    self.Debug("Received Can232 serial data: " + repr(msg))
                    self.handleCanFrameRow(msg)
            except Exception, e:
                self.Log("Exception: " + e.__str__())
                self.setFail()
            except IOError, ioe:
                self.Log("IOError: " + ioe.__str__())
                self.setFail()

        self.closePort()

    def handleCanFrameRow(self, msg):
        id = None
        datalen = 0
        data = ''
        
        if self.framelistener != None:
            if len(msg) < 1:
                return
            if msg[0] == 't':
                if len(msg) < 5:
                    return
                id = int(msg[1:4], 16)
                datalen = int(msg[4], 16)
                if datalen > 0:
                    if len(msg) < 5 + datalen * 2:
                        return
                    data = msg[5:5+datalen*2]
            elif msg[0] == 'T':
                if len(msg) < 10:
                    return
                id = int(msg[1:9], 16)
                datalen = int(msg[9], 16)
                if datalen > 0:
                    if len(msg) < 10 + datalen * 2:
                        return
                    data = msg[10:10+datalen*2]
            
            if id != None:
                temp = ''
                for i in range(datalen):
                    temp = temp + chr(int(data[i*2:i*2+2], 16))
                self.framelistener.frameReceived(id, temp)


###########################################################################

# Functions

# returns (status, response)
# status: 1 = ok, -1 = timeout, 0 = error in response
def can232Command(serio, cmd):
    serio.write(cmd + '\x0D')
    serio.flush()

    res = ""
    temp = " "
    while len(temp) > 0:
        temp = serio.read()
        if len(temp) <= 0:
            if len(res) > 0:
                (stat, data, res) = checkMessage(res) 
                return (stat, data)
            else:
                return (-1, '')
        res = res + temp
        (stat, data, res) = checkMessage(res)
        if stat == 0 or stat == 1:
            return (stat, data)

def checkMessage(res):
    for i in range(len(res)):
        if res[i] == '\x0D':
            return (1, res[:i], res[i+1:])
        elif res[i] == '\x07':
            return (0, res[:i], res[i+1:])
    return (-1, '', res)
