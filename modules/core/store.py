#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            store.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.8b
#
# Date:            23.01.2024
#
# Description:     Abstract base class for services that can store logged 
#                  data values. 
#                 
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
# Version history: ** 24.02.2009 v0.9a (Olli Lammi) **
#                  First beta version for testers. 
#
#                  ** 26.10.2011 v1.4f (Olli Lammi) **
#                  Added filtering features.
#
#                  ** 07.01.2013 v1.5a (Olli Lammi) **
#                  Added timeval parameter to logging. Added support for
#                  queuing data if storing fails.
#
#                  ** 15.05.2014 v1.6b (Olli Lammi) **
#                  Added clearStagedData-method. Changed added log.Logging
#                  to this class (removed from the implementations). 
#                  Handling and discarding invalid data. 
#
#                  ** 14.01.2015 v1.6e (Olli Lammi) **
#                  Module structure changed.
#
#                  ** 30.01.2017 v1.7j (Olli Lammi) **
#                  Added data point renaming for a data store to filter.
#
#                  ** 23.01.2024 v1.8b (Olli Lammi) **
#                  Store filter order overrides result order.
#
###########################################################################

# Imports

import string

from modules.core import threads
from modules.core import configuration
from modules.core import log

###########################################################################

# Classes

class Store(configuration.Configurable, log.Logging):
    def __init__(self, modname):
        configuration.Configurable.__init__(self)
        log.Logging.__init__(self, modname)
        self.setModuleName(modname)
        self.storefilters = None
        self.storefilterkeys = None
        self.staged_data = []
        self.stage_lock = threads.Lock()

    def insertData(self, timeval, values):
        self.Log("Insert data values: "+str(values))
            
        if self.storefilters != None:
            temp = []
            tempdata = {}
            for value in values:
                tempdata[value[0]] = value[1]
            for posname in self.storefilterkeys:
                filter = self.storefilters[posname]
                temp.append([filter, tempdata[posname]])
            self.stageData(timeval, temp)
        else:
            self.stageData(timeval, values)
        self.handleStagedData()

    def stageData(self, timeval, values):
        if self.stage_lock.lock_wait():
            self.staged_data.append([timeval, values])
            self.stage_lock.free()

    def handleStagedData(self):
        if self.stage_lock.lock_wait():
            try:
                discarded = []
                inserted = 0
                while len(self.staged_data) > 0:
                    item = self.staged_data[0]
                    self.staged_data.pop(0)
                    if self.insertDataImpl(item[0], item[1]):
                        inserted = 1
                    else:
                        discarded.append(item)
                if inserted:
                    # something of the data went in, try discarded
                    # items once more, log if not able to insert
                    for item in discarded:
                        if not self.insertDataImpl(item[0], item[1]):
                            self.logDiscardedData(item)
                else:
                    # re-add discarded to stage
                    self.staged_data = discarded
            except:
                pass
            self.stage_lock.free()

    def clearStagedData(self):
        if self.stage_lock.lock_wait():
            while len(self.staged_data) > 0:
                item = self.staged_data[0]
                try:
                    self.logDiscardedData(item)
                except:
                    pass
                self.staged_data.pop(0)
            self.stage_lock.free()

    def logDiscardedData(self, data):
        if data == None or len(data) <= 0:
            return

        msg = "timestamp:\"%d\"" % data[0]
        for item in data[1]:
            msg = msg + ", %s:\"%s\"" % (item[0], item[1])

        self.Log("Discarding staged data: " + msg)

    def initStoreFilters(self, conf):
        self.storefilters = None
        self.storefilterkeys = None
        temp = conf.getValue('STOREFILTER', [])
        if len(temp) > 0:
            tempfilters = {}
            tempfilterkeys = []
            for filter in temp:
                mname = None
                posname = None
                storepos = None
                if filter.find(':') < 0:
                    return False
                tempnames = filter.split(':')
                if len(tempnames) == 2:
                    mname = tempnames[0].strip()
                    posname = tempnames[1].strip()
                    storepos = posname
                elif len(tempnames) == 3:
                    mname = tempnames[0].strip()
                    posname = tempnames[1].strip()
                    storepos = tempnames[2].strip()
                else:
                    return False
                if mname == self.getModuleName() and posname not in tempfilterkeys:
                    tempfilters[posname] = storepos
                    tempfilterkeys.append(posname)
            if len(tempfilters) > 0:
                self.storefilters = tempfilters
                self.storefilterkeys = tempfilterkeys
        return True

    def checkStoreFilters(self, measurepositions):
        if self.storefilters != None:
            for filter in self.storefilterkeys:
                if filter not in measurepositions:
                    return (0, "Data store module %s has invalid store filter %s." % (self.getModuleName(), filter))
        return (1, '')

    # returns 0 if inserting failed, 1 with success
    def insertDataImpl(self, timeval, values): pass
    
