#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            storeInfluxDb.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Saku Pakkanen (saku.pakkanen@gmail.com)
#
# Version:         1.0i
#
# Date:            10.02.2025
#
# Description:     Data Store class to store logged data values into a
#                  InfluxDB database.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
#
###########################################################################

# Imports

from influxdb_client import InfluxDBClient, Point, Dialect
from influxdb_client.client.write_api import SYNCHRONOUS

from modules.core import store
from modules.core import configuration

# InfluxDB module, not loaded until init of DBStore class instance
InfluxDB = None

# InfluxDB.connector module, not loaded until init of DBStore class instance
InfluxDBconn = None

client = None

###########################################################################

# Constants

CREATE_TALO_DATA_1 = "CREATE TABLE IF NOT EXISTS talo_data (" + \
                     "id INTEGER UNSIGNED PRIMARY KEY AUTO_INCREMENT, " + \
                     "time DATETIME NOT NULL, " + \
                     "position_id SMALLINT UNSIGNED NOT NULL, " + \
                     "value DOUBLE, " + \
                     "INDEX (time))"

CREATE_TALO_POSITIONS_1 = "CREATE TABLE IF NOT EXISTS talo_positions (" + \
                     "id SMALLINT UNSIGNED PRIMARY KEY AUTO_INCREMENT, " + \
                     "position_name VARCHAR(32) NOT NULL UNIQUE)"

###########################################################################

# Classes

class DBStore(store.Store):
    def __init__(self, modname):
        store.Store.__init__(self, modname)
        
        self.TIMECOL_IS_TIMESTAMP_TYPE = 0
        self.POSITIONS = {}

    def handleConfiguration(self, conf):
        if not self.initStoreFilters(conf):
            return (0, "Invalid store filter.")
        
        self.DB_URL = conf.getValue('URL', '', self.getModuleName())
        self.DB_TOKEN = conf.getValue('TOKEN_KEY', '', self.getModuleName())
        self.DB_ORG = conf.getValue('ORG', '', self.getModuleName())
        
        self.DB_NAME = conf.getValue('NAME', '', self.getModuleName())
        self.DB_TABLE = conf.getValue('TABLE', '', self.getModuleName())
        self.DB_TIMECOL = conf.getValue('TIMECOL', '', self.getModuleName())

        if not len(self.DB_NAME) > 0:
            return (-1, 'Missing database name from database configuration.')
        return (1, '')
    
    def connect(self):
        try:
          client = InfluxDBClient(url=self.DB_URL, token=self.DB_TOKEN, org=self.DB_ORG)
          return (client, 1)
        except Exception as e:
          print("Exception: ", str(e))
          self.Log("ERROR: Error loading database module InfluxDBClient")
          return (None, 0)

    def initConfiguration(self):
        status = 0
        sqlstmt = ""
        
        try:
            (client, status) = self.connect() # Connect to InfluxDB database.
            query_api = client.query_api()
            query_api.query('from(bucket:"data") |> range(start: -10m)')
            client.close()
            status = 1
        except Exception as e:
            print("Exception Query SQL Error: ", e)
            self.Log("ERROR: Query Error, SQL: %s (%s)" % (sqlstmt, e.__str__()))
            status = 0
        if status:
            return (1, '')
        else:
            return (0, 'DBStore: Errors with database access.')
 
    def insertDataImpl(self, timeval, values):
        sqlstmt = ""
        try:
            (client, status) = self.connect() # Connect to InfluxDB database.
            
            if status:
                print("ok")

            self.Log("Setting data to database using SQL: " + sqlstmt)

            client.close
        except Exception as e:
            print("Exception Query SQL Error: ", e)
            self.Log("ERROR: Query Error, SQL: " + sqlstmt)
            self.POSITIONS = {}
            return 0
        return 1

    @staticmethod
    def getModuleTypeName():
        return 'INFLUXDB'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['URL', 'TOKEN_KEY', 'ORG', 'NAME', 'TABLE', 'TIMECOL'], [])

###########################################################################

# Functions

def checkDBValue(val):
    if (val and len(val) > 0):
        return val
    return "NULL"
