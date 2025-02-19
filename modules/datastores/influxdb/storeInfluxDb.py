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
                
        self.DB_SCHEMA = conf.getValue('DB_SCHEMA_VERSION', '', self.getModuleName())
        if len(self.DB_SCHEMA) <= 0 or int(self.DB_SCHEMA) <= 0:
            self.DB_SCHEMA = 0
        elif len(self.DB_SCHEMA) > 0:
            self.DB_SCHEMA = int(self.DB_SCHEMA)
        if self.DB_SCHEMA == 1:
            self.DB_TABLE = 'talo_data'
            self.DB_TIMECOL = 'time'
        elif self.DB_SCHEMA == 0:
            if not len(self.DB_TABLE) > 0:
                return (-1, 'Missing database table name from database configuration.')
            if not len(self.DB_TIMECOL) > 0:
                return (-1, 'Missing database time column name from database configuration.')
        else:
            return (-1, 'Invalid DB schema version.')

        return (1, '')

    def initConfiguration(self):
        try:
          client = InfluxDBClient(url=self.DB_URL, token=self.DB_TOKEN, org=self.DB_ORG)
        except Exception as e:
          print("Exception: ", str(e))
          self.Log("ERROR: Error loading database module InfluxDB")
          return (0, 'DBStore: Error loading databse module InfluxDB')
        
        status = 0
        sqlstmt = ""
        try:
            query_api = client.query_api()
            tables = query_api.query('from(bucket:"data") |> range(start: -10m)')

            for table in tables:
              print("saku:"+ table)
              for record in table.records:
                print("saku2:"+record.values)

            client.close()
            status = 1
        except Exception as e:
            print("Exception Query Error: ", e)
            self.Log("ERROR: Query Error, SQL: %s (%s)" % (sqlstmt, e.__str__()))
            status = 0
        if status:
            return (1, '')
        else:
            return (0, 'DBStore: Errors with database access.')
 
    def insertDataImpl(self, timeval, values):
        if self.DB_SCHEMA == 1:
            if len(self.POSITIONS.keys()) <= 0:
                self.initConfiguration()

        sqlstmt = ""
        try:
            db = InfluxDB.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
              passwd=self.DB_PASSWD, db=self.DB_NAME)
            
            if self.TIMECOL_IS_TIMESTAMP_TYPE:
                cur = db.cursor()
                sqlstmt = "set time_zone = \'+0:00\'"
                cur.execute(sqlstmt)
                cur.close()

            if self.DB_SCHEMA == 1:
                timestr = "FROM_UNIXTIME(%d)" % (timeval, )

                for val in values:
                    cur = db.cursor()
    
                    posid = self.POSITIONS[val[0]]
                            
                    sqlstmt = "INSERT INTO " + self.DB_TABLE + " "
                    sqlstmt = sqlstmt + "(" + self.DB_TIMECOL + ", position_id, value) VALUES ("
                    sqlstmt = sqlstmt + "%s, %d, " % (timestr, posid)
                    sqlstmt = sqlstmt + checkDBValue(val[1]) + ")"
        
                    self.Debug("Inserting data to database using SQL: " + sqlstmt)
                    cur.execute(sqlstmt)
                    cur.close()
            else:
                timestr = "FROM_UNIXTIME(%d)" % (timeval, )
                
                cur = db.cursor()
                sqlstmt = "INSERT IGNORE INTO " + self.DB_TABLE + " "
                sqlstmt = sqlstmt + "(" + self.DB_TIMECOL 
                sqlstmt = sqlstmt + ") VALUES (" + timestr 
                sqlstmt = sqlstmt + ")"                
                cur.execute(sqlstmt)
                cur.close()

                self.Debug("Insert data to database using SQL: " + sqlstmt)              

                cur = db.cursor()    
                valuestrs = []
                for item in values:
                    valuestrs.append(item[0] + ' = ' + checkDBValue(item[1]))
                        
                sqlstmt = "UPDATE " + self.DB_TABLE + " SET "
                sqlstmt = sqlstmt + valuestrs.join(", ")
                sqlstmt = sqlstmt + " WHERE " + self.DB_TIMECOL + " = " + timestr
    
                self.Log("INFO: Update data to database using SQL: " + sqlstmt)
                cur.execute(sqlstmt)
                cur.close()
            db.commit()
            db.close()
        except:
            self.Log("ERROR: Error in database operation, SQL: " + sqlstmt)
            self.POSITIONS = {}
            return 0
        return 1

    @staticmethod
    def getModuleTypeName():
        return 'INFLUXDB'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['URL', 'TOKEN_KEY', 'ORG', 'NAME', 'TABLE', 'TIMECOL', 'DB_SCHEMA_VERSION'], [])

###########################################################################

# Functions

def checkDBValue(val):
    if (val and len(val) > 0):
        return val
    return "NULL"
