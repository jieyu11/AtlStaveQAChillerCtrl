"""
device class to read from / write to USB connected devices:
  chiller
  boost pump
  thermocouple couple
  humidity sensor
  IR camcera
"""
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
import logging
import ChillerRdConfig
from ChillerDevices import *       #real devices classes: Chiller Pump Humidity Thermocouple
from ChillerPseudoDevices import * #pseudo devices classes

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
          self.__dictDevices[ strDevName ] = clsChiller(strDevName, strPort, intBaud)
      elif strDevName == 'Pump':
        if bolRunPseudo == True: 
          self.__dictDevices[ strDevName ] = clsPseudoPump(strDevName)
        else:
          #!! self.__dictDevices[ strDevName ] = clsPump(strDevName, strPort, intBaud)
          self.__dictDevices[ strDevName ] = clsPseudoPump(strDevName)
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

