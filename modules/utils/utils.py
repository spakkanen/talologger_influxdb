#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            utils.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.2b
#
# Date:            16.02.2015
#
# Description:     taloLogger utils
#                  
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
#
# Version history: ** 20.01.2013 v0.1a (Olli Lammi) **
#                  First version. 
#
#                  ** 02.12.2014 v0.2a (Olli Lammi) **
#                  Non-unix support.
#
#                  ** 16.02.2015 v0.2b (Olli Lammi) **
#                  Fix to failing command execution (intermittent).
#
###########################################################################

# Imports
 
import subprocess, os
import time

from modules.core import threads

if os.name == 'posix':
    import fcntl, select

###########################################################################

# Constants


###########################################################################

# Classes

if os.name == 'posix':
    
    # implementation for Unix systems
    
    class TimeoutableFileReader(object):
        def __init__(self, file, timeout):
            self.filename = file
            self.timeout = timeout
    
        def read(self):
            data = ''
            status = 0
            
            closestatus = 0
            
            fd = -1
            try:
                fd = os.open(self.filename, os.O_RDONLY | os.O_NONBLOCK)
            except:
                return (-1, '')
            if fd < 0:
                return (-1, '')
            
            closestatus = 1
            
            try:
                fileobj = os.fdopen(fd)
                closestatus = 2
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                sttime = time.time()
                ended = False
                while not ended and (self.timeout == 0 or time.time() - sttime < self.timeout):
                    fdlists = select.select([fd],[],[], 1)
                    if fd in fdlists[0]:
                        while 1:
                            tempd = None
                            try:
                                tempd = fileobj.read(1)
                            except:
                                tempd = None
                                
                            if tempd == None:
                                break
                            elif len(tempd) > 0:
                                data = data + tempd
                            else:
                                ended = True
                                break
                if ended:
                    status = 1
            except:
                status = -1
    
            if closestatus == 2:
                fileobj.close()
                closestatus = 0
            elif closestatus == 1:
                os.close(fd)
                closestatus = 0
                
            return (status, data)


    class TimeoutableShellCommandCommunicateThread(threads.Thread):
        def __init__(self, sbp):
            threads.Thread.__init__(self)
            self.subp = sbp
            self.data = ''
            self.err = ''
            
        def run(self):
            fd_o = self.subp.stdout.fileno()
            fd_e = self.subp.stderr.fileno()
          
            fl = fcntl.fcntl(fd_o, fcntl.F_GETFL)
            fcntl.fcntl(fd_o, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            fl = fcntl.fcntl(fd_e, fcntl.F_GETFL)
            fcntl.fcntl(fd_e, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
            ended_o = False
            ended_e = False
            while not (ended_o and ended_e and self.subp.poll() != None) and not self.isTerminated():
                fdlists = select.select([fd_o, fd_e],[],[], 1)
                if fd_o in fdlists[0]:
                    while not ended_o and not self.isTerminated():
                        tempd = None
                        try:
                            tempd = self.subp.stdout.read(1)
                        except:
                            tempd = None
                            
                        if tempd == None:
                            break
                        elif len(tempd) > 0:
                            self.data = self.data + tempd
                        else:
                            ended_o = True
                            break
                if fd_e in fdlists[0]:
                    while not ended_e and not self.isTerminated():
                        tempd = None
                        try:
                            tempd = self.subp.stderr.read(1)
                        except:
                            tempd = None
                            
                        if tempd == None:
                            break
                        elif len(tempd) > 0:
                            self.err = self.err + tempd
                        else:
                            ended_e = True
                            break
        
        def getResult(self):
            return [self.data, self.err]
            
            
    class TimeoutableShellCommand(object):
        def __init__(self):
            self.timeout = 120
            
        def setTimeout(self, tout):
            self.timeout = tout
            
        def execute(self, command):
            sb = None
            try:      
                sb = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except:
                return (-1, '', '')
    
            tsct = TimeoutableShellCommandCommunicateThread(sb)
            tsct.start()
            if not tsct.wait_sleeping_timeout(self.timeout, 0.1):
                tsct.terminate()
                tsct.wait()
    
            status = sb.returncode
            (stdo, stde) = tsct.getResult()
    
            if status == None:
                status = -1
            
            return (status, stdo, stde)


elif os.name == 'nt':
    
    # implementation for Windows systems

    class TimeoutableShellCommandTerminatorThread(threads.Thread):
        def __init__(self, sbp, timeout):
            threads.Thread.__init__(self)
            self.subp = sbp
            self.timeout = timeout
            
        def run(self):
            starttime = time.time()
            while not self.isTerminated():
                if time.time() - starttime > self.timeout:
                    try:
                        self.subp.terminate()
                    except:
                        pass
                    break
                else:
                    time.sleep(0.1)

					
    class TimeoutableShellCommand(object):
        def __init__(self):
            self.timeout = 120
            
        def setTimeout(self, tout):
            self.timeout = tout
            
        def execute(self, command):    
            sb = None
            try:      
                sb = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except:
                return (-1, '', '')
    
            tsctt = TimeoutableShellCommandTerminatorThread(sb, self.timeout)
            tsctt.start()
            (stdo, stde) = sb.communicate()
            tsctt.terminate()
            status = sb.returncode

            if status == None:
                status = -1
			
            return (status, stdo, stde)
