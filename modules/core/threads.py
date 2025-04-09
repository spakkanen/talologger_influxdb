#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            threads.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.1c
#
# Date:            30.11.2016
#
# Description:     Library to implement threading and locking classes in
#                  python.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
# Version history: ** 02.12.2008 v1.0a (Olli Lammi) **
#                  First version. 
#
#                  ** 06.01.2013 v1.1a (Olli Lammi) **
#                  Added termination controlled version. 
#
#                  ** 14.05.2014 v1.1b (Olli Lammi) **
#                  Added error print when not able to start thread. 
#
#                  ** 30.11.2016 v1.1c (Olli Lammi) **
#                  Added time monitored lock that will free the lock if 
#                  reserved for too long (timeout).
#
###########################################################################
# Imports
###########################################################################

import sys
import threading
import traceback
import signal, time

###########################################################################

# Classes

class Lock(object):
    def __init__(self):
        self.mylock = threading.Lock()

    def lock_wait(self):
        return self.mylock.acquire()

    def lock_immediate(self):
      return self.mylock.acquire(0)

    def free(self):
        self.mylock.release()

RUNNING = 0
TERMINATING = 1
TERMINATED = 2

class Thread(object):
    def __init__(self):
        self.lock = Lock()
        self.tid = None
        self.thr_state = TERMINATED

    def start(self):
        if self.lock.lock_immediate():
            self.setRunning()
            try:
                self.tid = threading.Thread(target=self.main, args=(self,))
                self.tid.start()
            except Exception as e:
                print("ERROR: Error starting thread. Exception: " + e.__str__())
                self.setTerminated()
                self.lock.free()
                return 0
            return 1
        else:
            return 0

    def main(self, starter):
        try:
            print("Starting thread name: ", starter)
            starter.run()
        except Exception as e:
            print("ERROR: Error running thread id: " + str(self.tid), ", starter id: " + str(starter), "Exception: " + e.__str__())
            print(traceback.format_exc())
            
        starter.setTerminated()
        starter.lock.free()        

    def run(self):
        print("Unimplemented thread run method.")

    def wait(self):
        self.lock.lock_wait()
        self.lock.free()

    def wait_sleeping(self):
        while 1:
            if self.lock.lock_immediate():
               self.lock.free()
               return 
            else:
               time.sleep(1)

    def wait_sleeping_timeout(self, timeout, interval = 1.0):
        sttime = time.time()
        while 1:
            if self.lock.lock_immediate():
                self.lock.free()
                return True
            elif timeout > 0 and time.time() - sttime > timeout:
                return False
            else:
                time.sleep(interval)

    def setRunning(self):
        self.thr_state = RUNNING
        
    def setTerminated(self):
        if self.thr_state < 0:
            self.thr_state = -TERMINATED
        else:
            self.thr_state = TERMINATED

    def terminate(self):
        if self.thr_state == RUNNING:
            self.thr_state = TERMINATING
        if self.thr_state < 0:
            self.thr_state = -self.thr_state

    def setFail(self):
        self.thr_state = -TERMINATING

    def isRunning(self):
        if self.thr_state == RUNNING:
            return 1
        return 0

    def isFailed(self):
        if self.thr_state < 0:
            return 1
        return 0

    def isTerminated(self):
        return (self.thr_state != 0)

    def hasTerminated(self):
        return (self.thr_state == TERMINATED or self.thr_state == -TERMINATED)
    
    
class MonitoredLock(Lock, Thread):
    def __init__(self, timeout):
        Lock.__init__(self)
        Thread.__init__(self)
        self.TIMEOUT = timeout
        self.locktime = 0
        self.start()

    def lock_wait(self):
        result = self.mylock.acquire()
        if result:
            self.locktime = time.time()
        return result

    def lock_immediate(self):
        result = self.mylock.acquire(0)
        if result:
            self.locktime = time.time()
        return result

    def free(self):
        if self.mylock.locked():
            self.locktime = 0
            self.mylock.release()
    
    def reset(self):
        if self.mylock.locked():
            self.locktime = 0
            try:
                self.mylock.release()
            except:
                pass
            
    def run(self):
        while self.isRunning():
            time.sleep(1)
            if self.locktime > 0:
                if time.time() - self.locktime > self.TIMEOUT:
                    if self.mylock.locked():
                        self.locktime = 0
                        print("Freeing timed out lock...")
                        try:
                            self.mylock.release()
                        except:
                            pass
