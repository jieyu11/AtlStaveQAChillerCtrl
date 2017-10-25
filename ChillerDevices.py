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

import serial  # https://github.com/pyserial/pyserial, install: pip3.6 install pyserial
import time
import logging
from CycRedundCheck import *

# ------------------------------------------------------------------------------
# Class Device (base) ----------------------------------------------------------
# Serve as base class for specific devices 
#
class clsDevice:
  def __init__(self, strname, strport, intbaud, bytesize, parity, stopbits, timeout):
    """
      function of initialization for any device
    """
    logging.info( ' Initialization Device, name ' + strname + ' PORT ' + strport + ' baud ' + str(intbaud) + \
                  ' bytesize ' + str(bytesize) + ' parity ' + str( parity ) + ' stopbits ' + str( stopbits ) + \
                  ' timeout ' + str(timeout) )

    self._strclassname = ' < Device > '

    self._bolopened = True
    self._pdev = serial.Serial( strport, intbaud) 
    self._pdev.bytesize = bytesize
    self._pdev.parity = parity
    self._pdev.stopbits = stopbits
    self._pdev.timeout = timeout
    # self._pdev.open()
    self._bolopened = self._pdev.is_open # need to check the device status first

    self.strname = strname
    logging.info( 'Loading {:20s}'.format( strname ) + ' at port {:6s}'.format( strport ) + \
                  ' baudrate at {:6d}'.format( intbaud ) + ' status {:b}'.format( self._bolopened) );

  def __str__(self):
    print( 'Device {:20s}'.format( strname ) + ' at port {:6s}'.format( strport ) + \
           ' baudrate at {:6d}'.format( intbaud ) + ' status {:b}'.format( self._bolopened) );

  def read(self, strcmdname, strcmdpara=""):
    """
      function of reading device data
    """
    if strcmdpara == "" :
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self.strname )
    else:
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self.strname + " with parameter " + strcmdpara )

  def last(self) :
    """
      function to get the last read out value(s)
    """
    return 0


# ------------------------------------------------------------------------------
# Class Humidity (inherited Device) --------------------------------------------
class clsHumidity ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None):
    """
      Devide: Humidity, function of initialization
    """


    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)

    self._strclassname = ' < Humidity > '

    # keep the last read out value, initialized with 100%
    self._value = 100

  def read(self, strcmdname, strcmdpara=""):
    """
      Humidity: function of reading data
    """
    logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self.strname )

    if self._bolopened is False: 
      logging.error( self._strclassname + ' device ' + self.strname + ' is still closed! Return! ' )
      return

    self._pdev.write( (strcmdname + '\r\n').encode() )

    # read 10 bits
    byteline = self._pdev.read(10)
    strline = byteline.hex()
    logging.debug( ' READING current ' + self.strname + ' value: ' + strline  )
    humval = int(strline[6:10], 16) / 10
    self._value = humval
    #logging.info( ' READING current ' + self.strname + ' value: {:4.1f}%'.format( humval )  )
    # TODO: do I need to return the value??
    #return humval

  def last(self) : 
    return self._value

# ------------------------------------------------------------------------------
# Class Thermocouple (inherited Device) ----------------------------------------
class clsThermocouple ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=None, ndataread=1):
    """
      Device: Thermocouple, function of initialization
      ndataread: 1 -- 29; 
          29 data points are obtained each time, one can chose how many to write out.
    """

    self._strclassname = ' < Thermo > '

    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)
    self._intDataLines = 29 # 29 data measurements
    self._intDataPoint =  4 # 4 thermocouple
    self._ndataread = ndataread
    if ndataread < 1 :
      self._ndataread = 1
      logging.warning(' Cannot set data points to ' + str( ndataread ) + ' to ' + self.strname + '. Force it to 1.' )
    elif ndataread > 29 :
      self._ndataread = 29
      logging.warning(' Cannot set data points to ' + str( ndataread ) + ' to ' + self.strname + '. Force it to 29.' )
    # temperature data in 2D: [29][4]
    # initialized with 0. refer as [i][j]
    self._temperaturedata =  [[0 for x in range( self._intDataPoint )] for y in range( self._intDataLines )]


  def read(self, strcmdname, strcmdpara=""):
    """
      Thermocouple: function of reading data
    """
    logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
    #self._pdev.write( (strcmdname + '\r\n').encode() )
    #should send HEX instead of a string
    self._pdev.write( bytes.fromhex(strcmdname) )

    #print ('Start reading thermocouple reader!!! ' + strcmdname )
    # 734 bytes combining (head) + 29 lines of (data)
    # head: AA B2 80 00 00 76 01 00 AB
    # data: AA B1 80 00 00 76 01 00 13 02 00 07 12 02 00 21 11 02 00 09 66 02 00 43 AB
    # 
    # it takes about 25 seconds to read all these data
    # 
    
    _intTotalBytes = 734
    byteline = self._pdev.read( _intTotalBytes )
    strline = byteline.hex()

    #
    # Response: 
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
 
    logging.debug ("got "+ strline)
    
    # skip the first 18 bytes
    idxbase = 18
    for Lidx in range( self._intDataLines ) :
      
      # skip the first 16 bytes in each line
      idxbase = idxbase + 16

      strTall = '<DATA> ThermoDaPt ' + str(Lidx)
      for Tidx in range( self._intDataPoint ) :
        strTval = strline[idxbase+2:idxbase+4] + strline[idxbase:idxbase+2] + strline[idxbase+6:idxbase+8] 
        #print (' THE value ' + strTval )
        Tval = int(strTval) / 1000
        self._temperaturedata[ Lidx ][ Tidx ] = Tval

        #strTall.append( ' T{:1d} value: {:6.3f}'.format((Tidx+1), Tval ) )
        strTall += ' T{:1d}: {:6.3f}'.format((Tidx+1), Tval ) 

        # every read out has 8 bytes
        idxbase = idxbase + 8

      # skip the first 2 bytes at the end of each line
      idxbase = idxbase + 2

      #print( strTall )
      logging.info( strTall )

  def last(self, lineIdx = 0) :
    """
      function to read the last obtained result
      there are total of 29 readouts, define for which one to read
    """
    if lineIdx < 0 :
      logging.warning( ' data line index ' + str(lineIdx) + ' < 0!! set to 0. ' )
      lineIdx = 0
    elif lineIdx >= self._intDataPoint :
      logging.warning( ' data line index ' + str(lineIdx) + ' >= ' + str(self._intDataPoint) + \
                       '!! set to ' + str(self._intDataPoint - 1) + '.' )
      lineIdx = self._intDataPoint - 1

    return tuple( self._temperaturedata[lineIdx] )

class clsChiller ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)

    self._strclassname = ' < Chiller > '

    # keep the last read out value
    self._value = 0


  def read(self, strcmdname, strcmdpara=""):
    """
      Chiller: function of reading data
    """
    if strcmdpara == "" :
      logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
      self._pdev.write( (strcmdname + '\r\n').encode() )
    else :
      logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + " with parameter " + strcmdpara)
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

        self._value = fltvarvalue

        logging.info( ' READING current ' + self.strname + ' value: %4.2f ' % fltvarvalue   )
        return

  def last(self) :
    return self._value

class clsPump ( clsDevice ):
  def __init__(self, strname, strport, intbaud, bytesize=8, parity='N', stopbits=1, timeout=1):
    """
      Device: boost pump, function of initialization
    """
    super().__init__(strname, strport, intbaud, bytesize, parity, stopbits, timeout)
    self.istCRC = CycRedundCheck()
    self._value = 0


  def read(self, strcmdname, strcmdpara=""):
    """
      Pump: function of reading data
    """
    if strcmdpara == "" : 
      logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname )
      self._pdev.write( bytes.fromhex(strcmdname) )
      logging.debug( ' READING: ' + strcmdname + ' COMMAND sent ' )

    else :
      if strcmdname[-1:] == "=" :
        strcmdname = strcmdname[0:-1]

      logging.debug ("pump parameter: " + strcmdpara)
      fltcmdpara = float(strcmdpara) # e.g. 22.5
      if fltcmdpara < 5 or fltcmdpara > 25 :
        logging.warning( ' setting value ' + strcmdpara + ' is out of allowed range [5, 25] to device ' + self.strname )
        #print( ' WARNING setting value ' + strcmdpara + ' is out of allowed range [5, 25] to device ' + self.strname )
        fltcmdpara = 10

      intcmdpara = int( 10 * fltcmdpara )
      logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + ' at parameter ' + strcmdpara )
      strcmdpara = '{:04x}'.format(intcmdpara) # should return a hex number with 015A...
      strcmdpara = strcmdpara.upper()

      logging.debug ('GOT command name ' + strcmdname)

      strcmdnamepara = strcmdname + strcmdpara

      logging.debug (" READING " + self.strname + " converting from " + strcmdnamepara + " with length " + str(len(strcmdnamepara)) )

      strhexcmdnamepara = bytearray.fromhex( strcmdnamepara )
      # 'cp1252' windows default encoding
      strhexcmdnamepara = str( strhexcmdnamepara.decode('cp1252') )


      logging.debug ('SEND command parameters for conversion ' + str(strhexcmdnamepara) )
      crc = 0xFFFF

      ##! OK!! strhexcmdnamepara = "\x01\x06\x00\x2C\x00\xdc" #This is what must be sent to the following line to give the correct
      ##! CRC value to change the pump to 22 RPM

      hexcrc = self.istCRC.calcString( strhexcmdnamepara, crc)
      logging.debug ('conver to string ' + str(hexcrc) )
      strhexcrc = format(hexcrc, '04x')
      strhexcrc = strhexcrc[2:] + strhexcrc[0:2]
      logging.debug( ' READING: Sending command ' + strcmdname + ' to device ' + self.strname + ' at parameter in hex: ' + strcmdpara + " generated: " + strhexcrc )
      logging.debug ('SENDING : ' + strcmdname +strcmdpara.upper() +strhexcrc.upper() )

      self._pdev.write( bytes.fromhex(strcmdname +strcmdpara.upper() +strhexcrc.upper() ) )


    logging.debug( ' READING ' + self.strname + ' commend sent ' )
    byteline = self._pdev.readline()
    logging.debug( ' READING ' + self.strname + ' line obtained with bytes ' )
    strline = byteline.hex()
    logging.debug( ' READING ' + self.strname + ' line obtained ' + strline )
    #print( ' READING current ' + self.strname + ' value: ' + strline )
    logging.debug( ' READING current ' + self.strname + ' value: ' + strline )

    # TODO: setting pump values OK???
    self._value =  strline

  def last(self) : 
    return self._value
