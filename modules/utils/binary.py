#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            binary.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.0b
#
# Date:            16.11.2010
#
# Description:     Library to implement some binary operations.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
# Version history: ** 29.04.2010 v1.0a (Olli Lammi) **
#                  First version. Imported code from other classes. 
#
#                  ** 16.11.2010 v1.0b (Olli Lammi) **
#                  Rego related binary functions. 
#
###########################################################################

# Imports



###########################################################################

# Classes


###########################################################################

# Functions

def twosComplementToInt(value, bits):
    if (int(value) & (1 << (bits - 1))) == 0:
        return value
    # complement
    temp = 0
    for i in range(0, bits):
        if (int(value-1) & (1 << i)) == 0:
            temp = temp | (1 << i)
    return -temp


def intToTwosComplement(value, bits):
    if value >= 0:
        return value
    
    temp = int(-value)
    res = 0
    hasone = 0
    for i in range(0, bits):
        if hasone and temp & (1 << i) == 0:
            res = res | (1 << i)
        elif not hasone and temp & (1 << i) != 0:
            hasone = 1
            res = res | (1 << i)
    return res


def int16ToSevenBitBuff(value):
    res = []
    temp = intToTwosComplement(value, 16)
    res.append((temp & 0xC000) >> 14)
    res.append((temp & 0x3F80) >> 7)
    res.append((temp & 0x007F))
    return res


def sevenBitBuffToInt16(buff):
    temp = 0
    temp = temp | (ord(buff[0]) << 14)
    temp = temp | (ord(buff[1]) << 7)
    temp = temp | ord(buff[2])
    return twosComplementToInt(temp, 16)