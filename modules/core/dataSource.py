#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            dataSource.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.2c
#
# Date:            14.05.2014
#
# Description:     Abstract base class for services that can read data 
#                  values from appliances. 
#                 
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
# Version history: ** 11.10.2011 v0.1a (Olli Lammi) **
#                  Moved from main application class. 
#
#                  ** 13.02.2012 v0.2a (Olli Lammi) **
#                  Threaded interface. Multisupport.
#
#                  ** 19.01.2013 v0.2b (Olli Lammi) **
#                  Corrected missing time import causing exception
#                  in thread execution during possible error condition.
#
#                  ** 14.05.2014 v0.2c (Olli Lammi) **
#                  Added queue timestamp to interfaces.
#
###########################################################################

# Imports

import time
from modules.core import threads

###########################################################################

# Constants

DATASOURCE_DEFAULT_TIMEOUT = 120


###########################################################################

# Classes

class DataSourceThread(threads.Thread):
    def __init__(self, source):
        threads.Thread.__init__(self)
        self.running = 0
        self.datasource = source
        self.moduleid = ''
        self.queuets = 0
        self.listener = None
        self.commands = None

    def startQuery(self, listener, moduleid, cmds, tstamp):
        if self.running != 0:
            return False
        self.listener = listener
        self.moduleid = moduleid
        self.commands = cmds
        self.queuets = tstamp
        return (self.start() == 1)

    def getMissingKeys(self, data):
        mkeys = []
        for cmd in self.commands:
            if not data.has_key(cmd):
                mkeys.append(cmd)
        return mkeys 

    def run(self):
        self.running = 1
        
        try:
            if self.datasource != None and self.listener != None and len(self.commands) > 0:
                retries = 3
                tempdata = {}
                while retries > 0:
                    mkeys = self.getMissingKeys(tempdata)
                    if len(mkeys) > 0:
                        if retries < 3:
                            time.sleep(0.2)
                        try:
                            qdata = self.datasource.runDataSourceQueryCommand(mkeys)
                            tempdata.update(qdata)
                        except:
                            pass
                        retries = retries - 1
                    else:
                        break
                    
                mkeys = self.getMissingKeys(tempdata)    
                for key in mkeys:
                    tempdata[key] = ''
                try:
                    self.listener.dataReceived(self.moduleid, tempdata, self.queuets)
                except:
                    pass
    
            self.moduleid = ''
            self.queuets = 0
            self.listener = None
            self.commands = None
        finally:
            self.running = 0

class DataSourceListener(object):
    def dataReceived(self, moduleid, data, queuets): pass

class DataSource(object):
    def __init__(self):
        self.dsTimeout = DATASOURCE_DEFAULT_TIMEOUT
        self.dataSourceThread = DataSourceThread(self)
    
    def getServiceName(self): pass

    def runDataSourceQueryCommand(self, cmds):
        return self.runDataSourceQueryCommandImpl(cmds)

    def runDataSourceQueryCommandAsync(self, listener, moduleid, cmds, queuets):
        return self.dataSourceThread.startQuery(listener, moduleid, cmds, queuets) 

    def runDataSourceQueryCommandImpl(self, cmds): pass
    
    def runDataSourceQueryMultiWrapper(self, cmds):
        dataresult = {}
        for key in cmds:
            try:
                dataresult[key] = self.runQueryCommand(key)
            except:
                dataresult[key] = ""

        return dataresult
    