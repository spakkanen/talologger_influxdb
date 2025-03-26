#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            persistState.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.1b
#
# Date:            22.04.2020
#
# Description:     Class to implement module state persisting in 
#                  taloLogger.
#                  
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
#
# Version history: ** 03.02.2016 v0.1a (Olli Lammi) **
#                  First version. 
#
#                  ** 22.04.2020 v0.1b (Olli Lammi) **
#                  Added functions to persist measurement state as
#                  JSON.
#
###########################################################################

# Imports

import sys, os, string
import _pickle as cPickle
import json, tempfile

from modules.core import log

###########################################################################

# Classes

class StatePersistCapable(object):
    PSTATE_DIR = None
    
    def __init__(self, logging = None, mname = ''):
        self.modulename = mname
        self.log = logging

    def getModuleName(self):
        return self.modulename
    
    def setModuleName(self, mname):
        self.modulename = mname

    def getPStateFilename(self):
        if StatePersistCapable.PSTATE_DIR and len(StatePersistCapable.PSTATE_DIR) > 0:
            return StatePersistCapable.PSTATE_DIR + self.modulename + '.state'
        return None

    @staticmethod
    def setPersistentStateDirectory(dir):
        StatePersistCapable.PSTATE_DIR = dir
        
    # loads and returns persistent state for this module 
    # returns persisted state object, None if persistence is not
    # enabled or no state for this modulde exists
    def loadState(self):
        fname = self.getPStateFilename()
        if fname != None:
            if not os.path.isfile(fname):
                self.log.Log("WARN: Module state does not exist: " + fname)
                return None
            try:
                if self.log:
                    self.log.Debug("Loading module state from: " + fname)
                infile = open(fname, 'r')
                stateObject = cPickle.load(infile)
                infile.close()                 
                if self.log:
                    self.log.Log("Module state loaded.")
                return stateObject
            except Exception as e:
                print("Exception: ", e.__str__())
                if self.log:
                    self.log.Log("ERROR: Error loading module state from " + fname)
                return None 
        return None
    
    # saves the given stateObject to persistent state storage for this 
    # module 
    # returns values:
    #  -1 = persistence is enabled, error saving state
    #   0 = persistence is not enabled
    #   1 = state saved
    def saveState(self, stateObject):
        fname = self.getPStateFilename()
        if fname != None:
            try:
                if self.log:
                    self.log.Debug("Saving module state to  " + fname)
                outfile = open(fname, 'w')
                cPickle.dump(stateObject, outfile)
                outfile.close()
                if self.log:                 
                    self.log.Debug("Module state saved.")
                return 1
            except:
                if self.log:
                    self.log.Log("Error saving module state to " + fname)
                return -1
        return 0

###########################################################################

# Functions

def saveCycleState(state):
    (f, fname) = tempfile.mkstemp()
    of = os.fdopen(f, 'w')
    json.dump(state, of)
    of.close()
    return fname

def loadCycleState(fname, state):
    f = open(fname, 'r')
    temp = json.load(f)
    f.close()
    if temp:
        for key in temp:
            skey = key
            sval = temp[key]
            if isinstance(skey, str):
                skey = skey.encode('utf-8')
            if isinstance(sval, str):
                sval = sval.encode('utf-8')
            elif isinstance(sval, float) or isinstance(sval, int):
                sval = str(sval)
            state[skey] = sval
