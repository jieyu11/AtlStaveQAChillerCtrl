'''
  Program ChillerPseudoDevices.py
  
Description: ------------------------------------------------------------------
  This file contains the class constructs to mimic the real device used in the 
stave thermo evaluations.  Its purpose is to provide a means to check code 
during development.  The mimic devices are:
  
  Flir A655sc IR camera;
  FTS Systems RC211B0 recirculating cooler; 
  Lenze ESV751N02YXC NEMA 4x inverter drive;
  Omega HH314A Humidity/Temperature Meter;
  Omega HH147U Data Logger Thermometer;
  Arduino UNO Rev 3 shield.

History: ----------------------------------------------------------------------
  V1.0 - Oct-2017  First public release.
  V1.4 - Jul-2018  Added code for the Arduino UNO to read the flow meter (Proteus
           08004BN1) and control three actuators (Swagelok SS-62TS4-41DC).
           Updated comments and modified screen messages to operator.
Environment: ------------------------------------------------------------------
  This program is written in Python 3.6.  Python can be freely downloaded from 
http://www.python.org/.  This program has been tested on PCs running Windows 10.

Author List: -------------------------------------------------------------------
  R. McKay    Iowa State University, USA  mckay@iastate.edu
  J. Yu       Iowa State University, USA  jieyu@iastate.edu
  W. Heidorn  Iowa State University, USA  wheidorn@iastate.edu
  
Notes: -------------------------------------------------------------------------

Dictionary of abbreviations: ---------------------------------------------------
  cls - class
  cmd - command
   flt - float
   int - integer
  str - string

'''
# Import section ---------------------------------------------------------------

import time
import logging
import random
# ------------------------------------------------------------------------------
# Class Pseudo Device (base) ---------------------------------------------------
# Serve as base class for specific devices 
#
class clsPseudoDevice:
  def __init__(self, strname):
    """
      function of initialization for any device
    """

    logging.info( ' Initialization Pseudo Device, name ' + strname )
    self._strname = strname
    self._strclassname = ' < Device > '

# ----------------------------
  def read(self, strcmdname, strcmdpara="",fltCurrentTemps=[]):
    """
      function of reading device data
    """
    if strcmdpara == "" :
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname )
    else:
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname + " with parameter " + strcmdpara )

# ----------------------------
  def last(self) :
    """
      function to get the last read out value(s)
    """
    return 0


# ------------------------------------------------------------------------------
# Class Pseudo Humidity (inherited Device) -------------------------------------
class clsPseudoHumidity ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Devide: Humidity, function of initialization
    """
    super().__init__(strname)

    self._strclassname = ' < Humidity > '

    # keep the last read out value, initialized with 100%
    self._value = [100,0,0]

# ----------------------------
  def read(self, strcmdname, strcmdpara="",fltCurrentTemps=[]):
    """
      Humidity: function of reading data
    """
    logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname )

    # random in 0. - 1., return in percentage
    self._value = [random.random() * 5,20,20]

# ----------------------------
  def last(self) : 
    return self._value

# ------------------------------------------------------------------------------
# Class Thermocouple (inherited Device) ----------------------------------------
class clsPseudoThermocouple ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Pseudo Device: Thermocouple, function of initialization
      ndataread: 1 -- 29; 
          29 data points are obtained each time, one can chose how many to write out.
    """

    self._strclassname = ' < Thermo > '

    super().__init__(strname)
    self._intDataLines = 29 # 29 data measurements
    self._intDataPoint =  4 # 4 thermocouple
    # temperature data in 2D: [29][4]
    # initialized with 0. refer as [i][j]
    self._temperaturedata =  [0,0,0,0]

# ----------------------------
  def read(self, strcmdname, strcmdpara="",fltCurrentTemps=[]):
    """
      Thermocouple: function of reading data
    """
    # to mimic the real case, reading the thermocouple data takes around 25 seconds
    time.sleep( 0.3 )
	
    #Starting Temperature Conditions
    fltOldSetValue = fltCurrentTemps[0]
    TResOld = fltCurrentTemps[1]
    TinOld = fltCurrentTemps[2]
    ToutOld = fltCurrentTemps[3]
    TboxOld = fltCurrentTemps[4]
    TroomOld = fltCurrentTemps[5]

    #Create a new second of temp data
    TempPercentChange = 0.05 * random.random() # How much the fluid temperature going to the stave changes each second
    OffsetPercent = 0.05                       # Offset percentage that the outflowing fluid is
    
    # A statement to see if we are cooling or heating the stave
    if fltOldSetValue > TinOld:
      Offset = OffsetPercent
    else:
      Offset = -OffsetPercent
    # Generating the individual data from Old data
    #TRes  = TResOld*( 1- TempPercentChange)+ fltCurrentTemps[0]*TempPercentChange
    Tin   = TinOld *( 1- TempPercentChange*2)+ TResOld*TempPercentChange*2  
    Tout  = ToutOld*(1- TempPercentChange*4)+TinOld*TempPercentChange*4
    Troom = TroomOld + 0.001 * random.random()
    Tbox  = TboxOld + (((Tin+Tout)/2)-TboxOld)*0.0005*random.random()
  
    # Saving the data to _temperaturedata
    self._temperaturedata[0] = Tin
    self._temperaturedata[1] = Tout
    self._temperaturedata[2] = Tbox
    self._temperaturedata[3] = Troom
	
# ----------------------------
  def last(self, lineIdx = 28) :
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

    return tuple( self._temperaturedata )
# ------------------------------------------------------------------------------
# Class Chiller (inherited device) ---------------------------------------------
class clsPseudoChiller ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname)

    self._strclassname = ' < Chiller > '

    # keep the last read out value
    self._value = 0

# ----------------------------
  def read(self, strcmdname, strcmdpara="",fltCurrentTemps=[]):
    """
      Chiller: function of reading data
    """
    # chiller temperature -45 +55
    #Mimics approximate Chiller Communication Time
    time.sleep(2.2)
	
    TResOld = fltCurrentTemps[1]
    TSet = fltCurrentTemps[0]
    TempPercentChange = 0.3*random.random()
    TRes  = TResOld*( 1- TempPercentChange)+ TSet*TempPercentChange

    self._value = round(TRes,4)

# ----------------------------
  def last(self) :
    return self._value

# ------------------------------------------------------------------------------
# Class Pump (inherited device) ------------------------------------------------
class clsPseudoPump ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Pseudo Device: boost pump, function of initialization
    """
    super().__init__(strname)
    self._value = 0

# ----------------------------
  def read(self, strcmdname, strcmdpara="",fltCurrentTemps=[]):
    """
      Pump: function of reading data
    """
    if int(random.random() * 1000) % 2 == 0 :
      self._value = 10
    else:
      self._value = 22

# ----------------------------
  def last(self) : 
    return self._value
