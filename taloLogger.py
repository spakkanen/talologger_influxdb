#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            taloLogger.py
#
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
#
HELP_TEXT = """
# Usage:           python taloLogger.py --help
#                  python taloLogger.py [-d] [--nodaemon] [-v] [-l] [-f configuration_file]
#
#                  Options (options override the configuration file):
#                    --help     - Prints out a help and exits.
#
#                    -d         - Runs the application in daemon mode. Command will
#                                 return to shell and a daemon will be forked to
#                                 run in the background. 
#
#                    --nodaemon  - No daemon mode. Even if -d option or configuration
#                                 file directives would make taloLogger run in daemon
#                                 mode, this overrides them all and prevents forking.
#
#                    -v         - Enable debug/verbose logging.
#
#                    -l         - Console log mode. 
#
#                    -f configuration_file - Use the given filename as configuration
#                                 file for the application.
#
#                  Parameters:
#                                 None.
#
#                  Configuration:
#                                 See file taloLogger.conf for example configuration
#                                 and configuration keys.
#
"""
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         2.0
#
# Date:            14.02.2025
#
# Functions:       -
#                   
# Description:     House automation logger application for Python. The primary
#                  driver has been to produce a logger application to read Ouman
#                  control device and 1-wire sensor values and log them 
#                  periodically to MySql database. The application has been
#                  extended with various data source and data storage 
#                  modules.
#                  
#                  Can be extended to log to different data storages: file,
#                  rrdtool, database, etc. Suggest a new data storage for the 
#                  author if you need a specific module.
#
#                  Currently supported data sources:
#                    + Any runnable shell command or program
#                    + OneWire bus appliances and sensors using either OWFS,
#                      DigiTemp or EDS OW-SERVER-ENET-2 interface 
#                    + Modbus devices, serial line RTU and ASCII modes and
#                      Modbus TCP over network connection.
#                    + Ouman 200 and 686 series controllers using serial connection
#                    + Ouman EH800 controllers using ethernet connection
#                    + Rego600 series controllers using serial connection
#                    + Rego800 and 1000 controllers with Can232/CanUSB interface module.
#                    + Husdata H1-interface module with serial/USB connetion,
#                      supports multiple heat pumps 
#                      (see http://www.husdata.se/dl.asp?h=22344)
#                    + Ekowell heat pump controllers using serial connection
#                    + Nibe heat pump controllers using serial connection,
#                      modbus or OpenHab NibeGW (UDP over network).
#                    + ThermIQ interface (www.thermiq.net) connected to Thermia 
#                      or Danfoss heat pumps
#                    + Thermia heat pump controllers using serial connection
#                    + Siemens SmartWeb module using network (web) connection
#                    + Telldus TellStick Duo wireless sensor devices, 
#                      using telldus-core-library
#                    + Telldus TellStick Net wireless sensor devices, using Telldus
#                      Live API (over network from the remote service).
#                    + Raspberry Pi GPIO inputs (only on Raspberry Pi with 
#                      taloLoggerPi)
#                    + Enervent EDA using Modbus Serial RTU from device bus and
#                      ModbusTCP over network from Enervent Freeway WEB interface.
#                    + Stiebel Eltron heat pumps using Can232/CanUSB interface module
#                      (experimental)
#                    + Fronius Solar API
#                    + deCONX REST-API, Zigbee sensors
#                    + HomeWizard Enery API
#
#                  Currently supported data storages:  
#                    + text file (incl. XML format)
#                    + RRD database file
#                    + MySQL database tables
#                    + PostgreSQL database tables
#                    + SQLite3 database files
#                    + ThingSpeak cloud
#                    + MQTT broker
#                    + InfluxDB database
#
# Requirements:    Python interpreter 2.7 or newer (www.python.org).
#                  Series 3.X Python not supported.
# 
#                  For Modbus, Ouman, Husdata, Thermia, Rego600, RegoCan, Ekowell,  
#                  Nibe, ThermIQ, Enervent EDA and Stiebel Eltron Can controller logging:
#                    Python Serial Port Extension: pySerial  
#                    (http://pyserial.wiki.sourceforge.net/pySerial)
#
#                  For MySQL database data storage:
#                    MySQL-python library (MySQLdb) 
#                    (http://sourceforge.net/projects/mysql-python)
#
#                  For PostgreSQL database data storage:
#                    Psycopg2-library. 
#                    (http://initd.org/psycopg/)
#
#                  For 1-wire data sources one of below:
#                    OWFS (http://www.owfs.org/) 
#                    DigiTemp (http://www.digitemp.com/)
#
#                  For RRDtool data storage:
#                    RRDtool (http://oss.oetiker.ch/rrdtool/)
#
#                  For Telldus Tellstick Duo wireless sensor sources:
#                    telldus-core (http://developer.telldus.se/doxygen/)
#
#                  For Telldus TellStick Live/Net sensor sources:
#                    python-oauth
#
#                  For Raspberry Pi GPIO sources:
#                    taloLoggerPi (http://olammi.iki.fi/sw/taloLoggerPi/)
#
#                  For MQTT data storage:
#                    python-paho-mqtt library (https://pypi.org/project/paho-mqtt/)
#
###########################################################################

# Imports

import sys, os
import string, re, time
import traceback
import platform
import urllib.request as urllib2
import subprocess

from modules.core import threads
from modules.core import configuration
from modules.core import dataSource
from modules.core import log
from modules.core import store
from modules.core import virtualMeasures
from modules.core import persistState

from modules.datasources import *

from modules.datastores import *

###########################################################################

# Constants

VERSION = "v2.0"

DEFAULT_LOG_INTERVAL = 120
DEFAULT_LOG_INTERVAL_LIMIT = 5

###########################################################################

# Globals

main_terminated = 0

LOG = None

###########################################################################

# Classes


class TaloLoggerThreadMaster(log.Logging, dataSource.DataSourceListener):
    def __init__(self, meas, virt, sources, stores, cmds):
        log.Logging.__init__(self, 'main')

        self.inqueue = []
        self.inqueue_item = []
        self.inq_lock = threads.Lock()
        self.commands = cmds
        self.measures = meas

        self.loggerThread = TaloLoggerThreadLogger(self, sources)
        self.storeThread = TaloLoggerThreadStore(self, meas, virt, stores, cmds)

    def terminate(self):
        self.loggerThread.terminate()
        self.storeThread.terminate()

    def isterminated(self):
        if self.loggerThread.isterminated() or self.storeThread.isterminated():
            return True
        return False

    def wait_sleeping(self):
        self.loggerThread.wait_sleeping()
        self.storeThread.wait_sleeping()

    def start(self):
        if not self.loggerThread.start() or not self.storeThread.start():
            self.loggerThread.terminate()
            self.storeThread.terminate()
            return False
        return True

    def queue(self, type, val, timeval):
        # run commands PRECYCLE
        initialresult = {}
        runPhaseCommands(self.commands['PRECYCLE'], initialresult, self)
        
        # val for examples ['NIBERS485.BT1 Outdoor temp', 'NIBERS485.BT2 supply temp S1', 'NIBERS485.EB100-EP14-BT3 Return temp', 'NIBERS485.BT7 Hot Water top', 'NIBERS485.BT6 Hot Water load', 'NIBERS485.Compressor State EP14', 'NIBERS485.Compressor status EP15', 'NIBERS485.EB108-EP15 Heat med pump status', 'NIBERS485.Fan speed current', 'NIBERS485.F135 Heat pump']
        # timeval is unixtime.

        initialdata = {}
        for meas in self.measures:
            if meas[0] in initialresult:
                initialdata[meas[1]] = initialresult[meas[0]]

        if self.inq_lock.lock_wait():
            self.inqueue_item.append([type, val, timeval, initialdata])
            temp = {}
            for v in val:
                temp2 = v.split('.', 1)
                if not temp.__contains__(temp2[0]):
                    temp[temp2[0]] = [ temp2[1] ]
                else:
                    temp[temp2[0]].append(temp2[1])
            for k in temp.keys():
                self.inqueue.append([k, temp[k], timeval])
            self.inq_lock.free()

    def dataReceived(self, moduleid, data, queuets):
        if self.inq_lock.lock_wait():
            if len(self.inqueue_item) > 0:
                for item in self.inqueue_item:
                    if item[2] == queuets:
                        for key in data.keys():
                            tkey = moduleid + '.' + key
                            #self.Debug("Measure datas:" + str(item))

                            if tkey in item[1]:
                                item[3][tkey] = data[key]
                            else:
                                self.Log("Received not queried data: " + tkey)
                        break
            else:
                self.Log("Received not queried data.")
            self.inq_lock.free()
        

class TaloLoggerThreadLogger(threads.Thread, log.Logging):
    def __init__(self, master, sources):
        threads.Thread.__init__(self)
        log.Logging.__init__(self, 'TaloLoggerThreadLogger')
        self.myMaster = master
        self.datasourcelist = sources
        self.terminated = 0

    def terminate(self):
        self.terminated = 1

    def isterminated(self):
        return self.terminated
        
    def run(self):
        while not self.terminated:
            try:
                # check if there is something to do
                if self.myMaster.inq_lock.lock_wait():
                    temp = None
                    if len(self.myMaster.inqueue) > 0:
                        temp = self.myMaster.inqueue[0]
                        self.myMaster.inqueue = self.myMaster.inqueue[1:]
                    self.myMaster.inq_lock.free()

                    if temp != None:
                        # temp[0] is NIBERS485.
                        # temp[1] for examples 'BT1 Outdoor temp', 'BT2 supply temp S1', 'EB100-EP14-BT3 Return temp', 'BT7 Hot Water top', 'BT6 Hot Water load', 'Compressor State EP14', 'Compressor status EP15', 'EB108-EP15 Heat med pump status', 'Fan speed current', 'F135 Heat pump'.
                        # temp[2] is unixtime.
                        fnd = False                    
                        isok = False
                        for s in self.datasourcelist:
                            if s.getServiceName() == temp[0]:
                                fnd = True
                                if s.runDataSourceQueryCommandAsync(self.myMaster, temp[0], temp[1], temp[2]):
                                    isok = True
                                else:
                                    self.Log("Unable to start data source query for module " + temp[0] + ".")
                                break
                        if not fnd:
                            self.Log("Unknown command source " + temp[0])
                        if not isok:
                            tempdata = {}
                            for key in temp[1]:
                                tempdata[key] = ""
                            self.myMaster.dataReceived(temp[0], tempdata, temp[2])
                    else:
                        time.sleep(1)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                self.Log("Exception: " + e.__str__())
                self.terminated = 1


class TaloLoggerThreadStore(threads.Thread, log.Logging, persistState.StatePersistCapable):
    def __init__(self, master, meas, virt, stores, cmds):
        threads.Thread.__init__(self)
        log.Logging.__init__(self, 'main')
        persistState.StatePersistCapable.__init__(self, self, 'core_TaloLoggerThreadStore')
        self.myMaster = master
        self.storelist = stores
        self.measures = meas
        self.virtuals = virt
        self.commands = cmds
        self.terminated = 0

        self.prevresult = self.loadState()
        if self.prevresult == None:
            self.prevresult = {}

    def terminate(self):
        self.terminated = 1

    def isterminated(self):
        return self.terminated

    def run(self):
        while not self.terminated:
            try:
                # check if there is something to do
                if self.myMaster.inq_lock.lock_wait():
                    haslock = True    
                    status = 1
                    while len(self.myMaster.inqueue_item) > 0 and status == 1: 
                        for k in self.myMaster.inqueue_item[0][1]:
                            if k not in self.myMaster.inqueue_item[0][3]:
                                status = 0
                                break
                        if status:
                            item = self.myMaster.inqueue_item[0]
                            self.myMaster.inqueue_item = self.myMaster.inqueue_item[1:]
                            haslock = False
                            self.myMaster.inq_lock.free()
                            
                            tempresult = item[3]
                            for k in tempresult.keys():
                                if len(tempresult[k]) <= 0:
                                    self.Debug("ERROR: Received none or unknown data for command " + k + ".")                    
                            self.handleResult(item)
                            
                            if not self.terminated:
                                if self.myMaster.inq_lock.lock_wait():
                                    haslock = True
                                else:
                                    break
                            else:
                                break
                    if haslock:
                        self.myMaster.inq_lock.free()
                if not self.terminated:
                    time.sleep(1)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                print("Exception: " + e.__str__())
                self.Log("Exception: " + e.__str__())
                self.terminated = 1
        
    def handleResult(self, item):
        if item[0] == 'log':
            self.handleLogResult(item[2], item[3])
        else:
            data = item[3]
            self.Log("Received unknown item type " + item[0])
            for k in data.keys():
                self.Log("  " + k + ":" + data[k])
        
    def handleLogResult(self, timeval, data):
        self.Log("INFO: Storing logged data with " + repr(len(data)) + " points.")

        # map the result data to keys and values
        resultdict = {}
        for item in self.measures:
            resultdict[item[0]] = data[item[1]]

        # run commands PREVIRTUAL
        runPhaseCommands(self.commands['PREVIRTUAL'], resultdict, self)
            
        virtresult = virtualMeasures.HandleVirtuals(self, self.virtuals, timeval, resultdict, self.prevresult)
        for k in virtresult.keys():
            resultdict[k] = virtresult[k]
        self.prevresult = resultdict
        self.prevresult['%TIME%'] = timeval    
        self.saveState(self.prevresult)

        # run commands PRESTORE
        runPhaseCommands(self.commands['PRESTORE'], resultdict, self)

        result = []
        num = 0
        for item in self.measures + self.virtuals:
            tempres = resultdict[item[0]]
            result.append([item[0], tempres])
            if len(tempres) > 0:
                num = num + 1

        if num > 0:
            if len(self.storelist) > 0:
                for store in self.storelist:
                    store.insertData(timeval, result)
            else:
                temps = ""
                temps = "Logged data for timestamp %s" % time.strftime('%Y%m%d%H%M%S', time.localtime(timeval))
                for item in result:
                    temps = temps + "\n    " + item[0] + ": " + item[1]
                self.Log(temps)
        else:
            self.Log("Completely empty result, not storing data.")

        # run commands POSTCYCLE
        runPhaseCommands(self.commands['POSTCYCLE'], resultdict, self)

###########################################################################

# Functions

def runPhaseCommands(cmds, result, log):
    for cmd in cmds:
        runPhaseCommand(cmd[1], cmd[0] == 1, result, log)

def runPhaseCommand(cmd, reload, result, log):
    try:
        resultfile = persistState.saveCycleState(result)
    except:
        log.Log("ERROR: Unable to save logging cycle state before command: " + cmd)

    env = dict(os.environ)
    env['TALOLOGGER_TRANSIENT_STATE'] = resultfile
    stat = runCmdWithEnv(cmd, env, log)
    if reload == 1:
        if stat == 0:
            log.Debug("Reloading logging cycle state after command: " + cmd)
            try:
                persistState.loadCycleState(resultfile, result)
            except Exception as e:
                log.Log("ERROR: Unable to load logging cycle state after command: " + cmd + " (Exception: " + str(e) + ")")
        else:
            log.Debug("NOTE: Logging cycle command returned non zero status, not reloading state data.")
        
    try:
        os.unlink(resultfile)
    except:
        log.Log("ERROR: Cannot remove cycle state file: " + resultfile)

def runCmdWithEnv(cmd, env, log):
    MAXEXECUTIONTIME = 30.0
    starttime = time.time()
    stat = None

    try:
        log.Debug("Running cycle phase command: " + cmd)
        p = subprocess.Popen(cmd, shell=True, env=env)
        stat = p.poll()
        while stat is None and time.time() < starttime + MAXEXECUTIONTIME:        
            time.sleep(0.1)
            stat = p.poll()
        
        if stat is None:
            log.Log("ERROR: Cycle command timeout, terminating command, continuing logging: " + cmd)
            try:
                p.terminate()
            except:
                log.Log("ERROR: Unable to terminate cycle command: " + cmd)
    except:
        stat = None
        log.Log("ERROR: Error when running cycle command: " + cmd)

    return stat

def CheckPythonVersion():
    version = platform.python_version_tuple()
    # Require Python 2.7 or newer.
    try:
        if int(version[0]) != 3:
            print("ERROR: Invalid Python version to run taloLogger. Required Python version 3.")
            print("       Detected Python version: %s.%s.%s" % version)
            sys.exit(1)
    except:
        print("Error determining Python version.")
    return

def HUPhandler(signum, frame):
  global main_terminated, LOG
  LOG.log("Terminating due to SIGHUP.")
  main_terminated = 1
  return

def TERMhandler(signum, frame):
  global main_terminated, LOG
  LOG.log("Terminating due to SIGTERM.")
  main_terminated = 1
  return

def INThandler(signum, frame):
  global main_terminated, LOG
  LOG.log("Terminating due to SIGINT.")
  main_terminated = 1
  return

def GetModuleTypeAndName(str):
    if str.find(':') < 0:
        return ('', '')
    [mtype, mname] = str.split(':', 1)
    mtype = mtype.strip()
    mname = mname.strip()
    return (mtype, mname)

def GetDataSourceClass(mtype):
    for cls in dataSource.DataSource.__subclasses__():
        if issubclass(cls, configuration.Configurable):
            if mtype == cls.getModuleTypeName():
                return cls
    return None

def GetDataStoreClass(mtype):
    for cls in store.Store.__subclasses__():
        if issubclass(cls, configuration.Configurable):
            if mtype == cls.getModuleTypeName():
                return cls
    return None


####### main ##########################################################

def main():
  global main_terminated, LOG

  CheckPythonVersion()

  CONFIGURATION_FILE = "taloLogger.conf"

  nodaemon = 0
  daemon = 0
  logconsole = 0
  verbose = 0

  # handle command line parameters
  i = 1
  while i < len(sys.argv):
      if sys.argv[i] == '--help':
          Help()
          sys.exit(1)
      elif sys.argv[i] == '-l':
          logconsole = 1
      elif sys.argv[i] == '-v':
          verbose = 1
      elif sys.argv[i] == '-d':
          daemon = 1
      elif sys.argv[i] == '--nodaemon':
          nodaemon = 1
      elif  sys.argv[i] == '-f' and i+1 < len(sys.argv):
          i = i + 1
          CONFIGURATION_FILE = sys.argv[i]
      else:
          Usage()
          sys.exit(1)

      i = i + 1 

  # load configuration file
  conf = configuration.Configuration()
  
  conf.addConfigurable(log.Logger)

  conf.addAllowedKeys(['LOG_INTERVAL', 'LOG_INTERVAL_LIMIT', 'DAEMON_MODE', 'PERSISTENT_STATE_DIRECTORY'])
  conf.addAllowedListKeys(['DATASOURCE', 'DATASTORE', 'MEASURE', 'VIRTUAL', 'STOREFILTER', 'COMMAND'])

  (confstat, errmsg) = conf.loadFile(CONFIGURATION_FILE)
  if confstat == 0:
      print("ERROR: Cannot read configuration file: " + CONFIGURATION_FILE)
      sys.exit(1)
  elif confstat == -1:
      print("ERROR: Error reading configuration file: " + CONFIGURATION_FILE)
      print(errmsg)
      sys.exit(1)

  if logconsole:
      conf.setValue('CONSOLE_LOGGING', 'true')
  if verbose:
      conf.setValue('VERBOSE_LOGGING', 'true')

  LOG = log.Logger(conf)
  log.Logging.setLogger(LOG)

  pstate_dir = conf.getValue('PERSISTENT_STATE_DIRECTORY', '')
  if pstate_dir:
      pstate_dir = pstate_dir.strip()
      if len(pstate_dir) > 0:
          LOG.log("Persistent state directory: " + pstate_dir)
          if not os.path.isdir(pstate_dir):
              LOG.log("WARNING: Persisted state directory does not exist. Creating.")
              try:
                  os.mkdir(pstate_dir)
              except:
                  LOG.log("ERROR: Cannot create persistent state directory: " + pstate_dir)
                  sys.exit(1)
          if not pstate_dir.endswith(os.sep):
              pstate_dir = pstate_dir + os.sep           
          if not os.path.isdir(pstate_dir):
              LOG.log("ERROR: Persistent state directory does not exist. Exiting: " + pstate_dir)
              sys.exit(1)  
          persistState.StatePersistCapable.setPersistentStateDirectory(pstate_dir)
                    
  sources = []
  for st in conf.getValue('DATASOURCE', []):
      (mtype, mname) = GetModuleTypeAndName(st)
      if len(mtype) <= 0 or len(mname) <= 0:
          LOG.log("ERROR: Error in DATASOURCE definition: " + st)
          sys.exit(1)
          
      sourceClass = GetDataSourceClass(mtype)
      if sourceClass == None:
          LOG.log("ERROR: Invalid datasource type in DATASOURCE definition: " + str(st))
          sys.exit(1)
      sources.append( sourceClass(mname) )          
                    
  if len(sources) <= 0:
      LOG.log("ERROR: No data sources configured. Nothing to log. Exiting.")
      sys.exit(1)

  stores = []
  for st in conf.getValue('DATASTORE', []):
      (mtype, mname) = GetModuleTypeAndName(st)
      if len(mtype) <= 0 or len(mname) <= 0:
          LOG.log("ERROR: Error in DATASTORE definition: " + st)
          sys.exit(1)
      
      storeClass = GetDataStoreClass(mtype)
      if storeClass == None:
          LOG.log("ERROR: Invalid datastore type in DATASTORE definition: " + st)
          sys.exit(1)
      stores.append( storeClass(mname) )
          
  if len(stores) <= 0:
      LOG.log("WARNING: No log data stores configured. Data is written to application log.")

  if not nodaemon and (daemon or conf.isTrue('DAEMON_MODE')):
      pid = os.fork()
      if (pid != 0):
          LOG.log("Starting taloLogger.py (" + VERSION + ") as daemon.")
          sys.exit(0) 
  else:
      LOG.log("Starting taloLogger.py (" + VERSION + ").")
          
  # try to enable signal handlers, if fails, we are probably using Windows
  try:
      import signal 
      signal.signal(signal.SIGTERM, TERMhandler)
      signal.signal(signal.SIGINT, INThandler)
      if sys.platform.startswith('linux'):
        # SIGHUP not defined for Windows platform. Disabling pylint warning.
        # pylint: disable=no-member
        signal.signal(signal.SIGHUP, HUPhandler)
  except:
      pass

  LOG_INTERVAL = int(conf.getValue('LOG_INTERVAL', DEFAULT_LOG_INTERVAL))
  LOG_INTERVAL_LIMIT = int(conf.getValue('LOG_INTERVAL_LIMIT', DEFAULT_LOG_INTERVAL_LIMIT))

  measurekeys = []
  measurepositions = []
  measures = []
  for item in conf.getValue('MEASURE', []):
      temps = item.split(':', 1)
      if len(temps) < 2:
          LOG.log("ERROR: Invalid MEASURE configuration: " + item)
          sys.exit(1)          
      key = temps[0].strip()
      value = temps[1].strip()
      if len(key) <= 0 or len(value) <= 0:
          LOG.log("ERROR: Invalid MEASURE configuration: " + item)
          sys.exit(1)
      if len( value.split('.', 1) ) < 2:
          LOG.log("ERROR: Invalid MEASURE configuration: " + item)
          sys.exit(1)
      if key in measurepositions:
          LOG.log("ERROR: Duplicate MEASURE key: " + key)
          sys.exit(1)                    
      measurepositions.append(key)
      if value not in measurekeys:
          measurekeys.append(value)
      measures.append([key, value])

  if len(measures) <= 0:
      LOG.log("ERROR: No configured measures. Nothing to log. Exiting.")
      sys.exit(1)             

  LOG.debug("main: INFO: Initialized measure data: " + str(measures))

  virtualpositions = []
  virtuals = []
  for item in conf.getValue('VIRTUAL', []):
      temps = item.split(':', 2)
      if len(temps) < 3:
          LOG.log("ERROR: Invalid VIRTUAL configuration: " + item)
          sys.exit(1)          
      key = temps[0].strip()
      try:
          type = int(temps[1].strip())
      except:
          type = 0
      value = temps[2].strip()
      if type < 1 or type > 1:
          LOG.log("ERROR: Invalid VIRTUAL configuration type: " + item)
          sys.exit(1)          
      if len(key) <= 0 or len(value) <= 0:
          LOG.log("ERROR: Invalid VIRTUAL configuration: " + item)
          sys.exit(1)
      if key in measurepositions or key in virtualpositions:
          LOG.log("ERROR: Duplicate MEASURE/VIRTUAL key: " + key)
          sys.exit(1)                    
      virtualpositions.append(key)
      virtuals.append([key, type, value])

  cmd_phases = ['PRECYCLE', 'PREVIRTUAL', 'PRESTORE', 'POSTCYCLE']
  commands = {}
  for phase in cmd_phases:
      commands[phase] = []
  for item in conf.getValue('COMMAND', []):
      temps = item.split(':', 3)
      if len(temps) < 3:
          LOG.log("ERROR: Invalid COMMAND configuration: " + item)
          sys.exit(1)          

      phase = temps[0].strip().upper()
      if not phase in cmd_phases:
          LOG.log("ERROR: Invalid COMMAND phase: " + item)
          sys.exit(1)

      try:
          type = int(temps[1].strip())
      except:
          type = -1
      if not type in [0, 1]:
          LOG.log("ERROR: Invalid COMMAND type: " + item)
          sys.exit(1)

      cmd = temps[2].strip()
      if len(cmd) <= 0:
          LOG.log("ERROR: Missing COMMAND command: " + item)
          sys.exit(1)

      commands[phase].append([type, cmd])

  # handle module configurations
  for confmod in sources + stores:
      (stat, msg) = conf.checkConfigurationKeys(confmod)
      if stat == -1:
          LOG.log("ERROR: Module %s has invalid configuration key: %s" % (confmod.getModuleName(), msg))
          sys.exit(1)          
      elif stat == 0:
          LOG.log("WARNING: Module %s: %s" % (confmod.getModuleName(), msg))
          sys.exit(1)          
            
      (stat, msg) = confmod.handleConfiguration(conf)
      if stat == 0:
          LOG.log("ERROR: Error configuring module " + confmod.getModuleName() + ": " + msg)
      elif stat == -1:
          LOG.log("FATAL ERROR: Error configuring modules. Exiting.: " + msg)
          sys.exit(1)
      elif stat == 1:
          LOG.debug("Module config read " + confmod.getModuleName())

  # initialize module configurations
  for confmod in sources + stores:      
      (stat, msg) = confmod.initConfiguration()
      if stat == 0:
          LOG.log("ERROR: Error initializing module " + confmod.getModuleName() + ": " + msg)
      elif stat == -1:
          LOG.log("FATAL ERROR: Error initializing modules. Exiting.: " + msg)
          sys.exit(1)
      elif stat == 1:
          LOG.log("Initialized module " + confmod.getModuleName())

  # check that STOREFILTER positions are all also measures for active modules
  for store in stores:
      (stat, msg) = store.checkStoreFilters(measurepositions+virtualpositions)
      if stat == 0:
          LOG.log("ERROR: Invalid store filter position for active module: " + msg)
          sys.exit(1)
  
  loggerthread = TaloLoggerThreadMaster(measures, virtuals, sources, stores, commands)

  if not loggerthread.start():
      LOG.log("ERROR: Cannot start logger thread.")
      sys.exit(1)

  while not main_terminated and not loggerthread.isterminated():
      t = time.time() % LOG_INTERVAL
      if t < LOG_INTERVAL_LIMIT:
          loggerthread.queue('log', measurekeys, time.time())
          t = time.time() % LOG_INTERVAL
      try:
          time.sleep(LOG_INTERVAL - t)
      except:
          pass

  loggerthread.terminate() 
  loggerthread.wait_sleeping()
  
  for storemod in stores:
      storemod.clearStagedData()
  
  for confmod in sources + stores:
      (stat, msg) = confmod.releaseConfiguration()
      if stat == 0:
          LOG.log("ERROR: Error releasing module: " + msg)

  LOG.log("Terminating.")


def Usage():
    print("USAGE:  python taloLogger.py --help")
    print("        python taloLogger.py [-d] [--nodaemon] [-v] [-l] [-f configuration_file]")


def Help():
    temps = HELP_TEXT.split('\n')
    for temp in temps:
        if len(temp) > 0 and temp[0] == '#':
            temp = temp[1:]
        if len(temp) > 0 and temp[0] == ' ':
            temp = temp[1:]
        print(temp)
 

###########################################################################

if __name__ == "__main__":
  main()
