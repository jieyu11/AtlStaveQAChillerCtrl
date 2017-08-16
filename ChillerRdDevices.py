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
import serial
import time
import logging
import ChillerRdConfig

class clsDevice:
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None):
    """
      function of initialization
    """
    print (' NAME ' + strname + ' PORT ' + strport + ' baud ' + str(intbaud) )

    self.bolstatus = True
    if str('Humidity') == strname:
      print ( ' loading Humidity ' )
      self.__pdev = serial.Serial( strport, intbaud) 
      self.__pdev.bytesize = bytesize
      self.__pdev.parity = parity
      self.__pdev.stopbits = stopbits
      self.__pdev.timeout = timeout
      # self.__pdev.open()
      self.bolstatus = self.__pdev.is_open # need to check the device status first

    self.strname = strname
    logging.info( 'Loading {:20s}'.format( strname ) + \
                  ' at port {:6s}'.format( strport ) + \
                  ' baudrate at {:6d}'.format( intbaud ) + \
                  ' status {:b}'.format( self.bolstatus) );

  def read(self, strcmdname):
    """
      function of reading device data
    """

    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )

    if str('Humidity') == self.strname:

      # TODO: here should test if the device is connected already!!!

      self.__pdev.write( (strcmdname + '\r\n').encode() )
      #strline = self.__pdev.readline()
      byteline = self.__pdev.read(10)
      #print ( '   get output type: ' + type(strline)  )
      print (type(byteline))
      #strline = byteline.decode(encoding='UTF-8')
      #strline = byteline.decode(encoding='windows-1252')
      #strline = "".join(map(chr, byteline))
      strline = byteline.hex()
      logging.info( '   get output in hex: ' + strline  )

      # TODO: need to return the value obtained.


  def write(self, strcmdname):
    """
      function of writing to device
    """
    # format: https://pyformat.info/
    logging.info( ' WRITING: Sending command ' + strcmdname + ' to device ' + self.strname )

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
      self.__dictDevices[ strdevname ] = clsDevice(strdevname, istConfig.get(strdevname, 'Port'), int( istConfig.get(strdevname, 'Baud')) )

  def readdevice(self, strdevname, strcmdname) :
    """
      function to read from one of the devices through device name
      and command name
    """
    self.__dictDevices[ strdevname ].read( strcmdname )

  def writedevice(self, strdevname, strcmdname) :
    """
      function to write to one of the devices through device name
      and command name
    """
    self.__dictDevices[ strdevname ].write( strcmdname )

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
