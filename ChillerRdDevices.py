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
# function read( strcmdname ):
#   provide the command name
#   return information from the device
# function write( strcmdname ):
#   provide the command name
#   write to device if necessary
#   e.g. change Chiller setup temperature
# function getdevice( strdevname ):
#   provide device name
#   return the device instance
#
#
# need to install it: pip3.6 install pyserial
import logging
import ChillerRdConfig
from ChillerDevices import *
#clsChiller clsPump clsHumidity clsThermocouple
class clsDevicesHandler:
  def __init__(self, istConfig):
    """
      function initialization of devices handler
      read in configuration
      load all possible devices
    """ 
    # private configuration instance
    self.__istConfig = istConfig

    # use a dictionary to keep the instances of devices
    self.__dictDevices = {}
    for strdevname in istConfig.sections() : 
      # a device should have a connected port (lower case!)
      # otherwise skip the section, not device
      if 'port' not in istConfig.keys( strdevname ) :
        continue

      strPort = istConfig.get(strdevname, 'Port')
      intBaud = int( istConfig.get(strdevname, 'Baud'))
      if strdevname == 'Chiller':
        self.__dictDevices[ strdevname ] = clsChiller(strdevname, strPort, intBaud)
      elif strdevname == 'Pump':
        self.__dictDevices[ strdevname ] = clsPump(strdevname, strPort, intBaud)
      elif strdevname == 'Humidity':
        self.__dictDevices[ strdevname ] = clsHumidity(strdevname, strPort, intBaud)
      elif strdevname == 'Thermocouple':
        self.__dictDevices[ strdevname ] = clsThermocouple(strdevname, strPort, intBaud)
      else:
        logging.error( ' Device name: ' + strdevname + ' not found! ')

  def readdevice(self, strdevname, strcmdname, strcmdpara) :
    """
      function to read from one of the devices through device name
      and command name
    """
    self.__dictDevices[ strdevname ].read( strcmdname, strcmdpara)

  def getdevice(self, strdevname) :
    """
      function to get the instance of the device by providing
      device's name
    """
    if strdevname in self.__dictDevices :
      return self.__dictDevices[ strdevname ]
    else :
      logging.error( 'Device name ' + strdevname + ' not found. ' );
      logging.error( '    The possible devices names are: ' );
      for key in self.__dictDevices : 
        logging.error( '     ' + key );
      return None

  def getdevicenames(self) :
    """
      function to get the list of device names that have been registered
    """
      return tuple( self.__dictDevices.keys() )

