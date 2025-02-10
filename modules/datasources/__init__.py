#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            __init__.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Olli Lammi (olammi@iki.fi)
#
###########################################################################

# Module definitions

import os

__all__ = []
basepath = os.path.dirname(os.path.abspath(__file__))
for fn in os.listdir(basepath):
    if os.path.isdir(basepath + os.sep + fn) and \
       os.path.isfile(basepath + os.sep + fn + os.sep + '__init__.py'):
        __all__.append(fn)

