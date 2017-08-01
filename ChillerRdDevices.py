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
# function read:
#   read information from the device
# function write:
#   write to device if necessary
#   e.g. change Chiller setup temperature

# need to install it: pip3.6 install pyserial
import serial
import time
import logging

class clsDevice:
  def __init__(self, strname, strport, intbaud):
    """
      function of initialization
    """
    ########self.__pdev = serial.Serial( strport, intbaud) 
    # for example: serial.Serial("/dev/tty.usbserial-A400DUTI", 9600)
    self.bolstatus = True # need to check the device status first
    self.strname = strname
    logging.info( 'Loading ' + strname + ' at port ' + strport + ' baudrate at {:6d}'.format( intbaud ) );

  def getname(self):
    return self.strname

  def read(self):
    """
      function of reading device data
    """
    # tmp: return a random number
    return random.random();

    ##strline = __pdev.readline()
    ##try:
    ##  chrfirst = strline[0]
    ##except IndexError:  # got no data from sensor
    ##  break
    ##else:
    ##  if chrfirst == '@':  # begins a new sensor record
    ##    self.bolstatus = True
    ##  elif chrfirst == '$':
    ##    self.bolstatus = False
    ##  else:
    ##    print("Unexpected character at the start of the line:\n{}".format(line))
    ##  time.sleep(2)
    ##return strline

  def write(self):
    """
      function of writing to device
    """
    # format: https://pyformat.info/
    logging.info( strname + ' {:6.2f}'.format( self.read() ) );

class clsDevicesHandler:
  def __init__(self, istConfig):
    """
      function initialization of devices handler
      read in configuration
      load all possible devices
    """ 
    # private configuration instance
    self.__istConfig = istConfig
    # should check all the devices' status right after they are loaded
    # can the names of the devices be read out from the configuration as well?
    # OR let the configuration tell what are the devices needs to be loaded 
    #__istDevices__ = []
    #for strsecname in istConfig.sections(): 
    #  #__istDevices__ += clsDevice(strsecname, istConfig[ strsecname ]['Port'], int( istConfig[ strsecname ]['Baud']) )
    if 'Chiller' in istConfig:
      self.__istChiller__ = clsDevice('chiller', istConfig['Chiller']['Port'], int( istConfig['Chiller']['Baud']) )
    if 'Pump' in istConfig:
      self.__istBoostPump__ = clsDevide('boostpump', istConfig['Pump']['Port'], int( istConfig['Pump']['Baud']) )
    if 'Humidity' in istConfig:
      self.__istHumidity__ = clsDevice('huimidity', istConfig['Humidity']['Port'], int( istConfig['Humidity']['Baud']) )
    if 'Thermocouple' in istConfig:
      self.__istThermocouple__ = clsDevice('thermocouple', istConfig['Thermocouple']['Port'], int( istConfig['Thermocouple']['Baud']) )
    

  ##def loaddevices():
  ##  """
  ##    function of loading all devices used in the measurement
  ##  """

