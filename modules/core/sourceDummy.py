#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            sourceDummy.py
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
# Description:     TaloLogger Dummy data source for testing.
#                  
# Version history: ** 09.01.2013 v1.5a (Olli Lammi) **
#                  Added to taloLogger. 
#
#                  ** 14.01.2015 v1.6e (Olli Lammi) **
#                  Added module typename. 
#
###########################################################################

# Imports

import os, string, time, math

from modules.core import configuration
from modules.core import dataSource


###########################################################################

# Classes

class DummyConf(configuration.Configurable, dataSource.DataSource):
    def __init__(self, modname):
        configuration.Configurable.__init__(self)
        self.setModuleName(modname)
        dataSource.DataSource.__init__(self)
        
    def getServiceName(self):
        return self.getModuleName()

    def handleConfiguration(self, conf): 
        return (1, '')
        
    def initConfiguration(self):
        return (1, '')

    def runDataSourceQueryCommandImpl(self, cmds):
        dataresult = {}
    
        for cmd in cmds:
            val = 5.0 + 10.0 * math.sin((time.time() % 7200.0) / 3600.0 * math.pi) 
            dataresult[cmd] = "%.1f" % (val, )
                
        return dataresult

    @staticmethod
    def getModuleTypeName():
        return 'DUMMY'

    @staticmethod
    def getAllowedConfigurationKeys():
        return ([], [])
