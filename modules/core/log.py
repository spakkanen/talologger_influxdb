#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            log.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.9f
#
# Date:            04.05.2011
#
# Description:     File and console logging for taloLogger.py application log.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.4)
# 
# Version history: ** 24.02.2009 v0.9a (Olli Lammi) **
#                  First beta version for testers. 
#
#                  ** 25.02.2009 v0.9c (Olli Lammi) **
#                  Changed logging classes.
#
#                  ** 25.02.2009 v0.9c (Olli Lammi) **
#                  Added verbose/debug logging.
#
#                  ** 10.02.2011 v0.9d (Olli Lammi) **
#                  Minor interface changes for multimodule conf.
#
#                  ** 04.05.2011 v0.9f (Olli Lammi) **
#                  Added dumpBuffer function for debug purposes.
#
###########################################################################

# Imports

import sys, os 
import string, time 

from modules.core import configuration


###########################################################################

# Constants

DEFAULT_LOGFILE = "taloLogger.log"

###########################################################################

# Classes

class Logging(object):
    LOG = None
    
    def __init__(self, id):
        self.ID = id
           
    def Log(self, message):
        if (Logging.LOG != None):
            Logging.LOG.log(self.ID + ': ' + message)

    def Debug(self, message):
        if (Logging.LOG != None):
            Logging.LOG.debug(self.ID + ': ' + message)

    def getID(self):
        return self.ID
    
    def setID(self, nid):
        self.ID = nid

    @staticmethod
    def setLogger(logger):
        Logging.LOG = logger

class Logger(configuration.Configurable):
  def __init__(self, conf, id=''):
      configuration.Configurable.__init__(self)
      self.CONSOLE = conf.isTrue('CONSOLE_LOGGING')
      self.DEBUG = conf.isTrue('VERBOSE_LOGGING')
      self.FNAME = conf.getValue('LOGFILE', DEFAULT_LOGFILE)
      self.ID = id
 
  def log(self, msg):
      tstr = time.strftime("%d.%m.%Y %H:%M:%S")
      try:
          temps = tstr + ": "
          if len(self.ID) > 0:
              temps = temps + self.ID + ': '
          if self.CONSOLE:
              print(temps + msg)
          else:
              ofile = open(self.FNAME, 'a')
              ofile.write(temps + msg + "\n")
              ofile.close()
      except:
          print("Error writing log.")
          return

  def debug(self, msg):
      if self.DEBUG:
          self.log(msg)

  @staticmethod
  def getAllowedConfigurationKeys():
      return (['CONSOLE_LOGGING', 'VERBOSE_LOGGING', 'LOGFILE'], [])


###########################################################################

# Functions

def dumpBuffer(buff):
    temp = ''
    i = 0
    while i < len(buff):
        temp = temp + " %02X" %(buff[i],)
        i = i + 1
        if i % 16 == 0 and i < len(buff):
            temp = temp + '\n'
    return temp + '\n'

