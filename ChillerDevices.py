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
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      function of initialization for any device
    """
    print ( ' NAME ' + strname + ' PORT ' + strport + ' baud ' + str(intbaud) )
    print ( ' loading Device ' + strname )

    self.bolstatus = True
    self._pdev = serial.Serial( strport, intbaud) 
    self._pdev.bytesize = bytesize
    self._pdev.parity = parity
    self._pdev.stopbits = stopbits
    self._pdev.timeout = timeout
    # self._pdev.open()
    self.bolstatus = self._pdev.is_open # need to check the device status first

    self.strname = strname
    logging.info( 'Loading {:20s}'.format( strname ) + \
                  ' at port {:6s}'.format( strport ) + \
                  ' baudrate at {:6d}'.format( intbaud ) + \
                  ' status {:b}'.format( self.bolstatus) );
  def __str__(self):
    print( 'Device {:20s}'.format( strname ) + \
           ' at port {:6s}'.format( strport ) + \
           ' baudrate at {:6d}'.format( intbaud ) + \
           ' status {:b}'.format( self.bolstatus) );

  def read(self, strcmdname):
    """
      function of reading device data
    """
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )

class clsHumidity ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None):
    """
      Devide: HUMIDITY, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)

  def read(self, strcmdname):
    """
      function of reading device data
    """
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
    # TODO: here should test if the device is connected already!!!
    self._pdev.write( (strcmdname + '\r\n').encode() )
    # read 10 bits
    byteline = self._pdev.read(10)
    strline = byteline.hex()
    print( ' READING current ' + self.strname + ' value: ' + strline  )
    humval = int(strline[6:10], 16) / 10
    logging.info( ' READING current ' + self.strname + ' value: {:4.1f}%'.format( humval )  )
    # TODO: do I need to return the value??
    #return humval

class clsThermocouple ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)


  def read(self, strcmdname):
    """
      function of reading device data
    """
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )

class clsChiller ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)


  def read(self, strcmdname):
    """
      function of reading device data
    """
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
    self._pdev.write( (strcmdname + '\r\n').encode() )
    logging.info(' Device ' + self.strname + ' command ' + strcmdname)

    byteline = self._pdev.readline()
    strinclines =  byteline.decode()

    for index, strline in enumerate(strinclines.splitlines()) :
      if index ==0 and strline[0:2] == str('OK') : 
        logging.info( ' Device ' + self.strname + ' status OK ')
      elif index ==0 :
        logging.error(' Device ' + self.strname + ' Error status: ' + strline + '. Return! ' )
        return
      elif index == 1 :
        if strvarname[0:1] != str('F') :
          logging.error( ' Device ' + self.strname + ' returned message: ' + strline + ' not recognized. Return!' )
          return

        strvarname = strline[0:3]
        fltvarvalue = float( strline[5:-1] )

        logging.info( ' READING current ' + self.strname + ' value: %4.2f ' % fltvarvalue   )
        return
    # TODO: do I need to return the value??
    #return humval

class clsPump ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: boost pump, function of initialization for any device
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)


  def read(self, strcmdname):
    """
      function of reading device data
    """
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )

