'''
  Program ChillerRdConfig.py
  
Description: ------------------------------------------------------------------
  This file contains the class construct to read the ASCII text file containing 
the information of the configuration of devices/equipment used in the stave thermo
evaluation.
  
  Flir A655sc IR camera;
  FTS Systems RC211B0 recirculating cooler; 
  Lenze ESV751N02YXC NEMA 4x inverter drive;
  Omega HH314A Humidity/Temperature Meter;
  Omega HH147U Data Logger Thermometer;
  Arduino UNO Rev 3 shield.

History: ----------------------------------------------------------------------
  V1.0 - Oct-2017  First public release.
  V1.4 - Jul-2018  Added code for the Arduino UNO to read the flow meter (Proteus
           08004BN1) and control three actuators (Swagelok SS-62TS4-41DC).
           Updated comments and modified screen messages to operator.
Environment: ------------------------------------------------------------------
  This program is written in Python 3.6.  Python can be freely downloaded from 
http://www.python.org/.  This program has been tested on PCs running Windows 10.

Author List: -------------------------------------------------------------------
  R. McKay    Iowa State University, USA  mckay@iastate.edu
  J. Yu       Iowa State University, USA  jieyu@iastate.edu
  W. Heidorn  Iowa State University, USA  wheidorn@iastate.edu
  
Notes: -------------------------------------------------------------------------

Dictionary of abbreviations: ---------------------------------------------------
  cls - class
  str - string
'''

# function __init__ ( strconfname ): 
#   initialize the class clsConfig
#   using config file name
# function get( strsection, strkey )
#   provide the section (device) name and key name
#   return the value in string
#
# function sections():
#   return the list of the section (devices) names
#
# function keys(strsection):
#   provide the section (device) name
#   return the list of keys for this section (device)
#

# Import section --------------------------------------------------------------
import configparser
import logging

# Class section ---------------------------------------------------------------
class clsConfig:
  def __init__(self, strconfname, strdevnamelist):
    """
      Acquire the devices configuration parameters from the text file containing all
      the parameters for each device to run as desired.
      The configuration file consists of sections, led by a [section] header and 
      followed by name: value or name=value.  Lines beginning with '#' are ignored.
    """
    self.strname = strconfname
    # allow_no_value=True: key having no value allowed
    # RawConfigParser: KEY not turned to lower case: key
    #                  if lower case keys preferred, use ConfigParser
    self.__config = configparser.RawConfigParser( allow_no_value=True )
    self.__config.read( strconfname )
    logging.info( 'Loading configuration file: ' + strconfname );

    # fixing the inline comment problem
    for strsection in self.__config.sections():
      if strdevnamelist is not None  and  strsection not in strdevnamelist: 
        logging.debug('Configure: ' + strsection + ' skipped. ')
        continue;

      logging.info('Configure: ' + strsection)
      for strkey in self.__config[strsection]:
        strvalcomment = self.__config[strsection][strkey]
        #
        # assuming inline comments starting with '#'
        #
        strval = [x for x in strvalcomment.split('#')][0].strip()
        self.__config.set(strsection, strkey, strval)
        logging.info(' - ' + strkey + ' '+ strval)

    logging.info( ' ---- ---- ---- ---- ');


  def get(self, strsection, strkey):
    """
      function to get a value by providing the section name and key name
    """
    if strsection not in self.__config.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return ""
    if strkey not in self.__config[ strsection ]:
      logging.error(' - ' + strkey + ' not found in config section: ' + strsection )
      return ""
    return self.__config[ strsection ][ strkey ]

  def sections(self):
    """
      function to get the list of the sections in the config file
    """
    return self.__config.sections()

  def keys(self, strsection):
    """
      function to get the list of the sections in the config file
    """
    if strsection not in self.__config.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return []
    return list( self.__config[ strsection ].keys() )
 
  def name(self):
    """
      function to get the input configure file name
    """
    return self.strname

