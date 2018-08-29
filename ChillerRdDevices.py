'''
  Program ChillerRdDevices.py
  
Description: ------------------------------------------------------------------
  This file contains the class construct to read/write to the USB connected
devices/equipment.  The list of devices/equipment:
  
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
    bol - boolean
  cls - class
  dict - dictionary
  ist - instance
  str - string

'''
# function __init__: 
#   initialize the class device
#   should include Configure Instance as input???
# function read( strCmdName ):
#   provide the command name
#   return information from the device
# function write( strCmdName ):
#   provide the command name
#   write to device if necessary
#   e.g. change Chiller setup temperature
# function getdevice( strDevName ):
#   provide device name
#   return the device instance
#
#

# Import Section --------------------------------------------------------------
import logging                     # Flexible event logging functions/classes.

#User defined classes
import ChillerRdConfig             # Module with device configuration data.
from ChillerDevices import *       #real devices classes: Chiller, Pump, Humidity, Thermocouple
from ChillerPseudoDevices import * # Pseudo device classes for testing code.
from ArduinoDevice import *        #The arduino process

# -----------------------------------------------------------------------------
class clsDevicesHandler:
  def __init__(self, istConfig, strDevNameList, bolRunPseudo):
    """
      function initialization of devices handler
      read in configuration
      load all possible devices
    """ 
    # private configuration instance
    self.__istConfig = istConfig

    # use a dictionary to keep the instances of devices
    self.__dictDevices = {}
    for strDevName in istConfig.sections() : 
      # a device should have a connected port (lower case!)
      # otherwise skip the section, not device

      if strDevNameList is not None  and  strDevName not in strDevNameList: 
        logging.debug('Devices Handler: ' + strDevName + ' skipped. ')
        continue;

      if 'port' not in istConfig.keys( strDevName ) :
        continue

      #print ('Device name: ' + strDevName )
      strPort = istConfig.get(strDevName, 'Port')
      intBaud = int( istConfig.get(strDevName, 'Baud'))
      if strDevName == 'Chiller':
        if bolRunPseudo == True: 
          self.__dictDevices[ strDevName ] = clsPseudoChiller(strDevName)
        else:
          #self.__dictDevices[ strDevName ] = clsPseudoChiller(strDevName)
          self.__dictDevices[ strDevName ] = clsChiller(strDevName, strPort, intBaud)
      elif strDevName == 'Pump':
        if bolRunPseudo == True: 
          self.__dictDevices[ strDevName ] = clsPseudoPump(strDevName)
        else:
          self.__dictDevices[ strDevName ] = clsPseudoPump(strDevName)
          #self.__dictDevices[ strDevName ] = clsPump(strDevName, strPort, intBaud)
      elif strDevName == 'Humidity':
        if bolRunPseudo == True: 
          self.__dictDevices[ strDevName ] = clsPseudoHumidity(strDevName)
        else:
          self.__dictDevices[ strDevName ] = clsHumidity(strDevName, strPort, intBaud)
      elif strDevName == 'Thermocouple':
        if bolRunPseudo == True: 
          self.__dictDevices[ strDevName ] = clsPseudoThermocouple(strDevName)
        else:
          self.__dictDevices[ strDevName ] = clsThermocouple(strDevName, strPort, intBaud)
      elif strDevName == 'Arduino':
        if bolRunPseudo == True:
          self.__dictDevices[strDevName] = clsPseudoArduino(strDevName)
        else:
          self.__dictDevices[strDevName] = clsArduino(strDevName, strPort, intBaud)
      else:
        logging.error( ' Device name: ' + strDevName + ' not found! ')

  def readdevice(self, strDevName, strCmdName, strCmdPara,fltCurrentTemps) :
    """
      function to read from one of the devices through device name
      and command name
    """
    self.__dictDevices[ strDevName ].read( strCmdName, strCmdPara,fltCurrentTemps) 

  def getdevice(self, strDevName) :
    """
      function to get the instance of the device by providing
      device's name
    """
    if strDevName in self.__dictDevices :
      return self.__dictDevices[ strDevName ]
    else :
      logging.error( 'Device name ' + strDevName + ' not found. ' );
      logging.error( '    The possible devices names are: ' );
      for key in self.__dictDevices : 
        logging.error( '     ' + key );
      return None

  def getdevicenames(self) :
    """
      function to get the list of device names that have been registered
    """
    return tuple ( self.__dictDevices.keys() )

