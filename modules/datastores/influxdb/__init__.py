#!env python
# -*- coding: iso-8859-1 -*-
###########################################################################
# 
# File:            __init__.py
#
# License:         Donationware, see attached LICENSE file for more 
#                  information
#
# Author:          Saku Pakkanen (saku.pakkanen@gmail.com)
#
###########################################################################

# Imports

try:
  import os, sys

  dir_path = os.path.dirname(os.path.realpath(__file__))
  parent_dir_path = os.path.abspath(os.path.join(dir_path, os.pardir))
  sys.path.insert(0, parent_dir_path + "/influxdb")

  import storeInfluxDb
except ImportError as e:
    print('Relative import failed. Path: '+__name__+'. ImportError: ', e)

# Module definitions
# __all__ = []
