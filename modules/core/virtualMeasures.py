#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            virtualMeasures.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
# Version:         0.1b
#
# Date:            25.06.2014
#
# Description:     Module to evaluate virtual measures.
#                  
# Requirements:    Python interpreter 2.6 or newer (www.python.org)
# 
# Version history: ** 24.03.2013 v0.1a (Olli Lammi) **
#                  First version. 
#
#                  ** 25.06.2014 v0.1b (Olli Lammi) **
#                  Changed handling of missing values. Now replaced
#                  with None rather than failing. 
#
###########################################################################

# Imports

import sys, os 
import string, time 
import math
import re

from modules.core import log

###########################################################################

# Functions

# virtuals: [key, type, expression]

def HandleVirtuals(logger, virtuals, timeval, result, prevresult):
    tempresult = result

    for virt in virtuals:
        logger.Debug("Virtuals: Handling: " + virt[0])
        
        if virt[1] == 1:
            key = virt[0]
            expr = virt[2]

            if expr.count('%_%TIME%_%') > 0:
                expr = expr.replace('%_%TIME%_%', str(timeval))
                
            if expr.count('%/_%TIME%_/%') > 0:
                if prevresult in '%TIME%':
                    expr = expr.replace('%/_%TIME%_/%', str(prevresult['%TIME%']))
                else:
                    tempresult[key] = ""
                    continue
            
            for k in tempresult.keys():
                if expr.count('%_' + k + '_%') > 0:
                    if len(tempresult[k]) > 0:
                        expr = expr.replace('%_' + k + '_%', str(tempresult[k]))
            for k in prevresult.keys():
                if expr.count('%/_' + k + '_/%') > 0:
                    if len(prevresult[k]) > 0:
                        expr = expr.replace('%/_' + k + '_/%', str(prevresult[k]))
         
            if expr.count('%_') + expr.count('_%') > 0:
                logger.Log("ERROR: Virtuals: Unknown positions left in the expression. Substituting with None: " + expr)
                expr = re.sub('%_.+?_%', 'None', expr)

            if expr.count('%/_') + expr.count('_/%') > 0:
                logger.Log("ERROR: Virtuals: Unknown prev positions left in the expression. Substituting with None: " + expr)
                expr = re.sub('%/_.+?_/%', 'None', expr)
                                
            try:
                res = str(eval(expr))
            except:
                logger.Log("ERROR: Unable to evaluate virtual measurement expression: " + expr)
                res = ""
            if res == None or res == 'None':
                res = ""
            tempresult[key] = res
            logger.Debug("Virtuals: Virtual measurement (" + key + ") result: " + res)
                
        else:
            logger.Log("ERROR: Invalid or unimplemented type of virtual measurement, key: " + virt[0])

    virtresultdict = {}
    for virt in virtuals:
        virtresultdict[virt[0]] = tempresult[virt[0]]
    return virtresultdict
