"""
pseudo device class to mimic the real device and react to commands
  chiller
  boost pump
  thermocouple couple
  humidity sensor
  IR camcera
"""

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

  def read(self, strcmdname, strcmdpara=""):
    """
      function of reading device data
    """
    if strcmdpara == "" :
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname )
    else:
      logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname + " with parameter " + strcmdpara )

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
    self._value = 100

  def read(self, strcmdname, strcmdpara=""):
    """
      Humidity: function of reading data
    """
    logging.debug( self._strclassname + ' Sending command ' + strcmdname + ' to device ' + self._strname )

    # random in 0. - 1., return in percentage
    self._value = random.random() * 100

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
    self._temperaturedata =  [[0 for x in range( self._intDataPoint )] for y in range( self._intDataLines )]


  def read(self, strcmdname, strcmdpara=""):
    """
      Thermocouple: function of reading data
    """
    # to mimic the real case, reading the thermocouple data takes around 25 seconds
    time.sleep( 25 )
    for Lidx in range( self._intDataLines ) :
      for Tidx in range( self._intDataPoint ) :
        # temperature in -45 +55.
        self._temperaturedata[ Lidx ][ Tidx ] = random.random() * 100 - 45.


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

class clsPseudoChiller ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Device: Chiller, function of initialization
    """
    super().__init__(strname)

    self._strclassname = ' < Chiller > '

    # keep the last read out value
    self._value = 0


  def read(self, strcmdname, strcmdpara=""):
    """
      Chiller: function of reading data
    """
    # chiller temperature -45 +55
    self._value = random.random() * 100 - 45

  def last(self) :
    return self._value

class clsPseudoPump ( clsPseudoDevice ):
  def __init__(self, strname):
    """
      Pseudo Device: boost pump, function of initialization
    """
    super().__init__(strname)
    self._value = 0


  def read(self, strcmdname, strcmdpara=""):
    """
      Pump: function of reading data
    """
    if int(random.random() * 1000) % 2 == 0 :
      self._value = 10
    else:
      self._value = 22

  def last(self) : 
    return self._value
