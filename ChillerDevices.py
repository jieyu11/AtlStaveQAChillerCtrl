'''
  Program ChillerDevices.py
  
Description: ------------------------------------------------------------------
   This file contains the class construct to perform I/O with the USB connected
devices used in the HEP ATLAS stave testing equipment.  The current 
equipment/devices connected are:

   Flir A655sc IR camera.
   FTS Systems RC211B0 recirculating cooler,
   Lenze ESV751N02YXC NEMA 4x inverter drive to control booster pump,
   Omega HH314A Humidity meter,
   Omega HH147U Data Logger Thermometer,
   Arduino UNO board & DF Robot relay shield, ArduinoDevice.py

History: ----------------------------------------------------------------------
   V1.0 - Oct-2017  First public release.

Environment: ------------------------------------------------------------------
   This program is written in Python 3.6.  Python can be freely downloaded
from http://www.python.org/.  This program has been tested on PCs running 
Windows 10.

Author List: -------------------------------------------------------------------
  R. McKay    Iowa State University, USA  mckay@iastate.edu
  J. Yu       Iowa State University, USA  jieyu@iastate.edu
  W. Heidorn  Iowa State University, USA  wheidorn@iastate.edu
  
Notes: -------------------------------------------------------------------------

Dictionary of abbreviations: ---------------------------------------------------
    bol - boolean
  cls - class
  flt - float
  int - integer
  str - string
'''

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


# Import section --------------------------------------------------------------

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
    logging.info(' Initialization Device, name ' + strName + ' PORT ' + strPort + ' baud ' + str(intBaud) + \
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
    logging.info('Loading {:20s}'.format( strName ) + ' at port {:6s}'.format( strPort ) + \
                  ' baudrate at {:6d}'.format( intBaud ) + ' status {:b}'.format( self._bolOpened) );

  def __str__(self):
    print('Device {:20s}'.format( strName ) + ' at port {:6s}'.format( strPort ) + \
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
    self._value = [100, 0, 0]

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
    logging.debug(' READING current ' + self.strName + ' value: ' + strLine  )
    humval = int(strLine[6:10], 16) / 10 
    t1val = int(strLine[10:14],16)/10
    t2val = int(strLine[14:18],16)/10

    self._value = [humval,t1val,t2val]
    #logging.info(' READING current ' + self.strName + ' value: {:4.1f}%'.format( humval )  )
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
    logging.debug(' READING: Sending command ' + strCmdName + ' to device ' + self.strName )
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

        #strTall.append(' T{:1d} value: {:6.3f}'.format((Tidx+1), Tval ) )
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
      logging.warning(' data line index ' + str(lineIdx) + ' < 0!! set to 0. ' )
      lineIdx = 0
    elif lineIdx >= self._intDataLines :
      logging.warning(' data line index ' + str(lineIdx) + ' >= ' + str(self._intDataLines) + \
                       '!! set to ' + str(self._intDataLines - 1) + '.' )
      lineIdx = self._intDataLines - 1

    return tuple( self._temperaturedata[lineIdx] )

# ------------------------------------------------------------------------------
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
      logging.debug(' READING: Sending command ' + strCmdName + ' to device ' + self.strName )
      self._pdev.write( (strCmdName + '\r\n').encode() )
    else :
      logging.debug(' READING: Sending command ' + strCmdName + ' to device ' + self.strName + " with parameter " + strCmdPara)
      self._pdev.write( (strCmdName + strCmdPara + '\r\n').encode() ) 
    byteline = self._pdev.readline()
    strinclines =  byteline.decode()

     
    for index, strLine in enumerate(strinclines.splitlines()) :
      logging.debug(' Chiller returned: '+ strLine)
      if index ==0 and ('ok' in strLine or 'Ok' in strLine or 'OK' in strLine) : 
        logging.debug(' Device ' + self.strName + ' status :'+ strLine)
      elif index ==0 :
        logging.fatal(' Device ' + self.strName + ' Response from Chiller:' + strLine + '. FATAL! ' )
        raise ValueError(" Garbled Response!!!! NOT GOOD")
       
      elif index == 1 and '!' in strLine:
        strvarname = strLine[0:4]
        fltvarvalue = float( strLine[5:-1] )
        if strvarname[0:1] != str('F') and strvarname[0:1] != str('E') :
          logging.fatal(' Device ' + self.strName + ' returned message: ' + strLine + ' not recognized. FATAL!' )
          raise ValueError(" Bad Response")
        elif strvarname == str('E042'):
          logging.warning(' Device ' + self.strName + ' has already been started. Ignoring...')
        elif strvarname[0:1] == str('E'):
          logging.fatal(' Device ' + self.strName + ' returned error message: ' + strLine)
          raise ValueError("Error Message Returned")   
        elif strvarname == str('F076'):
          strNum = strLine.split('=')[-1]
          strNum = strNum.strip('+-!')
          fltNum = float(strNum)
#          logging.debug(' Device ' + self.strName + ' has given alarm: ' +strNum)
          if fltNum != 0:
            logging.fatal(' Device ' + self.strName + ' has given alarm: ' + strNum) 
            self._value = float(-9999)
          else:
            logging.debug('  Chiller has no alarms.')
        elif strvarname == str('F044'):
          strNum = strLine.split('=')[-1]
          strNum = strNum.strip('+-!')
          if '+' in strLine:
            self._value = float(strNum)
          else:
            self._value = float(strNum)*(-1.)
    
        #self._value = ErrorCode
        return
      else:
        logging.info(" Device " + self.strName + ' gave weird result: ' + strLine)
        
  def last(self) :
    return self._value
    
    
# ------------------------------------------------------------------------------
# --------------------------- Booster pump class -------------------------------
class clsPump ( clsDevice ):
  def __init__(self, strName, strPort, intBaud, bytesize=8, parity='N', stopbits=1, timeout=1):
    """
      Initialize booster pump inverter (i.e. controller) serial protocol and define the 
      boundries of the frequency (i.e. RPS) we will allow the booster pump to run.
    """
    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)
    self.istCRC = CycRedundCheck()
    self.fltRPSmin = 5.0
    self.fltRPSmax = 40.0
    self.fltRPSdefault = 12.0
    self._value = 0


# ------------------------------------------------------------------------------
  def read(self, strCmdName, strCmdParam="", fltCurrentTemps=[]):
    """
      Send a command to the booster pump inverter and read the response.
      The inverter will echo the command back, except for status commands.  Should
      the command sent not valid, the inverter will not respond.
    """
	
	# If there is no command parameter passed in, then assume the complete command with
	# parameter(s) plus CRC was included with the command passed in.
    if strCmdParam == "" : 
      logging.debug('READ: Sending command ' + strCmdName + ' to ' + self.strName )
      self._pdev.write( bytes.fromhex(strCmdName))
      logging.debug('READ:    sent command ' + strCmdName + ' to ' + self.strName)
      if '?' in strCmdName:
        print("#TODO check pump output convert")
		
	# Here we deal with commands that have a parameter and needs to calculate the CRC
	# for a correct command to send to the device. Also look for the '=' sign as this
	# means the parameter is included in the command.
    else :
      if strCmdName[-1:] == "=" :
        strCmdName = strCmdName[0:-1]

      logging.debug("Booster pump parameter: " + strCmdParam)
      fltCmdParam = float(strCmdParam) # e.g. 22.5
      if fltCmdParam < self.fltRPSmin or fltCmdParam > self.fltRPSmax :
        logging.warning(f' WARNING! value {strCmdParam} is out of allowed range [{self.fltRPSmin},{self.fltRPSmax}]' \
                      + f' for {self.strName}.  Pump will be set to {self.fltRPSdefault} RPS' )
        fltCmdParam = self.fltRPSdefault

      intCmdParam = int(10 * fltCmdParam)
      logging.debug(f'READ: Sending command {strCmdName} to {self.strName} with parameter {strCmdParam}' )
      strCmdParam = '{:04x}'.format(intCmdParam) # 
      strCmdParam = strCmdParam.upper()
      strCommand = strCmdName + strCmdParam
      logging.debug(f" READ: {self.strName} calculating CRC from {strCommand} of length {str(len(strCommand))}" )

      strCmdByteArr = bytearray.fromhex( strCommand )
      logging.debug('READ: command string to calculate CRC: ' + str(strCmdByteArr) )
      crc = 0xFFFF
      for ch in strCmdByteArr:
        crc = self.istCRC.calcByte(ch, crc)
      strHexCRC = format(crc, '04x')
      strHexCRC = strHexCRC[2:] + strHexCRC[0:2]  # Must swap bytes as CRC calculator result is little endian.
      logging.debug(f'READ: Sending command {strCmdName} to {self.strName} with parameter ' \
                  + f'{strCmdParam} + CRC {strHexCRC}')
      theCommand = strCommand + strHexCRC.upper()
      self._pdev.write( bytes.fromhex(theCommand) )
      logging.debug('READ: full command sent: ' + theCommand )
    
    byteline = self._pdev.readline(20)
    strResponse = byteline.hex()
    logging.debug(' Response from ' + self.strName +' = ' + strResponse)
    if strResponse[0:4] != strCmdName[0:4]:
      logging.fatal(' PUMP: Communication returned back a value that was different from the one sent... Aborting program') 
      logging.fatal(' PUMP: ' + strResponse[0:4] + " != " + strCmdName[0:4])
      raise ValueError("Command and response, do not match!")
      
    # TODO: setting pump values OK???
    self._value =  strResponse

  def last(self) : 
    return self._value
