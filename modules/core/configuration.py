#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            configuration.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.7b
#
# Date:            13.02.2015
#
# Description:     Configuration file class for taloLogger.py
#                  
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
#
# Version history: ** 24.02.2009 v0.9a (Olli Lammi) **
#                  First beta version for testers. 
#
#                  ** 24.02.2009 v0.9a (Olli Lammi) **
#                  Added methods for checking the configuration. 
#
#                  ** 25.01.2011 v0.1b (Olli Lammi) **
#                  Added methods for releasing the configuration. 
#
#                  ** 10.02.2011 v0.1c (Olli Lammi) **
#                  Interface changes for multiple module support. 
#
#                  ** 14.01.2015 v1.6e (Olli Lammi) **
#                  Added module typename. 
#
#                  ** 13.02.2015 v1.7b (Olli Lammi) **
#                  Added command support to configurables. 
#
###########################################################################

# Imports

import sys, os, string


###########################################################################

# Classes

class Configurable(object):
    def __init__(self):
        self.modulename = ''

    def getModuleName(self):
        return self.modulename
    
    def setModuleName(self, mname):
        self.modulename = mname

    # returns module type name used to refer to this type of
    # configurable in the configuration file
    @staticmethod
    def getModuleTypeName(): pass
        
    # returns a tuple with two lists both containing the
    # allowed normal and listed configuration keys that this
    # configurable allows
    @staticmethod
    def getAllowedConfigurationKeys(): pass

    # reads configuration conf and configurest itself
    # returns a tuple (stat, msg) where msg is possible
    # error message and stat is (1 = ok, 0 = error)
    def handleConfiguration(self, conf): pass

    # initializes the configurable with the given config ie. runs appropriate tests
    # to check if the configuration is semantically valid and all configured resources
    # work accordingly.
    # returns a tuple (stat, msg) where msg is possible error message
    # and stat is (1 = ok, 0 = error, -1 = fatal error)
    def initConfiguration(self):
        return (1, '')

    # releases/closes the configurable with the given config ie. frees resources
    # allocated by the module.
    # returns a tuple (stat, msg) where msg is possible error message
    # and stat is (1 = ok, 0 = error)
    def releaseConfiguration(self):
        return (1, '')

    # sends this configurable a command with parameter string.
    # returns a tuple (stat, msg) where msg is possible error message
    # and stat is (1 = ok, 0 = error, -1 = unknown command)
    def executeCommand(self, cmd, paramstr):
        return (-1, 'Commands are not supported for this module.')


class Configuration(object):
    def __init__(self):
        self.data = {}
        self.allowedkeys = []
        self.allowedlistkeys = []
        
    def addAllowedKeys(self, keys):
        for k in keys:
            self.allowedkeys.append(k)

    def addAllowedListKeys(self, keys):
        for k in keys:
            self.allowedlistkeys.append(k)

    def addConfigurable(self, cfable):
        (norm, lst) = cfable.getAllowedConfigurationKeys()
        self.addAllowedKeys(norm)
        self.addAllowedListKeys(lst)

    # load configuration file: tuple stat, msg: 0 = open/read error, -1 = invalid file, 1 = ok
    def loadFile(self, fname):
        try:
            inf = open(fname, 'r')
            lines = inf.readlines()
            inf.close()
        except:
            return (0, '')

        for line in lines:
            line = line.split('\n')[0].strip()
            if len(line) <= 0 or line[0] == '#':
                continue

            if line[0] == '@':
                line = line[1:]
                lineparts = line.split('=', 1)
                if len(lineparts) > 1:
                    module = ''
                    key = lineparts[0].strip()
                    if key.find(':') >= 0:
                        [module, key] = key.split(':', 1)
                        module = module.strip()
                        key = key.strip()
                    elif not key in self.allowedlistkeys:
                        return (-1, "Invalid configuration key: @" + key)
                    value = lineparts[1].strip()
                    if module not in self.data:
                        self.data[module] = {}
                    if key not in self.data[module]:
                        self.data[module][key] = [] 
                    self.data[module][key].append(value)
                else:
                    return (-1, "Invalid configuration line: @" + line)
            else:
                lineparts = line.split('=', 1)
                if len(lineparts) > 1:
                    module = ''
                    key = lineparts[0].strip()
                    if key.find(':') >= 0:
                        [module, key] = key.split(':', 1)
                        module = module.strip()
                        key = key.strip()
                    elif not key in self.allowedkeys:
                        return (-1, "Invalid configuration key: " + key)
                    value = lineparts[1].strip()
                    if module not in self.data:
                        self.data[module] = {}
                    self.data[module][key] = value
                else:
                    return (-1, "Invalid configuration line: " + line)

        return (1, '')

    def getData(self):
        return self.data

    def hasKey(self, key, module = ''):
        if not self.hasModule(module):
            return 0
        return key in self.data[module]

    def getValue(self, key, default, module = ''):
        if self.hasKey(key, module):
            return self.data[module][key]
        else:
            return default

    def setValue(self, key, value, module = ''):
        if not self.hasModule(module):
            self.data[module] = {}
        self.data[module][key] = value

    def isTrue(self, key, module = ''):
        if not self.hasKey(key, module):
            return 0
        if self.data[module][key].lower() == 'true':
            return 1
        return 0
    
    def hasModule(self, module):
        return module in self.data
    
    def checkConfigurationKeys(self, cfable):
        if not self.hasModule(cfable.getModuleName()):
            (cnorm, clst) = cfable.getAllowedConfigurationKeys()
            if len(cnorm)+len(clst) > 0: 
                return (0, 'Configurable module has no configuration directives present in the configuration.')
            return (1, '')
        modconf = self.data[cfable.getModuleName()]
        (cnorm, clst) = cfable.getAllowedConfigurationKeys()
        for key in modconf.keys():
            if type(modconf[key]) is list:
                if not key in clst:
                    return (-1, "@%s:%s" % (cfable.getModuleName(), key))
            else:
                if not key in cnorm:
                    print(self.data)
                    return (-1, "%s:%s" % (cfable.getModuleName(), key))
        return (1, '')
