#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            lockfile.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.0c
#
# Date:            06.01.2013
#
# Description:     Library to implement a lock file in Python.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
# Version history: ** 02.03.2009 v1.0a (Olli Lammi) **
#                  First version. 
#
#                  ** 22.08.2010 v1.0b (Olli Lammi) **
#                  Tries to remove the lockfile if the lock is older
#                  than 120 seconds. 
#
#                  ** 06.01.2013 v1.0c (Olli Lammi) **
#                  Lockfile module now determines the lock file location
#                  and name according to the given resource location. 
#
###########################################################################

# Imports

import sys, os, string, time
import tempfile, os.path

###########################################################################

# Constants

LOCK_LIFETIME = 120 

LOCKFILENAME_PREFIX = tempfile.gettempdir() + os.sep + 'lock_'

###########################################################################

# Classes

class LockFile(object):
    def __init__(self, fname):
        self.lockfilename = LOCKFILENAME_PREFIX + string.replace(os.path.realpath(fname), os.sep, '_')
        self.ihaveit = 0
        self.lockfile = None

    def lock(self):
        if self.ihaveit:
            return 1
        count = 0
        while not self.ihaveit:
            try:
                self.lockfile = os.open(self.lockfilename, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except:
                self.lockfile = None
            if self.lockfile == None:
                count = count + 1                 
                if count > 10:
                    return 0
                try:
                    if count > 1 and (time.time() - os.stat(self.lockfilename).st_mtime) > LOCK_LIFETIME:
                        os.remove(self.lockfilename)
                except:
                    pass
                time.sleep(1)
            else:
                self.ihaveit = 1
                
        return self.ihaveit

    def free(self):
        if not self.ihaveit:
            return 0
        if self.lockfile != None:
            os.close(self.lockfile)
            self.lockfile = None
        try:
            os.remove(self.lockfilename)
        except:
            pass
        self.ihaveit = 0
        return 1

    def getName(self):
        return self.lockfilename
