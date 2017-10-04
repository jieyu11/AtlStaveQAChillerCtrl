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
from CycRedundCheck import *

class clsDevice:
  def __init__(self, strname, strport, intbaud, bytesize, parity, stopbits, timeout):
    """
      function of initialization for any device
    """
    print ( ' Device name ' + strname + ' PORT ' + strport + ' baud ' + str(intbaud) )

    self.bolstatus = True
    self._pdev = serial.Serial( strport, intbaud) 
    self._pdev.bytesize = bytesize
    self._pdev.parity = parity
    self._pdev.stopbits = stopbits
    self._pdev.timeout = timeout
    # self._pdev.open()
    self.bolstatus = self._pdev.is_open # need to check the device status first

    self.strname = strname
    logging.info( 'Loading {:20s}'.format( strname ) + ' at port {:6s}'.format( strport ) + \
                  ' baudrate at {:6d}'.format( intbaud ) + ' status {:b}'.format( self.bolstatus) );

  def __str__(self):
    print( 'Device {:20s}'.format( strname ) + ' at port {:6s}'.format( strport ) + \
           ' baudrate at {:6d}'.format( intbaud ) + ' status {:b}'.format( self.bolstatus) );

  def read(self, strcmdname, strcmdpara=""):
    """
      function of reading device data
    """
    if strcmdpara == "" :
      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
    else:
      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + " with parameter " + strcmdpara )


class clsHumidity ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None):
    """
      Devide: HUMIDITY, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)

  def read(self, strcmdname, strcmdpara=""):
    """
      Humidity: function of reading data
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
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None, datapoints=1):
    """
      Device: Thermocouple, function of initialization
      datapoints: 1 -- 29; 
          29 data points are obtained each time, one can chose how many to write out.
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)
    self._datapoints = datapoints
    if datapoints < 1 :
      self._datapoints = 1
      logging.warning(' Cannot set data points to ' + str( datapoints ) + ' to ' + self.strname + '. Force it to 1.' )
    elif datapoints > 29 :
      self._datapoints = 29
      logging.warning(' Cannot set data points to ' + str( datapoints ) + ' to ' + self.strname + '. Force it to 29.' )
    # temperature data in 2D: [29][4]
    self._temperaturedata = []


  def read(self, strcmdname, strcmdpara=""):
    """
      Thermocouple: function of reading data
    """
    _intDataLines = 29 # 29 data measurements
    _intDataPoint =  4 # 4 thermocouple
    logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
    #self._pdev.write( (strcmdname + '\r\n').encode() )
    #should send HEX instead of a string
    self._pdev.write( bytes.fromhex(strcmdname) )

    print ('Start reading thermocouple reader!!! ' + strcmdname )
    # 734 bytes combining (head) + 29 lines of (data)
    # head: AA B2 80 00 00 76 01 00 AB
    # data: AA B1 80 00 00 76 01 00 13 02 00 07 12 02 00 21 11 02 00 09 66 02 00 43 AB
    # 
    # it takes about 25 seconds to read all these data
    # 
    
    _intTotalBytes = 734
    byteline = self._pdev.read( _intTotalBytes )
    strline = byteline.hex()
    # Response
    # AA B2 80 00 00 76 01 00 AB
    # AA B1 80 00 00 76 01 00 13 02 00 07 12 02 00 21 11 02 00 09 66 02 00 43 AB
    #                         (    T1   ) (    T2   ) (    T3   ) (    T4   )
    # ...
    # ...
    #     ---- 29 such data lines in total ----
    # ...
    # ...
    # NO "\n" or "\r" in the response, all in one line!!
    # To keep the result:
    # -- discard the first 17 bytes
    # -- use the next 4 x 4 bytes for T1 -- T4 temperatures
    # -- convert hex numbers into readable
 
    print ("got "+ strline)
    
    # skip the first 18 bytes
    idxbase = 18
    for Lidx in range( _intDataLines )
      
      # skip the first 16 bytes in each line
      idxbase = idxbase + 16

      strTall = ' Thermocouple data point ' + str(Lidx)
      for Tidx in range( _intDataPoint ) :
        strTval = strline[idxbase+2:idxbase+4] + strline[idxbase:idxbase+2] + strline[idxbase+6:idxbase+8] 
        #print (' THE value ' + strTval )
        Tval = int(strTval) / 1000
        strTall.append( ' T{:1d} value: {:6.3f}'.format((Tidx+1), Tval ) )

        # every read out has 8 bytes
        idxbase = idxbase + 8

      # skip the first 2 bytes at the end of each line
      idxbase = idxbase + 2

      print( strTall )
      logging.info( strTall )

    #byteline = self._pdev.readline()
    #strinclines =  byteline.hex()
    #print ("print all lines")
    #for index, strline in enumerate(strinclines.splitlines()) :
    #  print ('index ' + str(index) + ' line: ' + strline )


    #byteline = self._pdev.readline()
    #strinclines =  byteline.hex()
    #print (' read thermocouple: '+strinclines )
    #if self._pdev.inWaiting():
    #  print ('Device is waiting ')

    #byteline = self._pdev.read(10)
    #strline = byteline.hex()
    #print( ' READING current ' + self.strname + ' value: ' + strline  )
    #humval = int(strline[6:10], 16) / 10
    #logging.info( ' READING current ' + self.strname + ' value: {:4.1f}%'.format( humval )  )
    # TODO: do I need to return the value??
    #return humval

class clsChiller ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)


  def read(self, strcmdname, strcmdpara=""):
    """
      Chiller: function of reading data
    """
    if strcmdpara == "" :
      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
      self._pdev.write( (strcmdname + '\r\n').encode() )
    else :
      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + " with parameter " + strcmdpara)
      self._pdev.write( (strcmdname + strcmdpara + '\r\n').encode() )

    byteline = self._pdev.readline()
    strinclines =  byteline.decode()

    for index, strline in enumerate(strinclines.splitlines()) :
      if index ==0 and strline[0:2] == str('OK') : 
        logging.info( ' Device ' + self.strname + ' status OK ')
      elif index ==0 :
        logging.error(' Device ' + self.strname + ' Error status: ' + strline + '. Return! ' )
        return
      elif index == 1 :
        strvarname = strline[0:3]
        fltvarvalue = float( strline[5:-1] )

        if strvarname[0:1] != str('F') :
          logging.error( ' Device ' + self.strname + ' returned message: ' + strline + ' not recognized. Return!' )
          return

        logging.info( ' READING current ' + self.strname + ' value: %4.2f ' % fltvarvalue   )
        return
    # TODO: do I need to return the value??
    #return humval

class clsPump ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=1):
    """
      Device: boost pump, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)
    self.istCRC = CycRedundCheck()


  def read(self, strcmdname, strcmdpara=""):
    """
      Pump: function of reading data
    """
    if strcmdpara == "" : 
      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
      self._pdev.write( bytes.fromhex(strcmdname) )
    else :
      if strcmdname[-1:] == "=" :
        strcmdname = strcmdname[0:-1]

      print ("pump parameter: " + strcmdpara)
      intcmdpara = int(strcmdpara)
      if intcmdpara < 5 or intcmdpara > 25 :
        logging.warning( ' setting value ' + strcmdpara + ' is out of allowed range [5, 25] to device ' + self.strname )
        print( ' WARNING setting value ' + strcmdpara + ' is out of allowed range [5, 25] to device ' + self.strname )
        intcmdpara = 10
        strcmdpara = "10"

      logging.info( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + ' at parameter ' + strcmdpara )
      strcmdpara = '{:02x}'.format(intcmdpara) # should return a hex number with 015A...
      #strhexcmdpara = '{:02x}'.format(intcmdpara) # should return a hex number with \x01\x5A...
      strhexcmdpara = str( bytes.fromhex(strcmdpara) )
      #strhexcmdpara = strcmdpara.decode("hex")
      print ("looking good ? " + strhexcmdpara + " from " + strcmdpara )

      crc = 0xFFFF
      hexcrc = self.istCRC.calcString(strhexcmdpara, crc)
      print ('conver to string ' + str(hexcrc) )
      strhexcrc = format(hexcrc, 'x')
      print( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + ' at parameter in hex: ' + strcmdpara + " generated: " + strhexcrc )
      print ('SENDING : ' + strcmdname+strcmdpara+strhexcrc)

      self._pdev.write( bytes.fromhex(strcmdname+strcmdpara+strhexcrc) )

    byteline = self._pdev.readline()
    strline = byteline.hex()
    print( ' READING current ' + self.strname + ' value: ' + strline )
    logging.info( ' READING current ' + self.strname + ' value: ' + strline )