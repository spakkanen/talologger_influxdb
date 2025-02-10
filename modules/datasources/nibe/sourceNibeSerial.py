#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            sourceNibeSerial.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.4j
#
# Date:            06.01.2013
#
# Description:     TaloLogger configuration wrapper for NibeSerial library.
#                  
# Version history: ** 11.10.2011 v1.4e (Olli Lammi) **
#                  Moved from main taloLogger application module. 
#
#                  ** 13.02.2012 v1.4i (Olli Lammi) **
#                  Multisupport
#
#                  ** 06.01.2013 v1.4j (Olli Lammi) **
#                  Changed to support controlled Thread.
#
###########################################################################

# Imports

from modules.core import configuration
from modules.core import dataSource

import nibeSerial


###########################################################################

# Classes

class NibeSerialConf(nibeSerial.NibeSerial, configuration.Configurable, dataSource.DataSource):
    def __init__(self, modname):
        configuration.Configurable.__init__(self)
        self.setModuleName(modname)
        nibeSerial.NibeSerial.__init__(self, None, None)
        dataSource.DataSource.__init__(self)
        self.setID(modname)

    def getServiceName(self):
        return self.getModuleName()

    def runDataSourceQueryCommandImpl(self, cmds):
        return self.runDataSourceQueryMultiWrapper(cmds)
    
    def handleConfiguration(self, conf):
        self.port = conf.getValue('SERIAL_PORT', '', self.getModuleName())
        self.device = conf.getValue('DEVICE', '', self.getModuleName())
        return (1, '')
        
    def initConfiguration(self):
        if len(self.port) <= 0:
            return (-1, 'Missing Nibe serial port path.')
        if len(self.device) <= 0:
            return (-1, 'Missing Nibe device name.')

        self.setPort(self.port)
        self.setDevice(self.device)

        if not self.startModule():
            return (0, 'Error accessing Nibe controller.')
        else:
            self.Log('Started Nibe serial module.')
        return (1, '')

    def releaseConfiguration(self):
        self.terminate()
        if not self.hasTerminated():
            self.wait_sleeping()
        return (1, '')

    @staticmethod
    def getModuleTypeName():
        return 'NIBE'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['DEVICE', 'SERIAL_PORT'], [])

