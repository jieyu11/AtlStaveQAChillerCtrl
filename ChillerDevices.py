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

import serial  # https://github.com/pyserial/pyserial, install: pip3.6 install pyserial
import time
import logging
from CycRedundCheck import *

# ------------------------------------------------------------------------------
# Class Device (base) ----------------------------------------------------------
# Serve as base class for specific devices 
#
class clsDevice:
  def __init__(self, strName, strPort, intBaud, bytesize, parity, stopbits, timeout):
    """
      function of initialization for any device
    """
    logging.info( ' Initialization Device, name ' + strName + ' PORT ' + strPort + ' baud ' + str(intBaud) + \
                  ' bytesize ' + str(bytesize) + ' parity ' + str( parity ) + ' stopbits ' + str( stopbits ) + \
                  ' timeout ' + str(timeout) )

    self._strClassName = ' < Device > '

    self._bolOpened = True
    self._pdev = serial.Serial( strPort, intBaud) 
    self._pdev.bytesize = bytesize
    self._pdev.parity = parity
    self._pdev.stopbits = stopbits
    self._pdev.timeout = timeout
    # self._pdev.open()
    self._bolOpened = self._pdev.is_open # need to check the device status first

    self.strName = strName
    logging.info( 'Loading {:20s}'.format( strName ) + ' at port {:6s}'.format( strPort ) + \
                  ' baudrate at {:6d}'.format( intBaud ) + ' status {:b}'.format( self._bolOpened) );

  def __str__(self):
    print( 'Device {:20s}'.format( strName ) + ' at port {:6s}'.format( strPort ) + \
           ' baudrate at {:6d}'.format( intBaud ) + ' status {:b}'.format( self._bolOpened) );

  def read(self, strCmdName, strCmdPara="",fltCurrentTemps=[]):
    """
      function of reading device data
    """
    if strCmdPara == "" :
      logging.debug( self._strClassName + ' Sending command ' + strCmdName + ' to device ' + self.strName )
    else:
      logging.debug( self._strClassName + ' Sending command ' + strCmdName + ' to device ' + self.strName + " with parameter " + strCmdPara )

  def last(self) :
    """
      function to get the last read out value(s)
    """
    return 0


# ------------------------------------------------------------------------------
# Class Humidity (inherited Device) --------------------------------------------
class clsHumidity ( clsDevice ):
  def __init__(self, strName, strPort, intBaud, bytesize=8, parity='N', stopbits=1, timeout=None):
    """
      Devide: Humidity, function of initialization
    """


    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)

    self._strClassName = ' < Humidity > '

    # keep the last read out value, initialized with 100%
    self._value = 100

  def read(self, strCmdName, strCmdPara="",fltCurrentTemps=[]):
    """
      Humidity: function of reading data
    """
    logging.debug( self._strClassName + ' Sending command ' + strCmdName + ' to device ' + self.strName )

    if self._bolOpened is False: 
      logging.error( self._strClassName + ' device ' + self.strName + ' is still closed! Return! ' )
      return

    self._pdev.write( (strCmdName + '\r\n').encode() )

    # read 10 bits
    byteline = self._pdev.read(10)
    strLine = byteline.hex()
    logging.debug( ' READING current ' + self.strName + ' value: ' + strLine  )
    humval = int(strLine[6:10], 16) / 10
    self._value = humval
    #logging.info( ' READING current ' + self.strName + ' value: {:4.1f}%'.format( humval )  )
    # TODO: do I need to return the value??
    #return humval

  def last(self) : 
    return self._value

# ------------------------------------------------------------------------------
# Class Thermocouple (inherited Device) ----------------------------------------
class clsThermocouple ( clsDevice ):
  def __init__(self, strName, strPort, intBaud, bytesize=8, parity='N', stopbits=1, timeout=None, ndataread=1):
    """
      Device: Thermocouple, function of initialization
      ndataread: 1 -- 29; 
          29 data points are obtained each time, one can chose how many to write out.
    """

    self._strClassName = ' < Thermo > '

    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)
    self._intDataLines = 29 # 29 data measurements
    self._intDataPoint =  4 # 4 thermocouple
    self._ndataread = ndataread
    if ndataread < 1 :
      self._ndataread = 1
      logging.warning(' Cannot set data points to ' + str( ndataread ) + ' to ' + self.strName + '. Force it to 1.' )
    elif ndataread > 29 :
      self._ndataread = 29
      logging.warning(' Cannot set data points to ' + str( ndataread ) + ' to ' + self.strName + '. Force it to 29.' )
    # temperature data in 2D: [29][4]
    # initialized with 0. refer as [i][j]
    self._temperaturedata =  [[0 for x in range( self._intDataPoint )] for y in range( self._intDataLines )]


  def read(self, strCmdName, strCmdPara="",fltCurrentTemps=[]):
    """
      Thermocouple: function of reading data
    """
    logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName )
    #self._pdev.write( (strCmdName + '\r\n').encode() )
    #should send HEX instead of a string
    self._pdev.write( bytes.fromhex(strCmdName) )

    #print ('Start reading thermocouple reader!!! ' + strCmdName )
    # 734 bytes combining (head) + 29 lines of (data)
    # head: AA B2 80 00 00 76 01 00 AB
    # data: AA B1 80 00 00 76 01 00 13 02 00 07 12 02 00 21 11 02 00 09 66 02 00 43 AB
    # 
    # it takes about 25 seconds to read all these data
    # 
    
    _intTotalBytes = 734
    byteline = self._pdev.read( _intTotalBytes )
    strLine = byteline.hex()

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
 
    logging.debug ("got "+ strLine)
    
    # skip the first 18 bytes
    idxbase = 18
    for Lidx in range( self._intDataLines ) :
      
      # skip the first 16 bytes in each line
      idxbase = idxbase + 16

      strTall = '<DATA> ThermoDaPt ' + str(Lidx)
      for Tidx in range( self._intDataPoint ) :
        strTval = strLine[idxbase+2:idxbase+4] + strLine[idxbase:idxbase+2] + strLine[idxbase+6:idxbase+8] 
        strTsign = strLine[idxbase+4:idxbase+6]
        if strTsign == '10':
          fltTsign = -1
        else:
          fltTsign = 1
        #print (' THE value ' + strTval )
        Tval = int(strTval) / 1000 * fltTsign
        self._temperaturedata[ Lidx ][ Tidx ] = Tval

        #strTall.append( ' T{:1d} value: {:6.3f}'.format((Tidx+1), Tval ) )
        strTall += ' T{:1d}: {:6.3f}'.format((Tidx+1), Tval ) 

        # every read out has 8 bytes
        idxbase = idxbase + 8

      # skip the first 2 bytes at the end of each line
      idxbase = idxbase + 2

      #print( strTall )
      #logging.info( strTall )

  def last(self, lineIdx = 0) :
    """
      function to read the last obtained result
      there are total of 29 readouts, define for which one to read
    """
    if lineIdx < 0 :
      logging.warning( ' data line index ' + str(lineIdx) + ' < 0!! set to 0. ' )
      lineIdx = 0
    elif lineIdx >= self._intDataLines :
      logging.warning( ' data line index ' + str(lineIdx) + ' >= ' + str(self._intDataLines) + \
                       '!! set to ' + str(self._intDataLines - 1) + '.' )
      lineIdx = self._intDataLines - 1

    return tuple( self._temperaturedata[lineIdx] )

class clsChiller ( clsDevice ):
  def __init__(self, strName, strPort, intBaud, bytesize=8, parity='N', stopbits=1, timeout=2):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)

    self._strClassName = ' < Chiller > '

    # keep the last read out value
    self._value = 0


  def read(self, strCmdName, strCmdPara="",fltCurrentTemps=[]):
    """
      Chiller: function of reading data
    """
    if strCmdPara == "" :
      logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName )
      self._pdev.write( (strCmdName + '\r\n').encode() )
    else :
      logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName + " with parameter " + strCmdPara)
      self._pdev.write( (strCmdName + strCmdPara + '\r\n').encode() )

    byteline = self._pdev.readline()
    strinclines =  byteline.decode()


    for index, strLine in enumerate(strinclines.splitlines()) :

      if index ==0 and strLine[0:2] == str('OK') : 
        logging.debug( ' Device ' + self.strName + ' status OK ')
      elif index ==0 :
        logging.fatal(' Device ' + self.strName + ' Response from Chiller: ' + strLine + '. FATAL! ' )
        raise ValueError("A Problem Occured")
      elif index == 1 :
        strvarname = strLine[0:3]
        fltvarvalue = float( strLine[5:-1] )

        if strvarname[0:1] != str('F') :
          logging.fatal( ' Device ' + self.strName + ' returned message: ' + strLine + ' not recognized. FATAL!' )
          raise ValueError("A Problem Occured")
        self._value = fltvarvalue
        if fltvarvalue > 0:
          logging.fatal( ' Device ' + self.strName + ' has given alarm: ' +str(fltvarvalue)) 
          raise ValueError("ALARM IS GOING OFF")
        #logging.info(str(fltvarvalue))
        #logging.info( ' READING current ' + self.strName + ' value: %4.2f ' % fltvarvalue   )
        return

  def last(self) :
    return self._value

class clsPump ( clsDevice ):
  def __init__(self, strName, strPort, intBaud, bytesize=8, parity='N', stopbits=1, timeout=1):
    """
      Device: boost pump, function of initialization
    """
    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)
    self.istCRC = CycRedundCheck()
    self._value = 0


  def read(self, strCmdName, strCmdPara="",fltCurrentTemps=[]):
    """
      Pump: function of reading data
    """
    #logging.info(' ==== Pump read through ' + strCmdName + ' and parameter: ' + strCmdPara)
    if strCmdPara == "" : 
      logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName )
      self._pdev.write( bytes.fromhex(strCmdName))
      logging.debug( ' READING: ' + strCmdName + ' COMMAND sent ' )

    else :
      if strCmdName[-1:] == "=" :
        strCmdName = strCmdName[0:-1]

      logging.debug ("pump parameter: " + strCmdPara)
      fltCmdPara = float(strCmdPara) # e.g. 22.5
      if fltCmdPara < 5 or fltCmdPara > 25 :
        logging.warning( ' setting value ' + strCmdPara + ' is out of allowed range [5, 25] to device ' + self.strName )
        #print( ' WARNING setting value ' + strCmdPara + ' is out of allowed range [5, 25] to device ' + self.strName )
        fltCmdPara = 10

      intcmdpara = int( 10 * fltCmdPara )
      logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName + ' at parameter ' + strCmdPara )
      strCmdPara = '{:04x}'.format(intcmdpara) # 
      strCmdPara = strCmdPara.upper()

      logging.debug ('GOT command name ' + strCmdName)

      strCmdNamepara = strCmdName + strCmdPara

      logging.debug (" READING " + self.strName + " converting from " + strCmdNamepara + " with length " + str(len(strCmdNamepara)) )

      strHexCmdNamePara = bytearray.fromhex( strCmdNamepara )
      # 'cp1252' windows default encoding
      strHexCmdNamePara = str( strHexCmdNamePara.decode('cp1252') )


      logging.debug ('SEND command parameters for conversion ' + str(strHexCmdNamePara) )
      crc = 0xFFFF

      ##! OK!! strHexCmdNamePara = "\x01\x06\x00\x2C\x00\xdc" #This is what must be sent to the following line to give the correct
      ##! CRC value to change the pump to 22 RPM

      hexcrc = self.istCRC.calcString( strHexCmdNamePara, crc)
      logging.debug ('conver to string ' + str(hexcrc) )
      strhexcrc = format(hexcrc, '04x')
      strhexcrc = strhexcrc[2:] + strhexcrc[0:2]
      logging.debug( ' READING: Sending command ' + strCmdName + ' to device ' + self.strName + ' at parameter in hex: ' + strCmdPara + " generated: " + strhexcrc )
      logging.debug ('SENDING : ' + strCmdName +strCmdPara.upper() +strhexcrc.upper() )

      self._pdev.write( bytes.fromhex(strCmdName +strCmdPara.upper() +strhexcrc.upper() ) )


    logging.debug( ' READING ' + self.strName + ' commend sent ' )
    
    byteline = self._pdev.readline(20)
    logging.debug( ' READING ' + self.strName + ' line obtained with bytes ' )
    strLine = byteline.hex()
    logging.debug(' strLine[0:4]= '+strLine[0:4]+', strCmdName[0:4]= '+strCmdName[0:4])
    if strLine[0:4] != strCmdName[0:4]:
      logging.fatal(' PUMP: Communication returned back a value that was different from the one sent... Aborting program')
      raise ValueError("Command and response, do not match!")
      
    logging.debug( ' READING ' + self.strName + ' line obtained ' + strLine )
    #print( ' READING current ' + self.strName + ' value: ' + strLine )
    logging.debug( ' READING current ' + self.strName + ' value: ' + strLine )

    # TODO: setting pump values OK???
    self._value =  strLine

  def last(self) : 
    return self._value
