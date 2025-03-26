#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            nibeSerial.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#                  (initial data research and code for nibeSerial module
#                  done by Mikko Tuominen) 
#
# Version:         0.1i
#
# Date:            06.01.2013
#
# Description:     Library to communicate with the Nibe heat pump controllers.
#                  
# Supported devices: 
#                  Nibe heat pump controllers.
#
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
#                  Python Serial Port Extension: pySerial  
#                  (http://pyserial.wiki.sourceforge.net/pySerial)
#
###########################################################################

# Imports

import sys, os 
import string
import time 

from modules.core import threads
from modules.core import log
from modules.utils import lockfile
from modules.utils import binary

# pySerial module, not loaded until init of NibeSerial class instance
serial = None

###########################################################################

# Constants

BAUDRATE = 19200 
TIMEOUT = 2
WRTIMEOUT = 2
DATAVALID = 240
SLEEP_AFTER_LOAD = 10
CONNECTION_BAD_TIMEOUT = 30


###########################################################################

# Device configuration data

TYPE_INT8 = 1 
TYPE_INT16 = 2
TYPE_INT32 = 3 
TYPE_UINT8 = 4 
TYPE_UINT16 = 5
TYPE_UINT32 = 6
TYPE_INT16_10 = 7
TYPE_INT8_10 = 8

TYPE_LENGTHS = { TYPE_INT8: 1, TYPE_INT16: 2, TYPE_INT32: 4, \
                 TYPE_UINT8: 1, TYPE_UINT16: 2, TYPE_UINT32: 4, \
                 TYPE_INT16_10: 2, TYPE_INT8_10:1 }

NIBE_DEVICES = { 'DEFAULT': [ [0x00, 'Tuotekoodi', TYPE_INT8], \
                              [0x01, 'LV lampotila', TYPE_INT16_10], \
                              [0x02, 'LV aloitus', TYPE_INT8], \
                              [0x03, 'LV lopetus', TYPE_INT8], \
                              [0x04, 'LLV lopetus', TYPE_INT8], \
                              [0x05, 'LVV kompressori lopetus', TYPE_INT8], \
                              [0x06, 'LVV jakso', TYPE_INT8], \
                              [0x07, 'Kayttoaika minuutti', TYPE_INT8], \
                              [0x08, 'Kayttoaika tunti', TYPE_UINT32], \
                              [0x09, 'Menovesilampotila', TYPE_INT16_10], \
                              [0x0a, 'Menovesilampotila (laskettu)', TYPE_INT16_10], \
                              [0x0b, 'Lampokayra', TYPE_INT8], \
                              [0x0c, 'Rinnakkaissiirto', TYPE_INT8], \
                              [0x0d, 'LJ minimi', TYPE_INT8], \
                              [0x0e, 'LJ maksimi', TYPE_INT8], \
                              [0x0f, 'Ulkoinen kompensointi', TYPE_INT8], \
                              [0x10, 'LJ paluulampotila', TYPE_INT16_10], \
                              [0x11, 'LJ paluulampotila maksimi', TYPE_INT8], \
                              [0x12, 'Asteminuutit', TYPE_INT16], \
                              [0x13, 'Menovesilampotila lisa', TYPE_INT16_10], \
                              [0x14, 'Menovesilampotila lisa (laskettu)', TYPE_INT16_10], \
                              [0x15, 'Lampokayra lisa', TYPE_INT8], \
                              [0x16, 'Rinnakkaissiirto lisa', TYPE_INT8], \
                              [0x17, 'LJ minimi lisa', TYPE_INT8], \
                              [0x18, 'LJ maksimi lisa', TYPE_INT8], \
                              [0x19, 'Ulkoinen kompensointi lisa', TYPE_INT8], \
                              [0x1a, 'LJ paluulampotila lisa', TYPE_INT16_10], \
                              [0x1b, 'Ulkolampotila', TYPE_INT16_10], \
                              [0x1c, 'Ulkolampotila keskiarvo', TYPE_INT16_10], \
                              [0x1d, 'Keruulampotila sisaan', TYPE_INT16_10], \
                              [0x1e, 'Keruulampotila ulos', TYPE_INT16_10], \
                              [0x1f, 'Kaynnistyskerrat kompressori', TYPE_UINT32], \
                              [0x20, 'Kayntikerrat kompressori minuutit', TYPE_INT8], \
                              [0x21, 'Kayntikerrat kompressori tunnit', TYPE_INT32], \
                              [0x22, 'Kuumakaasulampotila', TYPE_INT16_10], \
                              [0x23, 'Nestelampotila', TYPE_INT16_10], \
                              [0x24, 'Imukaasulampotila', TYPE_INT16_10], \
                              [0x25, 'Lauhdin LJ-meno', TYPE_INT16_10], \
                              [0x26, 'Huonelampotila', TYPE_INT16_10], \
                              [0x27, 'Asetettu huonelampotila', TYPE_INT16_10], \
                              [0x28, 'Kesatila lampotila', TYPE_INT8], \
                              [0x29, 'Talvitila lampotila', TYPE_INT8], \
                              [0x2a, 'Sahkon kulutus L1', TYPE_INT16_10], \
                              [0x2b, 'Sahkon kulutus L2', TYPE_INT16_10], \
                              [0x2c, 'Sahkon kulutus L3', TYPE_INT16_10], \
                              [0x2d, 'Kayttoaika lisalampo minuutit', TYPE_INT8], \
                              [0x2e, 'kayttoaika lisalampo tunnit', TYPE_INT32], \
                              [0x2f, 'Sahkokattila kaytto', TYPE_INT8], \
                              [0x30, 'Shunttiryhma 2', TYPE_INT8], \
                              [0x31, 'Lattiankuivaus', TYPE_INT8], \
                              [0x32, 'Allasohjaus', TYPE_INT8], \
                              [0x33, 'Tehdasasetus', TYPE_INT8], \
                              [0x34, 'Jaahdytys systeemi', TYPE_INT8], \
                              [0x35, 'Kayttotilaasetukset', TYPE_INT8], \
                              [0x36, 'Lamminvesi lisa', TYPE_INT8], \
                              [0x37, 'Ulkoinen kompensointi', TYPE_INT16], \
                              [0x38, 'Huonekompensointi', TYPE_INT8], \
                              [0x39, 'Korkea paluulampotila ym', TYPE_INT16], \
                              [0x3a, 'Kiertopumppu ym', TYPE_INT8], \
                              [0x3b, 'Lisalampo ym', TYPE_INT8], \
                              [0x3c, 'Jaahdytys', TYPE_INT16], \
                              [0x3d, 'RCU 1', TYPE_INT8], \
                              [0x3e, 'RCU 2', TYPE_INT8], \
                              [0x3f, 'Ei kaytossa 1', TYPE_INT8], \
                              [0x40, 'F1120 lamminvesivaraaja', TYPE_INT8], \
                              [0x41, 'F1120 kaasu/oljy kytketty', TYPE_INT8], \
                              [0x42, 'F1120 sahkopatruuna', TYPE_INT8], \
                              [0x43, 'LV Lampotila yla', TYPE_INT16_10], \
                              [0x44, 'Allaslampotila', TYPE_INT16_10], \
                              [0x45, 'Vuosi', TYPE_INT16], \
                              [0x46, 'Kuukausi', TYPE_INT16], \
                              [0x47, 'Paiva', TYPE_INT16], \
                              [0x48, 'Tunti', TYPE_INT16], \
                              [0x49, 'Minuutti', TYPE_INT16], \
                              [0x4A, 'Halytys nollaus', TYPE_INT8], \
                              [0x4B, 'Pikakaynnistys', TYPE_INT8], \
                              [0x4C, 'Allaslampotila asetettu', TYPE_INT8], \
                              [0x4D, 'Ero lampotila allas', TYPE_INT8_10], \
                              [0x4E, 'Jaahdytyskayra', TYPE_INT8], \
                              [0x4F, 'Rinnakkaissiirto jaahdytys', TYPE_INT8], \
                              [0x50, 'Lahtolampo jaahdytys', TYPE_INT8], \
                              [0x51, 'Kompressorin lahtoarvo', TYPE_INT16], \
                              [0x52, 'Lisalampo lahtoarvo', TYPE_INT16], \
                              [0x53, 'Sulakearvo', TYPE_INT16], \
                              [0x54, 'Maksimi sahkoteho', TYPE_INT16], \
                              [0x55, 'Ero lisalampo porras', TYPE_INT8], \
                              [0x56, 'LJ-ero LP', TYPE_INT8], \
                              [0x57, 'Ero LP-lisalampo', TYPE_INT8], \
                              [0x58, 'Ei kaytossa 2', TYPE_INT8], \
                              [0x59, 'Lattiakuivatus aikajakso 1', TYPE_INT8], \
                              [0x5A, 'Lattiakuivatus max lampotila aikajakso 1', TYPE_INT8], \
                              [0x5B, 'Lattiakuivatus aikajakso 2', TYPE_INT8], \
                              [0x5C, 'Lattiakuivatus max lampotila aikajakso 2', TYPE_INT8], \
                              [0x5D, 'HPAC aktiivi viilennys indikaattori', TYPE_INT16], \
                              [0x5E, 'HPAC passiivi viilennys indikaattori', TYPE_INT16], \
                              [0x5F, 'Jaksollinen lisalammitys indikaattori', TYPE_INT16], \
                              [0x60, 'Halytys', TYPE_INT8] \
                        ] \
                }



###########################################################################

# Classes

class NibeSerial(threads.Thread, log.Logging):
    def __init__(self, port, device):
        threads.Thread.__init__(self)
        log.Logging.__init__(self, 'NibeSerial')
        
        global serial
        serial = __import__('serial') 
        
        self.data = {}
        self.data_lock = threads.Lock()
  
        self.SERPORT = port
        self.NIBE_DEVICE = device
        self.serio = 0
          
        self.typelens = {}  
          
        self.LOCK = None
        
    def setPort(self, port):
        self.SERPORT = port
        
    def setDevice(self, device):
        self.NIBE_DEVICE = device
        
    def run(self):
        self.initTypelens()
        
        nr_registers = len(NIBE_DEVICES[self.NIBE_DEVICE])
        
        lastrecv = time.time()
        try:              
            while self.isRunning():
                if not self.isOpen():
                    if not self.openPort():
                        self.Log("Cannot open serial port.")
                        self.setFail()
                        break
                    
                self.Debug("Flushing serial input buffer.")
                temp = ' '
                while self.isRunning() and len(temp) > 0 and self.serio.inWaiting() > 0:
                    temp = self.serio.read(1)

                errcnt = 0
                registers_found = 0
                while self.isRunning() and registers_found < nr_registers:                
                    res = ''
                    self.Debug("Sending 0x06")
                    self.serio.write('\x06\n')                    
                    time.sleep(0.2)
                    while self.isRunning() and self.serio.inWaiting() > 0:
                        blocktime = time.time()                
                        temp = self.serio.read(1)
                        if len(temp) <= 0:
                            if time.time() - blocktime < (TIMEOUT / 2.0):
                                errcnt = errcnt + 1
                                if errcnt > 5:
                                    self.Log("Repeating error while reading Nibe serial data. Terminating Nibe thread.")
                                    self.setFail()
                                    break
                            else:                                
                                # timed out 
                                self.Debug("Timeout when reading Nibe serial data.")
                                break
                        else:
                            errcnt = 0
                            res = res + temp
                    
                    if len(res) > 0:
                        lastrecv = time.time()
                        self.Debug("Received:\n" + log.dumpBuffer(res))
                
                    stat = 1
                    while self.isRunning() and stat != 0 and len(res) > 0:                    
                        stat = checkNibeMessage(res)
                        if stat > 0:
                            rcvdata = res[:stat]
                            res = res[stat:]
                            registers_found = registers_found + self.handleBuffer(rcvdata)
                        elif stat == -1:
                            res = res[1:]
                    
                    if time.time() - lastrecv > CONNECTION_BAD_TIMEOUT: 
                        self.Log("Received no data timeout. Terminating Nibe thread.")
                        self.setFail()
                        break 

                self.closePort()
                                
                if self.isRunning():
                    time.sleep(SLEEP_AFTER_LOAD)

        except Exception as e:
            self.Log("Exception: " + e.__str__())
            self.setFail()
        except IOError as ioe:
            self.Log("IOError: " + ioe.__str__())
            self.setFail()

        self.closePort()
       
        self.Log("Nibe serial thread stopped.")
    
    
    def handleBuffer(self, buff):
        n_data = 0
        temp = getNibeDataPart(buff)
        if self.data_lock.lock_wait():
            id = 0
            l = len(temp)
            i = 0
            while i < l:
                id = ord(temp[i]) << 8
                id = id + ord(temp[i+1])
                i = i + 2
                dl = self.typelens[id]
                self.data[id] = [time.time(), temp[i:i+dl]]
                self.Debug("Got data for id %d: %s" % (id, repr(temp[i:i+dl])))
                n_data = n_data + 1
                i = i + dl        
            self.data_lock.free()
        else:
            self.Log("Cannot get data lock.")
            
        return n_data
    
    def initTypelens(self):
        self.typelens= {}
        for t in NIBE_DEVICES[self.NIBE_DEVICE]:
            self.typelens[t[0]] = TYPE_LENGTHS[t[2]]
        
    def openPort(self):
        if not NIBE_DEVICES.__contains__(self.NIBE_DEVICE):
            self.Log("ERROR: Invalid NIBE device type: " + self.NIBE_DEVICE)
            return 0

        if not self.LOCK.lock():
            self.Log("ERROR: Unable to aquire lockfile for nibeSerial port: " + self.LOCK.getName())
            return 0

        try:
            self.serio = serial.Serial(port=self.SERPORT,baudrate=BAUDRATE, \
                                bytesize=serial.EIGHTBITS, \
                                parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, \
                                xonxoff=0, rtscts=0, dsrdtr=0, timeout=TIMEOUT, writeTimeout=WRTIMEOUT)
            if not self.serio.isOpen():
                self.serio = 0
                self.LOCK.free()
                return 0 
        except:
            self.serio = 0
            self.LOCK.free()
            return 0
        
        self.Debug("Opened nibeSerial port: " + self.SERPORT)
        return 1
        
    def closePort(self):
        if self.serio:
            try:
                self.serio.close()
            except:
                pass
            self.serio = 0
        self.LOCK.free()
        self.Debug("Closed nibeSerial port: " + self.SERPORT)

    def isOpen(self):
        if self.serio and self.serio.isOpen():
            return 1
        return 0

    def runQueryCommand(self, cmd):
        if self.hasTerminated() and self.isFailed():
            if not self.startModule():
                self.Log("Could not restart module after being failed.")
            else:
                self.Log("Module restarted after being failed.")
        
        id = 0
        type = 0
        for t in NIBE_DEVICES[self.NIBE_DEVICE]:
            if t[1] == cmd:
                id = t[0]
                type = t[2]
                break

        if type == 0:
            self.Log("ERROR: Invalid NIBE key: " + cmd)
            return ""

        res = self.runQueryId(id)
        if res != None:
            return convertNibeMessage(type, res)
        return ""

    def startModule(self):
        if self.LOCK == None:
            self.LOCK = lockfile.LockFile(self.SERPORT)
            
        if not self.isOpen():
            self.openPort()
        if self.isOpen():
            self.start()
            return 1
        else:
            self.setFail()
            self.setTerminated()
            
        return 0

    def runQueryId(self, id):
        self.Debug("Running nibeSerial query with id " + repr(id))

        res = None
        if self.data_lock.lock_wait():
            if self.data.__contains__(id):
                temp = self.data[id]
                if (time.time() - temp[0]) <= DATAVALID:
                    res = temp[1]
                else:
                    self.Debug("Data expired with id " + repr(id))
            else:
                self.Debug("No data found with id " + repr(id))
            self.data_lock.free()
        else:
            self.Log("Cannot get data lock.")
        return res   

        
###########################################################################

# Functions

# returns int
#   -1 = error
#   0 = ok, but not ready
#   > 0 = ok, lenght of valid data
def checkNibeMessage(data):
    l = len(data)
    dl = 0
    if l <= 0:
        return 0

    # first byte is '\xC0'
    if l >= 1 and data[0] != '\xC0':
        return -1

    # fourth byte is data part len
    if l >= 4:
        dl = ord(data[3])
    else:
        return 0
    
    # check CRC
    if l >= dl + 5:
        crc = 0
        for i in range(dl+4):
            crc = crc ^ ord(data[i])
        if crc != ord(data[dl+4]):
            return -1
    else:
        return 0
    
    return dl + 5

def getNibeDataPart(data):
    dl = ord(data[3])
    return data[4:4+dl]
    
def convertNibeMessage(type, data):
    if type == TYPE_INT8:
        temp = ord(data[0])
        temp = binary.twosComplementToInt(temp, 8)
        temp = "%d" % temp
        return temp
    elif type == TYPE_INT16:
        temp = (ord(data[0]) << 8) + ord(data[1])
        temp = binary.twosComplementToInt(temp, 16)
        temp = "%d" % temp
        return temp
    elif type == TYPE_INT32:
        temp = (ord(data[0]) << 24) + (ord(data[1]) << 16) + (ord(data[2]) << 8) + ord(data[3])
        temp = binary.twosComplementToInt(temp, 32)
        temp = "%d" % temp
        return temp
    elif type == TYPE_UINT8:
        temp = ord(data[0])
        temp = "%d" % temp
        return temp
    elif type == TYPE_UINT16:
        temp = (ord(data[0]) << 8) + ord(data[1])
        temp = "%d" % temp
        return temp
    elif type == TYPE_UINT32:
        temp = (ord(data[0]) << 24) + (ord(data[1]) << 16) + (ord(data[2]) << 8) + ord(data[3])
        temp = "%d" % temp
        return temp
    elif type == TYPE_INT16_10:
        temp = (ord(data[0]) << 8) + ord(data[1])
        temp = binary.twosComplementToInt(temp, 16)
        temp = "%.1f" % (temp / 10.0)
        return temp
    elif type == TYPE_INT8_10:
        temp = ord(data[0])
        temp = binary.twosComplementToInt(temp, 8)
        temp = "%.1f" % (temp / 10.0)
        return temp

    return ""


