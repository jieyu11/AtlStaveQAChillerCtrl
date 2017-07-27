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

import serial
import time

class clsDevice:
  def __init__(self, strname, strportId):
  """
    function of initialization
  """
    self.__pdev = serial.Serial( strportId, 9600) 
    # for example: serial.Serial("/dev/tty.usbserial-A400DUTI", 9600)
    self.bolstatus = True # need to check the device status first
    self.strname = strname

  def read(self):
  """
    function of reading device data
  """
    strline = __pdev.readline()
    try:
      chrfirst = strline[0]
    except IndexError:  # got no data from sensor
      break
    else:
      if chrfirst == '@':  # begins a new sensor record
        self.bolstatus = True
      elif chrfirst == '$':
        self.bolstatus = False
      else:
        print("Unexpected character at the start of the line:\n{}".format(line))
      time.sleep(2)
    return strline

  def write(self, writable):
  """
    function of writing to device
  """

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
    self.__istChiller__ = clsDevice("chiller", istConfig.usbport("chiller") );
    self.__istBoostPump__ = clsDevide("boostpump", stConfig.usbport("boostpump") );
    # ... all the rest ...

  def loaddevices():
  """
    function of loading all devices used in the measurement
  """

