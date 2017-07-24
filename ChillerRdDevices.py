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

class device:
  def __init__(self, name, portId):
  """
    function of initialization
  """
    self.__pdev = serial.Serial(portId, 9600) 
    # for example: serial.Serial("/dev/tty.usbserial-A400DUTI", 9600)
    self.status = True # need to check the device status first
    self.name = name

  def read(self):
  """
    function of reading device data
  """
    line = __pdev.readline()
    try:
      first_char = line[0]
    except IndexError:  # got no data from sensor
      break
    else:
      if first_char == '@':  # begins a new sensor record
        self.status = True
      elif first_char == '$':
        self.status = False
      else:
        print("Unexpected character at the start of the line:\n{}".format(line))
      time.sleep(2)
    return line

  def write(self, writable):
  """
    function of write to device
  """

