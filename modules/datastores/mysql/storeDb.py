#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            storeDb.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         1.0i
#
# Date:            03.01.2017
#
# Description:     Data Store class to store logged data values into a
#                  MySql database.
#                  
# Requirements:    Python interpreter 2.4 or newer (www.python.org)
#                  (tested with 2.4.3)
# 
#                  MySQL-python library (MySQLdb) 
#                  (http://sourceforge.net/projects/mysql-python)
#
#                    or 
#                   
#                  MySQL Connector/Python (mysql.connector)
#                  (https://dev.mysql.com/doc/connector-python/en/)
#
###########################################################################

# Imports

from modules.core import store
from modules.core import configuration

# MySQLdb module, not loaded until init of DBStore class instance
MySQLdb = None

# MySQL.connector module, not loaded until init of DBStore class instance
MySQLconn = None


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
        self.USE_MYSQL_CONNECTOR = 0

    def handleConfiguration(self, conf):
        if not self.initStoreFilters(conf):
            return (0, "Invalid store filter.")
        
        self.DB_HOST = conf.getValue('HOST', '', self.getModuleName())
        try:
            self.DB_PORT = int(conf.getValue('PORT', '3306', self.getModuleName()))
        except:
            return (0, 'Invalid DB port value.')
        self.DB_USER = conf.getValue('USER', '', self.getModuleName())
        self.DB_PASSWD = conf.getValue('PASSWD', '', self.getModuleName())
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

        try:
            self.USE_MYSQL_CONNECTOR = conf.isTrue('USE_MYSQL_CONNECTOR', self.getModuleName())
        except:
            self.USE_MYSQL_CONNECTOR = 0

        return (1, '')

    def initConfiguration(self):
        if self.USE_MYSQL_CONNECTOR:
            try:
                global MySQLconn
                MySQLconn = __import__('mysql', globals(), locals(), ['connector'])
            except Exception as e:
                print("Exception: ", str(e))
                self.Log("ERROR: Error loading database module mysql.connector")
                return (0, 'DBStore: Error loading databse module mysql.connector')
        else:
            try:
                global MySQLdb
                MySQLdb = __import__('MySQLdb') 
            except Exception as e:
                print("Exception: ", str(e))
                self.Log("ERROR: Error loading database module MySQLdb")
                return (0, 'DBStore: Error loading databse module MySQLdb')
        
        status = 0
        sqlstmt = ""
        try:
            if self.USE_MYSQL_CONNECTOR:
                db = MySQLconn.connector.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                     password=self.DB_PASSWD, database=self.DB_NAME, consume_results=True)
            else:
                db = MySQLdb.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                     passwd=self.DB_PASSWD, db=self.DB_NAME)
            cur = db.cursor()
            if self.DB_SCHEMA == 1:
                sqlstmt = CREATE_TALO_DATA_1
                cur.execute(sqlstmt)
                sqlstmt = CREATE_TALO_POSITIONS_1
                cur.execute(sqlstmt)
            sqlstmt = "SELECT " + self.DB_TIMECOL + " FROM " + self.DB_TABLE + " LIMIT 1"
            cur.execute(sqlstmt)
            cur.close()
            
            cur = db.cursor()
            sqlstmt = "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = \'%s\' AND COLUMN_NAME = \'%s\'" % (self.DB_TABLE, self.DB_TIMECOL)
            cur.execute(sqlstmt)
            res = cur.fetchall()
            
            try:
                if res[0][0].upper() == 'TIMESTAMP':
                    self.TIMECOL_IS_TIMESTAMP_TYPE = 1
            except:
                pass
            db.close()
            status = 1
        except Exception as e:
            print("Exception SQL Query Error: ", e)
            self.Log("ERROR: Error in database operation, SQL: %s (%s)" % (sqlstmt, e.__str__()))
            status = 0
        if status:
            self.initPositions()
            return (1, '')
        else:
            return (0, 'DBStore: Errors with database access.')

    def initPositions(self):
        if self.DB_SCHEMA == 1:
            self.POSITIONS = {}
            sqlstmt = ""
            try:
                if self.USE_MYSQL_CONNECTOR:
                    db = MySQLconn.connector.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                         password=self.DB_PASSWD, database=self.DB_NAME)
                else:
                    db = MySQLdb.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                         passwd=self.DB_PASSWD, db=self.DB_NAME)
                cur = db.cursor()
                sqlstmt = "SELECT id, position_name FROM talo_positions"
                cur.execute(sqlstmt)
                res = cur.fetchall()
                cur.close()
                db.close()
                for row in res:
                    self.POSITIONS[row[1]] = row[0]
            except:
                self.Log("ERROR: Error in database operation, SQL: " + sqlstmt)
 
    def insertDataImpl(self, timeval, values):
        if self.DB_SCHEMA == 1:
            if len(self.POSITIONS.keys()) <= 0:
                self.initConfiguration()
            
            status = 1
            for val in values:
                if not self.POSITIONS.__contains__(val[0]):
                    status = 0
                    break
            if status == 0:
                self.initPositions()
                toadd = []
                for val in values:
                    if not self.POSITIONS.__contains__(val[0]):
                        toadd.append(val[0])
                                
                try:
                    if self.USE_MYSQL_CONNECTOR:
                        db = MySQLconn.connector.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                         password=self.DB_PASSWD, database=self.DB_NAME)                        
                    else:
                        db = MySQLdb.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                         passwd=self.DB_PASSWD, db=self.DB_NAME)
                    cur = db.cursor()
                    for col in toadd:
                        sqlstmt = "INSERT INTO talo_positions (position_name) VALUES ('"
                        sqlstmt = sqlstmt + col
                        sqlstmt = sqlstmt + "')"
                        cur.execute(sqlstmt)
                    cur.close()
                    db.commit()
                    db.close()
                except:
                    self.Log("ERROR: Error in database operation, SQL: " + sqlstmt)
                    self.POSITIONS = {}
                    return 0
                self.initPositions()

        sqlstmt = ""
        try:
            if self.USE_MYSQL_CONNECTOR:
                db = MySQLconn.connector.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
                                     password=self.DB_PASSWD, database=self.DB_NAME)
            else:
                db = MySQLdb.connect(host=self.DB_HOST, port=self.DB_PORT, user=self.DB_USER, \
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
        return 'MYSQLDB'

    @staticmethod
    def getAllowedConfigurationKeys():
        return (['HOST', 'PORT', 'USER', 'PASSWD', 'NAME', 'TABLE', 'TIMECOL', 'DB_SCHEMA_VERSION', 'USE_MYSQL_CONNECTOR'], [])


###########################################################################

# Functions

def checkDBValue(val):
    if (val and len(val) > 0):
        return val
    return "NULL"

