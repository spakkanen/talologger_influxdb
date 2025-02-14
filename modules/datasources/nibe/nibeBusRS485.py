#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            nibeRS485Serial.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#                  (Nibe datapoint table originally from OpenHab Nibe binding
#                   subproject by Pauli Anttila. Added datapoints gathered by
#                   "tk-" at Maal�mp�foorumi.) 
#
# Version:         0.1h
#
# Date:            03.03.2017
#
# Description:     Library to communicate with the Nibe heat pump controllers
#                  using RS485 adapter connected to Nibe bus or OpenHab
#                  NibeGW producing UDP frame packets.
#                  
# Supported devices: 
#                  Nibe devices compatible with Nibe MODBUS 40 communications
#                  module.
#
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
# 
#                  Python Serial Port Extension: pySerial  
#                  (http://pyserial.wiki.sourceforge.net/pySerial)
#
###########################################################################

# Imports

import sys, os 
import string
import time 
import socket

from modules.core import threads
from modules.core import log
from modules.utils import lockfile
from modules.utils import binary

# pySerial module, not loaded until init of NibeRS485Serial class instance
serial = None

###########################################################################

# Constants

BAUDRATE = 9600
TIMEOUT = 5
WRTIMEOUT = 2
DATAVALID = 240
QUERY_RESPONSE_TIMEOUT = 10
SLEEP_AFTER_FAIL = 10
UDP_RECEIVE_BUFFER_SIZE = 2048

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
TYPE_INT32_10 = 9
TYPE_UINT32_10 = 10
TYPE_UINT8_10 = 11
TYPE_INT16_100 = 12
TYPE_UINT16_100 = 13
TYPE_UINT16_10 = 14

TYPE_R = 1
TYPE_RW = 2

NIBE_DEVICES = { 'DEFAULT': [ \
        [40004, 'BT1 Outdoor temp', TYPE_INT16_10, TYPE_R, 'C', 'Outdoor temperature'], \
        [40005, 'EB23-BT2 Supply temp S4', TYPE_INT16_10, TYPE_R, 'C', 'Supply temperature for system 4'], \
        [40006, 'EB22-BT2 Supply temp S3', TYPE_INT16_10, TYPE_R, 'C', 'Supply temperature for system 3'], \
        [40007, 'EB21-BT2 Supply temp S2', TYPE_INT16_10, TYPE_R, 'C', 'Supply temperature for system 2'], \
        [40008, 'BT2 supply temp S1', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40011, 'EB100-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40012, 'EB100-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [40013, 'BT7 Hot Water top', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40014, 'BT6 Hot Water load', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40015, 'EB100-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40016, 'EB100-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40017, 'EB100-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40018, 'EB100-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40019, 'EB100-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40022, 'EB100-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40025, 'EB100-BT20 Exhaust air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40026, 'EB100-BT21 Vented air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40028, 'AZ1-BT26 Temp Collector in FLM 1', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40029, 'AZ1-BT27 Temp Collector out FLM 1', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40030, 'EB23-BT50 Room Temp S4', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40031, 'EB22-BT50 Room Temp S3', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40032, 'EB21-BT50 Room Temp S2', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40033, 'BT50 Room Temp S1', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40042, 'CL11-BT51 Pool 1 Temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40043, 'EP8-BT53 Solar Panel Temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40044, 'EP8-BT54 Solar Load Temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40045, 'EQ1-BT64 PCS4 Supply Temp', TYPE_INT16_10, TYPE_R, 'C', 'PCS4 Only'], \
        [40046, 'EQ1-BT65 PCS4 Return Temp', TYPE_INT16_10, TYPE_R, 'C', 'PCS4 Only'], \
        [40054, 'EB100-FD1 Temperature limiter', TYPE_INT16, TYPE_R, '', ''], \
        [40067, 'BT1 Average', TYPE_INT16_10, TYPE_R, 'C', 'EB100-BT1 Outdoor temperature average'], \
        [40070, 'EM1-BT52 Boiler temperature', TYPE_INT16_10, TYPE_R, 'C', 'Temperature of Boiler'], \
        [40071, 'BT25 external supply temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40072, 'BF1 Flow', TYPE_INT16_10, TYPE_R, 'l/m', ''], \
        [40074, 'EB100-FR1 Anode Status', TYPE_INT16, TYPE_R, '', ''], \
        [40079, 'EB100-BE3 Current Phase 3', TYPE_INT32_10, TYPE_R, 'A', ''], \
        [40081, 'EB100-BE2 Current Phase 2', TYPE_INT32_10, TYPE_R, 'A', ''], \
        [40083, 'EB100-BE1 Current Phase 1', TYPE_INT32_10, TYPE_R, 'A', ''], \
        [40085, 'EB100-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40086, 'EB100-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40087, 'EB100-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40088, 'EB100-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40089, 'EB100-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40100, 'EB100-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40106, 'CL11-BT51 Pool 2 Temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40107, 'EB100-BT20-2 Exhaust air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40108, 'EB100-BT20-3 Exhaust air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40109, 'EB100-BT20-4 Exhaust air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40110, 'EB100-BT21-2 Vented air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40111, 'EB100-BT21-3 Vented air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40112, 'EB100-BT21-4 Vented air temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40113, 'AZ1-BT26 Temp Collector in FLM 4', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40114, 'AZ1-BT26 Temp Collector in FLM 3', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40115, 'AZ1-BT26 Temp Collector in FLM 2', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40116, 'AZ1-BT27 Temp Collector out FLM 4', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40117, 'AZ1-BT27 Temp Collector out FLM 3', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40118, 'AZ1-BT27 Temp Collector out FLM 2', TYPE_INT16_10, TYPE_R, 'C', 'Connected to the FLM module'], \
        [40127, 'EB23-BT3 Return temp S4', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature for system 4'], \
        [40128, 'EB22-BT3 Return temp S3', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature for system 3'], \
        [40129, 'EB21-BT3 Return temp S2', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature for system 2'], \
        [40131, 'EB100-EP15-BP8 Pressure Transmitter', TYPE_INT16_10, TYPE_R, 'C', 'Temperture reported by the pressure transmitter'], \
        [40132, 'EB100-EP14-BP8 Pressure Transmitter', TYPE_INT16_10, TYPE_R, 'C', 'Temperture reported by the pressure transmitter'], \
        [40145, 'EB100-EP15-BT29', TYPE_INT16_10, TYPE_R, 'C', 'Compressor oil temperature'], \
        [40146, 'EB100-EP14-BT29', TYPE_INT16_10, TYPE_R, 'C', 'Compressor oil temperature'], \
        [40147, 'BT70 HW supply temp', TYPE_INT16_10, TYPE_R, 'C', 'Hot water supply temperature'], \
        [40152, 'BT71 Ext Return temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [40155, 'EQ1-BT57 Collector temp', TYPE_INT16_10, TYPE_R, 'C', 'External collector temperature for ACS'], \
        [40156, 'EQ1-BT75 Heatdump temp', TYPE_INT16_10, TYPE_R, 'C', 'Heating medium dump temperature for ACS'], \
        [43001, 'Software version', TYPE_UINT16, TYPE_R, '', ''], \
        [43005, 'Degree Minutes', TYPE_INT16_10, TYPE_RW, '', ''], \
        [43006, 'Calculated Supply Temperature S4', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43007, 'Calculated Supply Temperature S3', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43008, 'Calculated Supply Temperature S2', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43009, 'Calculated Supply Temperature S1', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43010, 'Calculated cooling supply temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43013, 'Freeze Protection Status', TYPE_UINT8, TYPE_R, '', '1 = Freeze protection active'], \
        [43024, 'Status cooling', TYPE_UINT8, TYPE_R, '', '0=OFF, 1=ON'], \
        [43081, 'Tot optime add', TYPE_INT32_10, TYPE_R, 'h', 'Total electric additive operation time'], \
        [43084, 'Int eladd Power', TYPE_INT16_100, TYPE_R, 'kW', 'Current power from the internal electrical addition'], \
        [43086, 'Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what heating action (HW/heat/pool) currently prioritised 10=Off 20=Hot Water 30=Heat 40=Pool 41=Pool 2 50=Transfer 60=Cooling'], \
        [43091, 'Int eladd State', TYPE_UINT8, TYPE_R, '', 'State of the internal electrical addition'], \
        [43103, 'HPAC state', TYPE_UINT8, TYPE_R, '', 'State of the HPAC cooling accessory.'], \
        [43108, 'Fan speed current', TYPE_UINT8, TYPE_R, '%', 'The current fan speed after scheduling and blocks are considered'], \
        [43136, 'Compressor freq current', TYPE_UINT16_10, TYPE_R, 'Hz', 'The frequency of the compressor at the moment'], \
        [43180, 'HWC Pump Status GP11', TYPE_UINT8, TYPE_R, '', 'Hot water circulation pump status. 1=on, 0=off'], \
        [43230, 'Accumulated energy', TYPE_UINT32_10, TYPE_R, 'kWh', ''], \
        [43239, 'Tot HW optime add', TYPE_INT32_10, TYPE_R, 'h', 'Total electric additive operation time in hot water mode'], \
        [43395, 'HPAC relays', TYPE_UINT8, TYPE_R, '', ''], \
        [43414, 'Compressor starts EB100-EP15', TYPE_INT32, TYPE_R, '', 'Number of compressorer starts'], \
        [43416, 'Compressor starts EB100-EP14', TYPE_INT32, TYPE_R, '', 'Number of compressorer starts'], \
        [43418, 'Tot optime compr EB100-EP15', TYPE_INT32, TYPE_R, 'h', 'Total compressorer operation time'], \
        [43420, 'Tot optime compr EB100-EP14', TYPE_INT32, TYPE_R, 'h', 'Total compressorer operation time'], \
        [43422, 'Tot HW optime compr EB100-EP15', TYPE_INT32, TYPE_R, 'h', 'Total compressorer operation time in hot water mode'], \
        [43424, 'Tot HW optime compr EB100-EP14', TYPE_INT32, TYPE_R, 'h', 'Total compressorer operation time in hot water mode'], \
        [43426, 'Compressor State EP15', TYPE_UINT8, TYPE_R, '', '20 = Stopped, 40 = Starting, 60 = Running, 100 = Stopping'], \
        [43427, 'Compressor State EP14', TYPE_UINT8, TYPE_R, '', '20 = Stopped, 40 = Starting, 60 = Running, 100 = Stopping'], \
        [43434, 'Compressor status EP15', TYPE_UINT8, TYPE_R, '', 'Indicates if the compressor is supplied with power 0=Off 1=On'], \
        [43435, 'Compressor status EP14', TYPE_UINT8, TYPE_R, '', 'Indicates if the compressor is supplied with power 0=Off 1=On'], \
        [43436, 'HM-pump Status EP15', TYPE_UINT8, TYPE_R, '', 'Status of the circ. pump'], \
        [43437, 'HM-pump Status EP14', TYPE_UINT8, TYPE_R, '', 'Status of the circ. pump'], \
        [43438, 'Brinepump Status EP15', TYPE_UINT8, TYPE_R, '', 'Status of the Brine pump'], \
        [43439, 'Brinepump Status EP14', TYPE_UINT8, TYPE_R, '', 'Status of the Brine pump'], \
        [43513, 'PCA-Base Relays EP15', TYPE_UINT8, TYPE_R, '', 'Indicates the active relays on the PCA-Base card. The information is binary encoded'], \
        [43514, 'PCA-Base Relays EP14', TYPE_UINT8, TYPE_R, '', 'Indicates the active relays on the PCA-Base card. The information is binary encoded'], \
        [43516, 'PCA-Power Relays EP14', TYPE_UINT8, TYPE_R, '', 'Indicates the active relays on the PCA-Power card. The information is binary encoded'], \
        [43600, 'EB108-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43601, 'EB108-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43602, 'EB108-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43603, 'EB108-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43604, 'EB108-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43605, 'EB108-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43606, 'EB108-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43607, 'EB108-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43608, 'EB108-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43609, 'EB108-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43610, 'EB108-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43611, 'EB108-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43612, 'EB108-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43613, 'EB108-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43614, 'EB108-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43616, 'EB108-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43618, 'EB108-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43620, 'EB108-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43621, 'EB108-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43622, 'EB108-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43623, 'EB108-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43624, 'EB108-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43625, 'EB108-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43626, 'EB108-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43627, 'EB108-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43628, 'EB108-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43629, 'EB108-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43630, 'EB108-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43631, 'EB108-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43632, 'EB108-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43633, 'EB108-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43634, 'EB108-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43635, 'EB108-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43637, 'EB108-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43639, 'EB108-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43641, 'EB108-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43662, 'EB107-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43663, 'EB107-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43664, 'EB107-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43665, 'EB107-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43666, 'EB107-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43667, 'EB107-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43668, 'EB107-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43669, 'EB107-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43670, 'EB107-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43671, 'EB107-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43672, 'EB107-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43673, 'EB107-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43674, 'EB107-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43675, 'EB107-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43676, 'EB107-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43678, 'EB107-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43680, 'EB107-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43682, 'EB107-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43683, 'EB107-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43684, 'EB107-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43685, 'EB107-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43686, 'EB107-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43687, 'EB107-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43688, 'EB107-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43689, 'EB107-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43690, 'EB107-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43691, 'EB107-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43692, 'EB107-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43693, 'EB107-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43694, 'EB107-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43695, 'EB107-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43696, 'EB107-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43697, 'EB107-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43699, 'EB107-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43701, 'EB107-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43703, 'EB107-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43724, 'EB106-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43725, 'EB106-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43726, 'EB106-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43727, 'EB106-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43728, 'EB106-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43729, 'EB106-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43730, 'EB106-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43731, 'EB106-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43732, 'EB106-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43733, 'EB106-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43734, 'EB106-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43735, 'EB106-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43736, 'EB106-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43737, 'EB106-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43738, 'EB106-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43740, 'EB106-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43742, 'EB106-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43744, 'EB106-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43745, 'EB106-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43746, 'EB106-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43747, 'EB106-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43748, 'EB106-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43749, 'EB106-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43750, 'EB106-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43751, 'EB106-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43752, 'EB106-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43753, 'EB106-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43754, 'EB106-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43755, 'EB106-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43756, 'EB106-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43757, 'EB106-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43758, 'EB106-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43759, 'EB106-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43761, 'EB106-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43763, 'EB106-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43765, 'EB106-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43786, 'EB105-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43787, 'EB105-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43788, 'EB105-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43789, 'EB105-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43790, 'EB105-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43791, 'EB105-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43792, 'EB105-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43793, 'EB105-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43794, 'EB105-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43795, 'EB105-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43796, 'EB105-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43797, 'EB105-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43798, 'EB105-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43799, 'EB105-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43800, 'EB105-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43802, 'EB105-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43804, 'EB105-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43806, 'EB105-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43807, 'EB105-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43808, 'EB105-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43809, 'EB105-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43810, 'EB105-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43811, 'EB105-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43812, 'EB105-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43813, 'EB105-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43814, 'EB105-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43815, 'EB105-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43816, 'EB105-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43817, 'EB105-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43818, 'EB105-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43819, 'EB105-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43820, 'EB105-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43821, 'EB105-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43823, 'EB105-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43825, 'EB105-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43827, 'EB105-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43848, 'EB104-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43849, 'EB104-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43850, 'EB104-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43851, 'EB104-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43852, 'EB104-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43853, 'EB104-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43854, 'EB104-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43855, 'EB104-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43856, 'EB104-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43857, 'EB104-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43858, 'EB104-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43859, 'EB104-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43860, 'EB104-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43861, 'EB104-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43862, 'EB104-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43864, 'EB104-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43866, 'EB104-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43868, 'EB104-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43869, 'EB104-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43870, 'EB104-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43871, 'EB104-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43872, 'EB104-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43873, 'EB104-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43874, 'EB104-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43875, 'EB104-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43876, 'EB104-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43877, 'EB104-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43878, 'EB104-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43879, 'EB104-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43880, 'EB104-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43881, 'EB104-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43882, 'EB104-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43883, 'EB104-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43885, 'EB104-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43887, 'EB104-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43889, 'EB104-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43910, 'EB103-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43911, 'EB103-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43912, 'EB103-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43913, 'EB103-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43914, 'EB103-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43915, 'EB103-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43916, 'EB103-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43917, 'EB103-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43918, 'EB103-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43919, 'EB103-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43920, 'EB103-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43921, 'EB103-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43922, 'EB103-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43923, 'EB103-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43924, 'EB103-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43926, 'EB103-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43928, 'EB103-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43930, 'EB103-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43931, 'EB103-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43932, 'EB103-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43933, 'EB103-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43934, 'EB103-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43935, 'EB103-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43936, 'EB103-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43937, 'EB103-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43938, 'EB103-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43939, 'EB103-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43940, 'EB103-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43941, 'EB103-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43942, 'EB103-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43943, 'EB103-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43944, 'EB103-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43945, 'EB103-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43947, 'EB103-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43949, 'EB103-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43951, 'EB103-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43972, 'EB102-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43973, 'EB102-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43974, 'EB102-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43975, 'EB102-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43976, 'EB102-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43977, 'EB102-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43978, 'EB102-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43979, 'EB102-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43980, 'EB102-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43981, 'EB102-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [43982, 'EB102-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [43983, 'EB102-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [43984, 'EB102-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43985, 'EB102-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [43986, 'EB102-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [43988, 'EB102-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43990, 'EB102-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [43992, 'EB102-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [43993, 'EB102-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [43994, 'EB102-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43995, 'EB102-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43996, 'EB102-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43997, 'EB102-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43998, 'EB102-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [43999, 'EB102-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44000, 'EB102-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44001, 'EB102-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44002, 'EB102-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [44003, 'EB102-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [44004, 'EB102-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [44005, 'EB102-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44006, 'EB102-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44007, 'EB102-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [44009, 'EB102-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44011, 'EB102-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44013, 'EB102-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [44034, 'EB101-EP15-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [44035, 'EB101-EP15-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44036, 'EB101-EP15-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44037, 'EB101-EP15-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44038, 'EB101-EP15-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44039, 'EB101-EP15-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44040, 'EB101-EP15-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44041, 'EB101-EP15-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44042, 'EB101-EP15-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44043, 'EB101-EP15 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [44044, 'EB101-EP15 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [44045, 'EB101-EP15 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [44046, 'EB101-EP15 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44047, 'EB101-EP15 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44048, 'EB101-EP15 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [44050, 'EB101-EP15 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44052, 'EB101-EP15 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44054, 'EB101-EP15 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [44055, 'EB101-EP14-BT3 Return temp', TYPE_INT16_10, TYPE_R, 'C', 'Return temperature'], \
        [44056, 'EB101-EP14-BT10 Brine in temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44057, 'EB101-EP14-BT11 Brine out temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44058, 'EB101-EP14-BT12 Cond out', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44059, 'EB101-EP14-BT14 Hot gas temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44060, 'EB101-EP14-BT15 Liquid line', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44061, 'EB101-EP14-BT17 Suction', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44062, 'EB101-EP14-BT29 Compr Oil temp', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44063, 'EB101-EP14-BP8 Pressure transmitter', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44064, 'EB101-EP14 Compressor State', TYPE_UINT8, TYPE_R, '', ''], \
        [44065, 'EB101-EP14 Compr time to start', TYPE_UINT8, TYPE_R, '', ''], \
        [44066, 'EB101-EP14 Relay status', TYPE_UINT16, TYPE_R, '', ''], \
        [44067, 'EB101-EP14 Heat med pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44068, 'EB101-EP14 Brine pump status', TYPE_UINT8, TYPE_R, '', ''], \
        [44069, 'EB101-EP14 Compressor starts', TYPE_UINT32, TYPE_R, '', ''], \
        [44071, 'EB101-EP14 Tot optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44073, 'EB101-EP14 Tot HW optime compr', TYPE_UINT32, TYPE_R, 'h', ''], \
        [44075, 'EB101-EP14 Alarm number', TYPE_UINT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [44138, 'EB108-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44139, 'EB108-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44151, 'EB107-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44152, 'EB107-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44164, 'EB106-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44165, 'EB106-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44177, 'EB105-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44178, 'EB105-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44190, 'EB104-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44191, 'EB104-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44203, 'EB103-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44204, 'EB103-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44216, 'EB102-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44217, 'EB102-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44229, 'EB101-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44230, 'EB101-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44242, 'EB100-EP15 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44243, 'EB100-EP14 Prio', TYPE_UINT8, TYPE_R, '', 'Indicates what need is assigned to the compressor module, 0 = Off, 1 = Heat, 2 = Hot water, 3 = Pool 1, 4 = Pool2'], \
        [44266, 'Cool Degree Minutes', TYPE_INT16_10, TYPE_RW, '', ''], \
        [44267, 'Calc Cooling Supply Temperature S4', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44268, 'Calc Cooling Supply Temperature S3', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44269, 'Calc Cooling Supply Temperature S2', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44270, 'Calc Cooling Supply Temperature S1', TYPE_INT16_10, TYPE_R, 'C', ''], \
        [44276, 'State ACS', TYPE_UINT8, TYPE_R, '', 'The state of the ACS accessory'], \
        [44277, 'State ACS heatdump', TYPE_UINT8, TYPE_R, '', 'The state of the heatdump in the ACS accessory'], \
        [44278, 'State ACS cooldump', TYPE_UINT8, TYPE_R, '', 'The state of the cooldump in the ACS accessory'], \
        [44282, 'Used cprs HW', TYPE_UINT8, TYPE_R, '', 'The number of compressors thats currently producing hot water'], \
        [44283, 'Used cprs heat', TYPE_UINT8, TYPE_R, '', 'The number of compressors thats currently producing heating'], \
        [44284, 'Used cprs pool 1', TYPE_UINT8, TYPE_R, '', 'The number of compressors thats currently producing poolheating for pool 1'], \
        [44285, 'Used cprs pool 2', TYPE_UINT8, TYPE_R, '', 'The number of compressors thats currently producing poolheating for pool 2'], \
        [44320, 'Used cprs cool', TYPE_UINT8, TYPE_R, '', 'The number of compressors thats currently producing active cooling'], \
        [44331, 'Software release', TYPE_UINT8, TYPE_R, '', ''], \
        [45001, 'Alarm number', TYPE_INT16, TYPE_R, '', 'The value indicates the most severe current alarm'], \
        [47004, 'Heat curve S4', TYPE_INT8, TYPE_RW, '', 'Heat curve to use see manual for the different curves.'], \
        [47005, 'Heat curve S3', TYPE_INT8, TYPE_RW, '', 'Heat curve to use see manual for the different curves.'], \
        [47006, 'Heat curve S2', TYPE_INT8, TYPE_RW, '', 'Heat curve to use see manual for the different curves.'], \
        [47007, 'Heat curve S1', TYPE_INT8, TYPE_RW, '', 'Heat curve to use see manual for the different curves.'], \
        [47008, 'Offset S4', TYPE_INT8, TYPE_RW, '', 'Offset of the heat curve'], \
        [47009, 'Offset S3', TYPE_INT8, TYPE_RW, '', 'Offset of the heat curve'], \
        [47010, 'Offset S2', TYPE_INT8, TYPE_RW, '', 'Offset of the heat curve'], \
        [47011, 'Offset S1', TYPE_INT8, TYPE_RW, '', 'Offset of the heat curve'], \
        [47012, 'Min Supply System 4', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47013, 'Min Supply System 3', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47014, 'Min Supply System 2', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47015, 'Min Supply System 1', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47016, 'Max Supply System 4', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47017, 'Max Supply System 3', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47018, 'Max Supply System 2', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47019, 'Max Supply System 1', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47020, 'Own Curve P7', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47021, 'Own Curve P6', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47022, 'Own Curve P5', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47023, 'Own Curve P4', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47024, 'Own Curve P3', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47025, 'Own Curve P2', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47026, 'Own Curve P1', TYPE_INT8, TYPE_RW, 'C', 'User defined curve point'], \
        [47027, 'Point offset outdoor temp', TYPE_INT8, TYPE_RW, 'C', 'Outdoor temperature point where the heat curve is offset'], \
        [47028, 'Point offset', TYPE_INT8, TYPE_RW, 'C', 'Amount of offset at the point offset temperature'], \
        [47029, 'External adjustment S4', TYPE_INT8, TYPE_RW, '', 'Change of the offset of the heat curve when closing the external adjustment input'], \
        [47030, 'External adjustment S3', TYPE_INT8, TYPE_RW, '', 'Change of the offset of the heat curve when closing the external adjustment input'], \
        [47031, 'External adjustment S2', TYPE_INT8, TYPE_RW, '', 'Change of the offset of the heat curve when closing the external adjustment input'], \
        [47032, 'External adjustment S1', TYPE_INT8, TYPE_RW, '', 'Change of the offset of the heat curve when closing the external adjustment input'], \
        [47033, 'External adjustment with room sensor S4', TYPE_INT16_10, TYPE_RW, 'C', 'Room temperature setting when closing the external adjustment input'], \
        [47034, 'External adjustment with room sensor S3', TYPE_INT16_10, TYPE_RW, 'C', 'Room temperature setting when closing the external adjustment input'], \
        [47035, 'External adjustment with room sensor S2', TYPE_INT16_10, TYPE_RW, 'C', 'Room temperature setting when closing the external adjustment input'], \
        [47036, 'External adjustment with room sensor S1', TYPE_INT16_10, TYPE_RW, 'C', 'Room temperature setting when closing the external adjustment input'], \
        [47041, 'Hot water mode', TYPE_INT8, TYPE_RW, '', ' 0=Economy 1=Normal 2=Luxury'], \
        [47043, 'Start temperature HW Luxury', TYPE_INT16_10, TYPE_RW, 'C', 'Start temperature for heating water'], \
        [47044, 'Start temperature HW Normal', TYPE_INT16_10, TYPE_RW, 'C', 'Start temperature for heating water'], \
        [47045, 'Start temperature HW Economy', TYPE_INT16_10, TYPE_RW, 'C', 'Start temperature for heating water'], \
        [47046, 'Stop temperature Periodic HW', TYPE_INT16_10, TYPE_RW, 'C', 'Temperature where hot water generation will stop'], \
        [47047, 'Stop temperature HW Luxury', TYPE_INT16_10, TYPE_RW, 'C', 'Temperature where hot water generation will stop'], \
        [47048, 'Stop temperature HW Normal', TYPE_INT16_10, TYPE_RW, 'C', 'Temperature where hot water generation will stop'], \
        [47049, 'Stop temperature HW Economy', TYPE_INT16_10, TYPE_RW, 'C', 'Temperature where hot water generation will stop'], \
        [47050, 'Periodic HW', TYPE_INT8, TYPE_RW, '', 'Activates the periodic hot water generation'], \
        [47051, 'Periodic HW Interval', TYPE_INT8, TYPE_RW, 'days', 'Interval between Periodic hot water sessions'], \
        [47054, 'Run time HWC', TYPE_INT8, TYPE_RW, 'min', 'Run time for the hot water circulation system'], \
        [47055, 'Still time HWC', TYPE_INT8, TYPE_RW, 'min', 'Still time for the hot water circulation system'], \
        [47131, 'Language', TYPE_INT8, TYPE_RW, '', 'Display language in the heat pump 0=English 1=Svenska 2=Deutsch 3=Francais 4=Espanol 5=Suomi 6=Lietuviu 7=Cesky 8=Polski 9=Nederlands 10=Norsk 11=Dansk 12=Eesti 13=Latviesu 16=Magyar'], \
        [47133, 'Period pool 2', TYPE_UINT8, TYPE_RW, 'min', ''], \
        [47134, 'Period HW', TYPE_UINT8, TYPE_RW, 'min', ''], \
        [47135, 'Period Heat', TYPE_UINT8, TYPE_RW, 'min', ''], \
        [47136, 'Period Pool', TYPE_UINT8, TYPE_RW, 'min', ''], \
        [47138, 'Operational mode heat medium pump', TYPE_UINT8, TYPE_RW, '', ' 10=Intermittent 20=Continous 30=Economy 40=Auto'], \
        [47139, 'Operational mode brine medium pump', TYPE_UINT8, TYPE_RW, '', ' 10=Intermittent 20=Continuous 30=Economy 40=Auto'], \
        [47206, 'DM start heating', TYPE_INT16, TYPE_RW, '', 'The value the degree minutes needed to be reached for the pump to start heating'], \
        [47207, 'DM start cooling', TYPE_INT16, TYPE_RW, 'DM', ''], \
        [47208, 'DM start addition', TYPE_INT16, TYPE_RW, 'DM', ''], \
        [47209, 'DM between add steps', TYPE_INT16, TYPE_RW, '', 'The number of degree minutes between start of each electric addition step'], \
        [47210, 'DM start add with shunt', TYPE_INT16, TYPE_RW, '', ''], \
        [47212, 'Max int addition power', TYPE_INT16_100, TYPE_RW, 'kW', ''], \
        [47214, 'Fuse', TYPE_UINT8, TYPE_RW, 'A', 'Size of the fuse that the HP is connected to'], \
        [47261, 'Exhaust Fan speed 4', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47262, 'Exhaust Fan speed 3', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47263, 'Exhaust Fan speed 2', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47264, 'Exhaust Fan speed 1', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47265, 'Exhaust Fan speed normal', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47271, 'Fan return time 4', TYPE_UINT8, TYPE_RW, 'h', 'Time from a changed fan speed until it returns to normal speed'], \
        [47272, 'Fan return time 3', TYPE_UINT8, TYPE_RW, 'h', 'Time from a changed fan speed until it returns to normal speed'], \
        [47273, 'Fan return time 2', TYPE_UINT8, TYPE_RW, 'h', 'Time from a changed fan speed until it returns to normal speed'], \
        [47274, 'Fan return time 1', TYPE_UINT8, TYPE_RW, 'h', 'Time from a changed fan speed until it returns to normal speed'], \
        [47275, 'Filter Reminder period', TYPE_UINT8, TYPE_RW, 'Months', 'Time between the reminder of filter replacement/cleaning.'], \
        [47276, 'Floor drying', TYPE_UINT8, TYPE_RW, '', ' 0=Off 1=On'], \
        [47277, 'Floor drying period 7', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47278, 'Floor drying period 6', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47279, 'Floor drying period 5', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47280, 'Floor drying period 4', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47281, 'Floor drying period 3', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47282, 'Floor drying period 2', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47283, 'Floor drying period 1', TYPE_UINT8, TYPE_RW, 'days', 'Days each period is active'], \
        [47284, 'Floor drying temp 7', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47285, 'Floor drying temp 6', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47286, 'Floor drying temp 5', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47287, 'Floor drying temp 4', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47288, 'Floor drying temp 3', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47289, 'Floor drying temp 2', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47290, 'Floor drying temp 1', TYPE_UINT8, TYPE_RW, 'C', 'Supply temperature each period'], \
        [47291, 'Floor drying timer', TYPE_UINT16, TYPE_R, 'hrs', ''], \
        [47292, 'Trend temperature', TYPE_UINT16, TYPE_RW, 'C', 'Above the set outdoor temperature the addition activation time is limited to give the compressor more time to raise the hot water temperature.'], \
        [47302, 'Climate system 2 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the climate system 2 accessory 0=Off 1=On'], \
        [47303, 'Climate system 3 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the climate system 3 accessory 0=Off 1=On'], \
        [47304, 'Climate system 4 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the climate system 4 accessory 0=Off 1=On'], \
        [47305, 'Climate system 4 mixing valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for extra climate systems'], \
        [47306, 'Climate system 3 mixing valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for extra climate systems'], \
        [47307, 'Climate system 2 mixing valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for extra climate systems'], \
        [47308, 'Climate system 4 shunt wait', TYPE_INT16_10, TYPE_RW, 'secs', 'Wait time between changes of the shunt in extra climate systems'], \
        [47309, 'Climate system 3 shunt wait', TYPE_INT16_10, TYPE_RW, 'secs', 'Wait time between changes of the shunt in extra climate systems'], \
        [47310, 'Climate system 2 shunt wait', TYPE_INT16_10, TYPE_RW, 'secs', 'Wait time between changes of the shunt in extra climate systems'], \
        [47312, 'FLM pump', TYPE_UINT8, TYPE_RW, '', 'Operating mode for the FLM pump 0=Off 1=On'], \
        [47313, 'FLM defrost', TYPE_UINT8, TYPE_RW, 'hrs', 'Minimum time between defrost in FLM'], \
        [47317, 'Shunt controlled add accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the shunt controlled addition accessory 0=Off 1=On'], \
        [47318, 'Shunt controlled add min temp', TYPE_INT8, TYPE_RW, 'C', ''], \
        [47319, 'Shunt controlled add min runtime', TYPE_UINT8, TYPE_RW, 'hrs', ''], \
        [47320, 'Shunt controlled add mixing valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for shunt controlled add.'], \
        [47321, 'Shunt controlled add mixing valve wait', TYPE_INT16, TYPE_RW, 'secs', 'Wait time between changes of the shunt in shunt controlled add.'], \
        [47322, 'Step controlled add accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the step controlled addition accessory 0=Off 1=On'], \
        [47323, 'Step controlled add start DM-2', TYPE_INT16, TYPE_RW, 'DM', ''], \
        [47324, 'Step controlled add diff DM', TYPE_INT16, TYPE_RW, '', 'Difference in DM of each step in the step controlled add.'], \
        [47326, 'Step controlled add mode', TYPE_UINT8, TYPE_RW, '', 'Binary or linear stepping method. 0=Linear 1=Binary'], \
        [47327, 'Ground water pump accessory', TYPE_UINT8, TYPE_RW, '', 'Ground water pump using AXC40 0=Off 1=On'], \
        [47329, 'Cooling 2-pipe accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the 2-pipe cooling accessory 0=Off 1=On'], \
        [47330, 'Cooling 4-pipe accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the 4-pipe cooling accessory 0=Off 1=On'], \
        [47331, 'Min cooling supply temp', TYPE_INT8, TYPE_RW, 'C', ''], \
        [47332, 'Cooling supply temp at 20C-5', TYPE_INT8, TYPE_RW, 'C', ''], \
        [47333, 'Cooling supply temp at 40C-5', TYPE_INT8, TYPE_RW, 'C', ''], \
        [47334, 'Cooling close mixing valves', TYPE_UINT8, TYPE_RW, '', ''], \
        [47335, 'Time betw switch heat/cool', TYPE_INT8, TYPE_RW, 'h', 'Time between switching from heating to cooling or vice versa.'], \
        [47336, 'Heat at room under temp', TYPE_INT8_10, TYPE_RW, 'C', 'This value indicates how many degrees under set room temp heating will be allowed'], \
        [47337, 'Cool at room over temp', TYPE_INT8_10, TYPE_RW, 'C', 'This value indicates how many degrees over set room temp cooling will be allowed'], \
        [47338, 'Cooling mix valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for the cooling valve'], \
        [47339, 'Cooling mix valve step delay', TYPE_INT16, TYPE_RW, '', ''], \
        [47340, 'Cooling with room sensor', TYPE_UINT8_10, TYPE_RW, '', 'Enables use of room sensor together with cooling 0=Off 1=On'], \
        [47341, 'HPAC accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the HPAC accessory'], \
        [47342, 'HPAC DM start passive cooling', TYPE_INT16, TYPE_RW, '', 'Value the degree minutes have to reach for the HPAC to start passive cooling'], \
        [47343, 'HPAC DM start active cooling', TYPE_INT16, TYPE_RW, '', 'Value the degree minutes have to reach for the HPAC to start active cooling'], \
        [47352, 'SMS40 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the SMS40 accessory'], \
        [47365, 'RMU System 1', TYPE_UINT8, TYPE_RW, '', 'Activates the RMU accessory for system 1'], \
        [47366, 'RMU System 2', TYPE_UINT8, TYPE_RW, '', 'Activates the RMU accessory for system 2'], \
        [47367, 'RMU System 3', TYPE_UINT8, TYPE_RW, '', 'Activates the RMU accessory for system 3'], \
        [47368, 'RMU System 4', TYPE_UINT8, TYPE_RW, '', 'Activates the RMU accessory for system 4'], \
        [47370, 'Allow Additive Heating', TYPE_UINT8, TYPE_RW, '', 'Whether to allow additive heating (only valid for operational mode Manual)'], \
        [47371, 'Allow Heating', TYPE_UINT8, TYPE_RW, '', 'Whether to allow heating (only valid for operational mode Manual or Add. heat only)'], \
        [47372, 'Allow Cooling', TYPE_UINT8, TYPE_RW, '', 'Whether to allow cooling (only valid for operational mode Manual or Add. heat only)'], \
        [47378, 'Max diff comp', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47379, 'Max diff add', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47380, 'Low brine out autoreset', TYPE_UINT8, TYPE_RW, '', ' 0=Off 1=On'], \
        [47381, 'Low brine out temp', TYPE_INT16_10, TYPE_RW, 'C', ''], \
        [47382, 'High brine in', TYPE_UINT8, TYPE_RW, '', 'Activates the High brine in temperature alarm. 0=Off 1=On'], \
        [47383, 'High brine in temp', TYPE_INT16_10, TYPE_RW, 'C', 'The brine in temperature that triggers the high brine in temperature alarm (if active).'], \
        [47384, 'Date format', TYPE_UINT8, TYPE_RW, '', ' 1=DD-MM-YY 2=YY-MM-DD'], \
        [47385, 'Time format', TYPE_UINT8, TYPE_RW, '', ' 12=12 hours 24=24 Hours'], \
        [47387, 'HW production', TYPE_UINT8, TYPE_RW, '', 'Activates hot water production where applicable 0=Off 1=On'], \
        [47388, 'Alarm lower room temp', TYPE_UINT8, TYPE_RW, '', 'Lowers the room temperature during red light alarms to notify the occupants of the building that something is the matter 0=Off 1=On'], \
        [47389, 'Alarm lower HW temp', TYPE_UINT8, TYPE_RW, '', 'Lowers the hot water temperature during red light alarms to notify the occupants of the building that something is the matter 0=Off 1=On'], \
        [47391, 'Use room sensor S4', TYPE_UINT8, TYPE_RW, '', 'When activated the system uses the room sensor 0=Off 1=On'], \
        [47392, 'Use room sensor S3', TYPE_UINT8, TYPE_RW, '', 'When activated the system uses the room sensor 0=Off 1=On'], \
        [47393, 'Use room sensor S2', TYPE_UINT8, TYPE_RW, '', 'When activated the system uses the room sensor 0=Off 1=On'], \
        [47394, 'Use room sensor S1', TYPE_UINT8, TYPE_RW, '', 'When activated the system uses the room sensor 0=Off 1=On'], \
        [47395, 'Room sensor setpoint S4', TYPE_INT16_10, TYPE_RW, 'C', 'Sets the room temperature setpoint for the system'], \
        [47396, 'Room sensor setpoint S3', TYPE_INT16_10, TYPE_RW, 'C', 'Sets the room temperature setpoint for the system'], \
        [47397, 'Room sensor setpoint S2', TYPE_INT16_10, TYPE_RW, 'C', 'Sets the room temperature setpoint for the system'], \
        [47398, 'Room sensor setpoint S1', TYPE_INT16_10, TYPE_RW, 'C', 'Sets the room temperature setpoint for the system'], \
        [47399, 'Room sensor factor S4', TYPE_UINT8_10, TYPE_RW, '', 'Setting of how much the difference between set and actual room temperature should affect the supply temperature.'], \
        [47400, 'Room sensor factor S3', TYPE_UINT8_10, TYPE_RW, '', 'Setting of how much the difference between set and actual room temperature should affect the supply temperature.'], \
        [47401, 'Room sensor factor S2', TYPE_UINT8_10, TYPE_RW, '', 'Setting of how much the difference between set and actual room temperature should affect the supply temperature.'], \
        [47402, 'Room sensor factor S1', TYPE_UINT8_10, TYPE_RW, '', 'Setting of how much the difference between set and actual room temperature should affect the supply temperature.'], \
        [47413, 'Speed circpump HW', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47414, 'Speed circpump Heat', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47415, 'Speed circpump Pool', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47416, 'Speed circpump Economy', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47417, 'Speed circpump Cooling', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47418, 'Speed brine pump', TYPE_UINT8, TYPE_RW, '%', ''], \
        [47537, 'Night cooling', TYPE_UINT8, TYPE_RW, '', 'If the fan should have a higher speed when there is a high room temp and a low outdoor temp. 0=Off 1=On'], \
        [47538, 'Start room temp night cooling', TYPE_UINT8, TYPE_RW, 'C', ''], \
        [47539, 'Night Cooling Min diff', TYPE_UINT8, TYPE_RW, 'C', 'Minimum difference between room temp and outdoor temp to start night cooling'], \
        [47540, 'Heat DM diff', TYPE_INT16, TYPE_RW, '', 'Difference in DM between compressor starts in heating mode'], \
        [47543, 'Cooling DM diff', TYPE_INT16, TYPE_RW, '', 'Difference in DM between compressor starts in cooling mode'], \
        [47570, 'Operational mode', TYPE_UINT8, TYPE_RW, '', 'The operational mode of the heat pump 0=Auto 1=Manual 2=Add. heat only'], \
        [47613, 'Max Internal Add', TYPE_UINT8, TYPE_RW, '', 'Maximum allowed steps for the internally connected addition.'], \
        [47614, 'Int connected add mode', TYPE_UINT8, TYPE_RW, '', 'Binary or linear stepping method for the internally connected external addition. 0=Linear 1=Binary'], \
        [48043, 'Holiday - Activated', TYPE_UINT8, TYPE_RW, '', '0=inactive, 10=active'], \
        [48053, 'FLM 2 speed 4', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48054, 'FLM 2 speed 3', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48055, 'FLM 2 speed 2', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48056, 'FLM 2 speed 1', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48057, 'FLM 2 speed normal', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48058, 'FLM 3 speed 4', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48059, 'FLM 3 speed 3', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48060, 'FLM 3 speed 2', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48061, 'FLM 3 speed 1', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48062, 'FLM 3 speed normal', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48063, 'FLM 4 speed 4', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48064, 'FLM 4 speed 3', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48065, 'FLM 4 speed 2', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48066, 'FLM 4 speed 1', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48067, 'FLM 4 speed normal', TYPE_UINT8, TYPE_RW, '%', ''], \
        [48068, 'FLM 4 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the FLM 4 accessory'], \
        [48069, 'FLM 3 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the FLM 3 accessory'], \
        [48070, 'FLM 2 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the FLM 2 accessory'], \
        [48071, 'FLM 1 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the FLM 1 accessory'], \
        [48072, 'DM diff start add', TYPE_INT16, TYPE_RW, '', 'The value below the last compressor step the degree minutes needed to be reached for the pump to start electric addition'], \
        [48073, 'FLM cooling', TYPE_UINT8, TYPE_RW, '', 'FLM cooling activated'], \
        [48074, 'Set point for BT74', TYPE_INT16_10, TYPE_RW, '', 'Set point for change between cooling and heating when using BT74'], \
        [48086, 'Hot water tank type', TYPE_UINT8, TYPE_RW, '', ' 10=VPB 20=VPA'], \
        [48087, 'Pool 2 accessory', TYPE_UINT8, TYPE_RW, '', 'Activate the pool 2 accessory'], \
        [48088, 'Pool 1 accessory', TYPE_UINT8, TYPE_RW, '', 'Activates the pool 1 accessory'], \
        [48089, 'Pool 2 start temp', TYPE_INT16_10, TYPE_RW, 'C', 'The Temperature below which the pool heating should start'], \
        [48090, 'Pool 1 start temp', TYPE_INT16_10, TYPE_RW, 'C', 'The Temperature below which the pool heating should start'], \
        [48091, 'Pool 2 stop temp', TYPE_INT16_10, TYPE_RW, 'C', 'The Temperature at which the pool heating will stop'], \
        [48092, 'Pool 1 stop temp', TYPE_INT16_10, TYPE_RW, 'C', 'The Temperature at which the pool heating will stop'], \
        [48093, 'Pool 2 Activated', TYPE_UINT8, TYPE_RW, '', 'Activates pool heating'], \
        [48094, 'Pool 1 Activated', TYPE_UINT8, TYPE_RW, '', 'Activates pool heating'], \
        [48120, 'HW Comfort', TYPE_UINT8, TYPE_RW, '', 'Activates the HW Comfort Accessory.'], \
        [48132, 'Temporary Lux', TYPE_UINT8, TYPE_RW, '', '0=Off, 1=3h, 2=6h, 3=12h, 4=One time increase.'], \
        [48133, 'Period Pool 2', TYPE_UINT8, TYPE_RW, 'min', ''], \
        [48139, 'DM startdiff add with shunt', TYPE_INT16, TYPE_RW, '', ''], \
        [48140, 'Max pool 2 compr', TYPE_UINT8, TYPE_RW, '', 'Maximum number of compressors that are simultaneously charging the pool'], \
        [48141, 'Max pool 1 compr', TYPE_UINT8, TYPE_RW, '', 'Maximum number of compressors that are simultaneously charging the pool'], \
        [48142, 'Step controlled add start DM', TYPE_INT16, TYPE_RW, '', 'DM diff from last compressor step where the first step of step controlled add. starts'], \
        [48144, 'HW Comfort add during Heat', TYPE_UINT8, TYPE_RW, '', 'Allows the HW Comfort addition to run during heating.'], \
        [48145, 'HW Comfort mixing valve', TYPE_UINT8, TYPE_RW, '', 'Activates the HW Comfort Shunt.'], \
        [48146, 'HW Comfort mixing valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for the HW Comfort Accessory'], \
        [48147, 'HW Comfort mixing valve wait', TYPE_INT16_10, TYPE_RW, 'secs', 'Wait time between changes of the mixing valve for the HW Comfort Accessory'], \
        [48148, 'HW Comfort hotwater temperature', TYPE_INT8_10, TYPE_RW, 'C', 'The desired hotwater temperature'], \
        [48157, 'HW Comfort add', TYPE_UINT8, TYPE_RW, '', 'Activates the HW Comfort Addition.'], \
        [48174, 'Min cooling supply temp S4', TYPE_INT8, TYPE_RW, 'C', 'Minimum allowed supply temperature during cooling'], \
        [48175, 'Min cooling supply temp S3', TYPE_INT8, TYPE_RW, 'C', 'Minimum allowed supply temperature during cooling'], \
        [48176, 'Min cooling supply temp S2', TYPE_INT8, TYPE_RW, 'C', 'Minimum allowed supply temperature during cooling'], \
        [48177, 'Min cooling supply temp S1', TYPE_INT8, TYPE_RW, 'C', 'Minimum allowed supply temperature during cooling'], \
        [48178, 'Cooling supply temp at 20C', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 20C. Used to create cooling curve'], \
        [48179, 'Cooling supply temp at 20C-2', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 20C. Used to create cooling curve'], \
        [48180, 'Cooling supply temp at 20C-3', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 20C. Used to create cooling curve'], \
        [48181, 'Cooling supply temp at 20C-4', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 20C. Used to create cooling curve'], \
        [48182, 'Cooling supply temp at 40C', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 40C. Used to create cooling curve'], \
        [48183, 'Cooling supply temp at 40C-2', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 40C. Used to create cooling curve'], \
        [48184, 'Cooling supply temp at 40C-3', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 40C. Used to create cooling curve'], \
        [48185, 'Cooling supply temp at 40C-4', TYPE_INT8, TYPE_RW, 'C', 'Supply Temperature at 40C. Used to create cooling curve'], \
        [48186, 'Cooling use mix valves', TYPE_UINT8, TYPE_RW, '', 'Close use valves during cooling mode'], \
        [48187, 'Cooling use mix valves-2', TYPE_UINT8, TYPE_RW, '', 'Close use valves during cooling mode'], \
        [48188, 'Cooling use mix valves-3', TYPE_UINT8, TYPE_RW, '', 'Close use valves during cooling mode'], \
        [48189, 'Cooling use mix valves-4', TYPE_UINT8, TYPE_RW, '', 'Close use valves during cooling mode'], \
        [48190, 'Heatdump mix valve delay', TYPE_INT16, TYPE_RW, 's', 'Mixing valve step delay for the heatdump valve'], \
        [48191, 'Heatdump mix valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for the heatdump valve'], \
        [48192, 'Cooldump mix valve delay', TYPE_INT16, TYPE_RW, 's', 'Mixing valve step delay for the cooldump valve for the ACS-system'], \
        [48193, 'Cooldump mix valve amp', TYPE_INT8_10, TYPE_RW, '', 'Mixing valve amplification for the cooldump valve for the ACS-system'], \
        [48194, 'ACS accessory', TYPE_UINT8, TYPE_RW, '', 'Activate the ACS accessory'], \
        [48195, 'ACS heat dump 24h-function', TYPE_UINT8, TYPE_RW, '', ''], \
        [48196, 'ACS run brinepump in wait mode', TYPE_UINT8, TYPE_RW, '', ''], \
        [48197, 'ACS closingtime for cool dump', TYPE_UINT8, TYPE_RW, 's', ''], \
        [48198, 'ACS max cprs in active cooling', TYPE_UINT8, TYPE_RW, '', ''], \
        [48199, 'ACS max brinepumps in passive cooling', TYPE_UINT8, TYPE_RW, '', ''], \
        [48537, 'Night cooling-2', TYPE_UINT8, TYPE_RW, '', '0=OFF, 1=ON'], \
        [48539, 'Night cooling min diff', TYPE_UINT8, TYPE_RW, 'C', ''], \
        [48893, 'F135 Heat pump', TYPE_INT8, TYPE_R, 'C', '0=not activated, 1=activated']      
    ] }
 
###########################################################################

# Classes

class NibeRS485Base(threads.Thread, log.Logging):
    def __init__(self, device):
        threads.Thread.__init__(self)
        log.Logging.__init__(self, 'NibeRS485')

        self.NIBE_DEVICE = device

        self.hasIdentified = False                
        self.data = {}
        self.query_queue = []
        self.query_data = {}
        self.query_sent = []
        self.data_lock = threads.MonitoredLock(120)

    def isQueryCapable(self):
        return False

    def setDevice(self, device):
        self.NIBE_DEVICE = device
                        
    def handleBuffer(self, buff):
        # check that the 4th byte is correct command 0x68
        if len(buff) < 4 or (buff[3] != '\x68' and buff[3] != '\x6A' and buff[3] != '\x6D'):
            self.Debug("Ignoring frame with unknown command in byte 4.")
            return
        
        cmd = buff[3]
        temp = getNibeDataPart(buff)
        temp = fixNibeDataPart(temp)
        
        if cmd == '\x68':       # str(ord(cmd)) = 104.
            if self.data_lock.lock_wait():
                try:                    
                    id = 0
                    l = len(temp)
                    i = 0
                    while i < l:
                        id = (ord(temp[i+1]) << 8) + ord(temp[i])
                        i = i + 2
                        value = (ord(temp[i+1]) << 8) + ord(temp[i])
                        i = i + 2
                        
                        #self.Log("ID: "+str(id))
                        
                        # if data left and next id is 0xFFFF: use that value as most 32bit value most significant bits
                        if i + 4 <= l:
                            if (ord(temp[i+1]) << 8) + ord(temp[i]) == 0xFFFF:
                                i = i + 2
                                value32 = (ord(temp[i+1]) << 8) + ord(temp[i])
                                i = i + 2
                                value = value + (value32 << 16)
        
                        self.data[id] = [time.time(), value]

                        if str(id) != "65535":
                          self.Debug("INFO: Got data for id %d: 0x%04X" % (id, value))
                        while id in self.query_queue:
                            self.query_queue.remove(id)
                finally:
                    self.data_lock.free()
            else:
                self.Log("Cannot get data lock.")
        elif cmd == '\x6A':
            id = 0
            l = len(temp)
            i = 0
            id = (ord(temp[i+1]) << 8) + ord(temp[i])
            i = i + 2
            value = (ord(temp[i+1]) << 8) + ord(temp[i])
            i = i + 2
            if i + 2 <= l:
                value32 = (ord(temp[i+1]) << 8) + ord(temp[i])
                i = i + 2
                value = value + (value32 << 16)

            if self.data_lock.lock_wait():
                try:                                                        
                    if id in self.query_queue:
                        self.query_data[id] = [time.time(), value]
                        self.Log("INFO: Got queried data for id %d: 0x%04X" % (id, value))
                    else:
                        self.Debug("ERROR: Received unqueried or cancelled query data with 0x6A frame.")
                    while id in self.query_queue:
                        self.query_queue.remove(id)
                    self.query_response_time = time.time()
                finally:
                    self.data_lock.free()
            else:
                self.Log("Cannot get data lock.")
        elif cmd == '\x6D':         # str(ord(cmd)) = 109.
            if len(temp) > 3:
                idstr = temp[3:]
                if not self.hasIdentified:
                    self.Log("Received identification: %s" % idstr)
                    self.hasIdentified = True
                else:
                    self.Debug("Received identification: %s" % idstr)
        else:
            self.Log("Unknown character: "+ord(cmd))
            
    def runQueryCommands(self, cmds):
        if self.hasTerminated() and self.isFailed():
            self.data_lock.reset()
            if not self.startModule():
                self.Log("Could not restart module after being failed.")
            else:
                self.Log("Module restarted after being failed.")
        
        if self.isQueryCapable():
            self.flushQueryQueue()
        
        res = {}
        for cmd in cmds:
            (id, type) = self.getNibeDevice(cmd)
            if type == 0:
                res[cmd] = ""
                self.Log("ERROR: Invalid NIBE key: " + cmd)
                continue
    
            temp = self.runQueryId(id)
            if temp != None:
                res[cmd] = convertNibeMessage(type, temp)

        ################################################################################
        # Nibe F470 testi. Luetaan kaikki Niben arvot.
        ################################################################################
        #i = 40004
        #j = 0
        #k = 0
        #while (i > 40003 and i < 50000):
        #    nibeDevice = NIBE_DEVICES['DEFAULT'][j][1]
        #    if (nibeDevice != None):
        #        self.Log("@MEASURE = " + str(nibeDevice) + ":NIBERS485." + str(nibeDevice))
        #    i += 1
        #    j += 1
        ################################################################################

        if self.isQueryCapable():
            qids = []            
            for cmd in cmds:
                if res not in cmd:
                    (id, type) = self.getNibeDevice(cmd)
                    if type != 0:
                        qids.append(id)
            if len(qids) > 0:
                self.queueQueryIds(qids)
                
                # wait for results
                self.waitForQueryQueues()

                for cmd in cmds:
                    if res not in cmd:
                        (id, type) = self.getNibeDevice(cmd)
                        if type != 0:
                            temp = self.runQueryId(id)
                            if temp != None:
                                res[cmd] = convertNibeMessage(type, temp)
                            else:
                                res[cmd] = ""

            self.flushQueryQueue()
        return res

    def getNibeDevice(self, cmd):
        id = 0
        type = 0
        for t in NIBE_DEVICES[self.NIBE_DEVICE]:
            if t[1] == cmd:
                id = t[0]
                type = t[2]
                break
        return (id, type)

    def runQueryId(self, id, haveLocksOutside = False):
        self.Log("INFO: Running nibeBus query with id %d" % id)

        res = None
        if haveLocksOutside or self.data_lock.lock_wait():
            try:
                if self.data in id:
                    temp = self.data[id]
                    if (time.time() - temp[0]) <= DATAVALID:
                        res = temp[1]
                    else:
                        self.Debug("Data expired with id " + repr(id))
                else:
                    self.Debug("DEBUG: No data found with id " + repr(id))
                    
                if res == None and self.isQueryCapable():
                    if self.query_data in id:
                        temp = self.query_data[id]
                        if (time.time() - temp[0]) <= DATAVALID:
                            res = temp[1]
            finally:
                if not haveLocksOutside:    
                    self.data_lock.free()            
        else:
            self.Log("ERROR: Cannot get data lock.")
        return res   

    def startModule(self):
        return False

    def queueQueryIds(self, qids):
        if self.data_lock.lock_wait():
            for qid in qids:
                if not qid in self.query_queue:
                    self.query_queue.append(qid)
            self.data_lock.free()
                
    def waitForQueryQueues(self):
        while self.isRunning():
            isComplete = False
            if self.data_lock.lock_wait():
                try:
                    if len(self.query_queue) <= 0:
                        isComplete = True
                    elif time.time() - self.query_response_time > QUERY_RESPONSE_TIMEOUT:
                        self.Log("ERROR: Communication timed out querying data.")
                        isComplete = True
                finally:
                    self.data_lock.free()
            if isComplete:
                break
            else:
                time.sleep(0.1)
    
    def flushQueryQueue(self):
        if self.data_lock.lock_wait():
            self.query_response_time = time.time()
            self.query_queue = []
            self.query_sent = []
            self.query_data = {}
            self.data_lock.free()
        

class NibeRS485Serial(NibeRS485Base):
    def __init__(self, port, device):
        NibeRS485Base.__init__(self, device)
       
        global serial
        serial = __import__('serial') 
          
        self.SERPORT = port
        self.serio = 0
                    
        self.LOCK = None

    def isQueryCapable(self):
        return True
        
    def setPort(self, port):
        self.SERPORT = port
                
    def run(self):        
        try:              
            while self.isRunning():
                if not self.isOpen():
                    if not self.openPort():
                        self.Log("ERROR: Cannot open serial port.")
                        self.setFail()
                        break
                    
                self.Debug("Flushing serial input buffer.")
                temp = ' '
                while self.isRunning() and len(temp) > 0 and self.serio.inWaiting() > 0:
                    temp = self.serio.read(1)

                res = ''
                prevchar = ''
                while self.isRunning():
                    temp = self.serio.read(1)
                    if len(temp) > 0:
                        res = res + temp
                                        
                        stat = 1
                        while self.isRunning() and stat != 0 and len(res) > 0:                    
                            (stat, flen) = checkNibeMessage(res, prevchar)
                            
                            if stat > 0:
                                rcvdata = res[:flen]
                                prevchar = rcvdata[flen-1]
                                res = res[flen:]
                                if stat == 1:
                                    buff = ''
                                    # if command in frame is '\x69', we can ask for data
                                    if rcvdata[3] == '\x69':
                                        # determine if there is something to query
                                        if self.data_lock.lock_wait():
                                            try:                                        
                                                if len(self.query_queue) > 0:
                                                    # qid is 40004.
                                                    qid = self.query_queue[0]
                                                    while qid in self.query_queue:
                                                        self.query_queue.remove(qid)
                                                    if self.runQueryId(qid, True) == None:
                                                        self.query_queue.append(qid)
                                                        self.query_sent.append(qid)
                                                        buff = buff + generateNibeIdQuery(qid)
                                                        self.Debug("Generating data query for id %d" % qid)
                                            finally:
                                                self.data_lock.free()
                                    buff = buff + '\x06'
                                    self.serio.write(buff)
                                    self.serio.flush()
                                    self.Debug("Received:\n" + log.dumpBuffer(rcvdata))
                                    self.Debug("Sending ACK")
                                    self.handleBuffer(rcvdata)
                                elif stat == 2:
                                    self.serio.write('\x15')
                                    self.serio.flush()
                                    self.Debug("Received:\n" + log.dumpBuffer(rcvdata))
                                    self.Debug("Sending NAK")
                                else:
                                    self.Debug("Received:\n" + log.dumpBuffer(rcvdata))
                                    self.Debug("Ignoring")                                    
                                                                
                            elif stat == -1:
                                prevchar = res[0]
                                res = res[1:]
                                self.Debug("Dropping frame byte 0x%02X" % ord(prevchar))

                self.closePort()
                                
                if self.isRunning():
                    time.sleep(SLEEP_AFTER_FAIL)

        except Exception as e:
            self.Log("Exception: " + e.__str__())
            self.setFail()
        except IOError as ioe:
            self.Log("IOError: " + ioe.__str__())
            self.setFail()

        self.closePort()
       
        self.Log("Nibe Bus serial thread stopped.")
    
                
    def openPort(self):
        if str(NIBE_DEVICES) not in self.NIBE_DEVICE:
            self.Log("ERROR: Invalid NIBE device type: " + self.NIBE_DEVICE)
            return 0

        if not self.LOCK.lock():
            self.Log("ERROR: Unable to aquire lockfile for nibeBus serial port: " + self.LOCK.getName())
            return 0

        try:
            self.serio = serial.Serial(port=self.SERPORT,baudrate=BAUDRATE, \
                                bytesize=serial.EIGHTBITS, \
                                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, \
                                xonxoff=0, rtscts=0, dsrdtr=0, timeout=TIMEOUT, writeTimeout=WRTIMEOUT)
            if not self.serio.isOpen():
                self.serio = 0
                self.LOCK.free()
                return 0 
        except Exception as e:
            print("Exception: ", str(e))
            self.Log("Error opening nibeBus serial port: " + self.SERPORT)
            self.serio = 0
            self.LOCK.free()
            return 0
        
        self.Debug("Opened nibeBus serial port: " + self.SERPORT)
        return 1
        
    def closePort(self):
        if self.serio:
            try:
                self.serio.close()
            except:
                pass
            self.serio = 0
        self.LOCK.free()
        self.Debug("Closed nibeBus serial port: " + self.SERPORT)

    def isOpen(self):
        if self.serio and self.serio.isOpen():
            return 1
        return 0

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


class NibeRS485UDP(NibeRS485Base):
    def __init__(self, listenaddress, port, device):
        NibeRS485Base.__init__(self, device)
       
        self.LISTENADDRESS = listenaddress
        self.UDPPORT = port
        self.QUERYADDRESS = None
        self.QUERYPORT = None
        
    def setListenAddress(self, listenaddress):
        self.LISTENADDRESS = listenaddress
                
    def setUDPPort(self, port):
        self.UDPPORT = port

    def setQueryPeer(self, queryaddress, queryport):
        self.QUERYADDRESS = queryaddress
        self.QUERYPORT = queryport

    def isQueryCapable(self):
        if self.QUERYADDRESS != None and self.QUERYPORT != None:            
            return True
        return False
                        
    def run(self):        
        sock = None
        try:              
            while self.isRunning():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.bind((self.LISTENADDRESS, self.UDPPORT))
                    sock.settimeout(2.0)
                except:
                    try:
                        sock.close()
                    except:
                        pass
                    sock = None
                    self.Log("ERROR: Cannot create UDP socket for address %s port %d." % (self.LISTENADDRESS, self.UDPPORT))
                    self.setFail()
                    break

                self.Debug("Listening for UDP packets in interface %s port %d" % (self.LISTENADDRESS, self.UDPPORT))

                while self.isRunning():
                    if self.isQueryCapable():
                        # determine if there is something to query
                        if self.data_lock.lock_wait():
                            try:                                        
                                if len(self.query_queue) > 0:
                                    tempqueue = list(self.query_queue)                                    
                                    for qid in tempqueue:
                                        if not qid in self.query_sent:
                                            while qid in self.query_queue:
                                                self.query_queue.remove(qid)
                                            if self.runQueryId(qid, True) == None:
                                                self.query_queue.append(qid)
                                                self.query_sent.append(qid)
                                                #self.Debug("Sending data query for id %d to %s port %d" % (qid, self.QUERYADDRESS, self.QUERYPORT))
                                                self.Log("INFO: Sending data query for id %d", qid)
                                                try:
                                                    sock.sendto(generateNibeIdQuery(qid), (self.QUERYADDRESS, self.QUERYPORT))
                                                except Exception as e:
                                                    self.Log("Error sending query UDP packet to %s port %d" % (self.QUERYADDRESS, self.QUERYPORT))
                                                    self.Log("Exception: " + e.__str__())
                            finally:
                                self.data_lock.free()
                    
                    try:
                        (res, peeraddr) = sock.recvfrom(UDP_RECEIVE_BUFFER_SIZE)
                    except socket.timeout as st:
                        continue
                    except Exception as e:
                        self.Log("Socket error. Terminating UDP receiver thread")
                        self.setFail()
                        break
                    
                    self.Debug("Received UDP packet from %s port %d length %d" % (peeraddr[0], peeraddr[1], len(res)))

                    prevchar = ''
                    stat = 1
                    while self.isRunning() and stat != 0 and len(res) > 0:                    
                        (stat, flen) = checkNibeMessage(res, prevchar)
                        if stat > 0:
                            rcvdata = res[:flen]
                            prevchar = rcvdata[flen-1]
                            res = res[flen:]
                            if stat == 1:
                                self.Log("Received and handled:\n" + log.dumpBuffer(rcvdata))
                                self.handleBuffer(rcvdata)
                            elif stat == 2:
                                self.Log("Received with invalid CRC:\n" + log.dumpBuffer(rcvdata))
                            else:
                                self.Log("Received and ignored:\n" + log.dumpBuffer(rcvdata))                                                                                                
                        elif stat == -1:
                            prevchar = res[0]
                            res = res[1:]
                            self.Log("INFO: Dropping frame byte 0x%02X" % ord(prevchar))
                        elif stat == 0:
                            # we cannot get more than there is in the UDP packet, discard the rest
                            self.Log("ERROR: Discarding %d bytes of data. Incomplete frame." % len(res))
                            res = ''
                        else:
                            self.Log("WARN: Dropping frame byte 0x%02X" % ord(res[0]))
                sock.close()
                sock = None
                                
                if self.isRunning():
                    time.sleep(SLEEP_AFTER_FAIL)

        except Exception as e:
            self.Log("Exception: " + e.__str__())
            self.setFail()
        except IOError as ioe:
            self.Log("IOError: " + ioe.__str__())
            self.setFail()

        if sock != None:
            try:
                sock.close()
            except:
                pass
            sock = None
       
        self.Log("Nibe Bus UDP receiver thread stopped.")
            
    def startModule(self):            
        self.start()
        return 1

    
        
###########################################################################

# Functions

# returns (stat, datalen)
#   -1 = error
#   0 = ok, but not ready
#   1 = ok, data lenght in datalen
#   2 = not ok, crc fail, data lenght in datalen
#   3 = ok/not ok, frame not for this device
def checkNibeMessage(data, previousChar = ''):
    l = len(data)
    dl = 0
    if l <= 0:
        return (0, 0)

    # if the previous character is 5C, must abandon one
    # back-to-back 5C can only be in the data part,
    # this is also why CRC is never 5C
    if l >= 1 and previousChar == '\x5C':
        return (-1, 0)

    # first byte is '\x5C'
    if l >= 1 and data[0] != '\x5C':
        return (-1, 0)

    # second byte is '\x00'
    if l >= 2 and data[1] != '\x00':
        return (-1, 0)
    
    # fifth byte is data part len
    if l >= 5:
        dl = ord(data[4])
    else:
        return (0, 0)
    
    # in case the frame length was not ok, find possible start of a new frame in
    # the data part
    if l >= 5+2:
        i = 5
        while i < l-1:
            if data[i] == '\x5C' and data[i+1] == '\x00' and data[i-1] != '\x5C':
                return (-1, 0)
            i = i + 1
    
    # if 1 byte crc and all data have not yet arrived
    if l < dl + 6:
        return (0, 0)
    
    # check third byte address
    # third byte should be '\x20'
    if data[2] != '\x20':
        return (3, dl + 6)

    # check CRC
    crc = 0
    for i in range(2, dl + 5):
        crc = crc ^ ord(data[i])
    datacrc = ord(data[dl + 5])    
    
    if crc == 0x5C:
        if datacrc != 0xC5:
            return (2, dl + 6)
    elif crc != datacrc:
        return (2, dl + 6)

    return (1, dl + 6)

def calculateCRC(data):
    crc = 0
    for i in range(len(data)):
        crc = crc ^ ord(data[i])
    
    if crc == 0x5C:
        crc = 0xC5

    return chr(crc)
    
def getNibeDataPart(data):
    dl = ord(data[4])
    return data[5:5+dl]
    
def fixNibeDataPart(data):
    temp = ''
    # remove back_to_back 0x5C characters
    i = 0
    l = len(data)
    while i < l:
        temp = temp + data[i]
        if data[i] == '\x5C' and i+1 < l and data[i+1] == '\x5C':
            i = i + 1
        i = i + 1
    
    return temp

def generateNibeIdQuery(qid):
    ## query id LSB first
    tdata = chr(qid & 0x00FF)
    tdata = tdata + chr((qid >> 8) & 0x00FF)
    tdata = unfixNibeDataPart(tdata)

    buff = '\xC0\x69'
    buff = buff + chr(len(tdata))
    buff = buff + tdata
    buff = buff + calculateCRC(buff)

    return buff
    
def unfixNibeDataPart(data):
    temp = ''
    # escape 0x5C characters with 0x5C
    i = 0
    l = len(data)
    while i < l:
        temp = temp + data[i]
        if data[i] == '\x5C':
            temp = temp + '\x5C'
        i = i + 1
    
    return temp
    
    
def convertNibeMessage(type, value):
    if type == TYPE_INT8:
        temp = binary.twosComplementToInt(value & 0x00FF, 8)
        temp = "%d" % temp
        return temp
    elif type == TYPE_INT16:
        temp = binary.twosComplementToInt(value, 16)
        temp = "%d" % temp
        return temp
    elif type == TYPE_INT32:
        temp = binary.twosComplementToInt(value, 32)
        temp = "%d" % temp
        return temp
    elif type == TYPE_UINT8:
        temp = "%d" % (value & 0x00FF)
        return temp
    elif type == TYPE_UINT16:
        temp = "%d" % value
        return temp
    elif type == TYPE_UINT32:
        temp = "%d" % value
        return temp
    elif type == TYPE_INT16_10:
        temp = binary.twosComplementToInt(value, 16)
        temp = "%.1f" % (temp / 10.0)
        return temp
    elif type == TYPE_INT8_10:
        temp = binary.twosComplementToInt(value & 0x00FF, 8)
        temp = "%.1f" % (temp / 10.0)
        return temp
    elif type == TYPE_INT32_10:
        temp = binary.twosComplementToInt(value, 32)
        temp = "%.1f" % (temp / 10.0)
        return temp
    elif type == TYPE_UINT32_10:
        temp = "%.1f" % (value / 10.0)
        return temp
    elif type == TYPE_UINT8_10:
        temp = "%.1f" % ((value & 0x00FF) / 10.0)
        return temp
    elif type == TYPE_INT16_100:
        temp = binary.twosComplementToInt(value, 16)
        temp = "%.2f" % (temp / 100.0)
        return temp
    elif type == TYPE_UINT16_10:
        temp = "%.1f" % (value / 10.0)
        return temp

    return ""

