"""
Class clsChillerRun
	
  Description: 
  	A Python script to control run routine of the chiller, data recording of the 
    thermocouples and humidity readout.
  
  Author and contact:
  	J. Yu  Iowa State University,  USA  jieyu@iastate.edu
  	
  Notes:
  
  Dictionary of abbreviations: 
"""


# ------------------------------------------------------------------------------
# Import section ---------------------------------------------------------------

import logging
#logging.addLevelName( 21, "DATA")
##def data(self, message, *args, **kws):
##  if self.isEnabledFor( 21 ):
##    self._log( 21, message, args, **kws) 
##logging.Logger.data = data
#def data(self, message, *args, **kws):
#    self.log(21, message, *args, **kws) 
#logging.Logger.data = data

# need setattr ?????

import time
import sys
from ChillerRdDevices import *
from ChillerRdConfig  import *
from ChillerRdCmd     import *

# https://docs.python.org/3.6/library/multiprocessing.html
#from multiprocessing import Process, Value
import multiprocessing as mp

from enum import IntEnum
from functools import total_ordering
@total_ordering
class StatusCode (IntEnum) :
  OK      = 0  # -> all devices are fine
  WARNING = 1  # -> e.g. Humidity reading not working
  ERROR   = 2  # -> e.g. Thermocouple temperature reading not working
  PANIC   = 3  # -> e.g. Chiller running at too high / low temperature
  FATAL   = 4  # -> emergency, e.g. Chiller running low liquid
  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented


# ------------------------------------------------------------------------------
# Class ChillerRun -------------------------------------------------------------
class clsChillerRun :
  """
    Class to provide user interfaces for:
    * Running the Chiller Pump system routine
    * Recording temperature and humidity values
    * Shutdown Chiller Pump system
    * Close Thermocouple and Humidity readout 

    Code Structure:
           | <---- Devices Commands 
           |           | <-- Command communications           
           |
           | <---- Devices Connection to PC 
           |           | <-- Devices connection configuration
           |
           | <---- Run Configuration 
           |
      |<-- Chiller Run                                         
      |
      Main
  """


# ------------------------------------------------------------------------------
# Function: Initialization -----------------------------------------------------
  def __init__(self, runPseudo = False) :

    self._strclassname = '< RUNNING >'
    #
    # Global status of the while system
    #

    self._intSystemStatus = StatusCode.OK

    #
    # configuration of how the devices are connected to the PC
    #

    self._istConnCfg = clsConfig( 'ChillerConnectConfig.txt' )

    #
    # pass the configuration of how the devices connection
    # to the device handler 
    #

    self._istDevHdl = clsDevicesHandler( self._istConnCfg, runPseudo )


    #
    # interpretation of machine readable commands into human readable commands
    # and vice versa
    #

    self._istCommand = clsCommands( 'ChillerEquipmentCommands.txt' )


    # 
    # configuration of the running routine
    # 

    self._istRunCfg = clsConfig( 'ChillerRunConfig.txt' )

    # last temperature value for liquid from thermocouple, needed for humidity sensor 
    # if liquid temperature is lower than 0., humidity cannot be too high.
    self._fltTempLiquid = 0.

# ------------------------------------------------------------------------------
# Function: sendcommand --------------------------------------------------------
  def sendcommand(self, strusercommand) :
    """
      function to send command to any of a device
    """
    try:
      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( strusercommand )
      self._istDevHdl.readdevice( strdevname, strcmdname, strcmdpara)
    except:
      if self._intSystemStatus < StatusCode.ERROR : 
        self._intSystemStatus = StatusCode.ERROR
      raise ValueError('Could not find user command: %s in %s' % (strusercommand, self._istCommand.name() ))


# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump in emergency --------------------------------
  def eShutdownChillerPump (self) :
    """
      Emergency Shut down
    """
    logging.info( self._strclassname + ' Chiller Pump Need to shut down due to emergency!!! ')
    self._intSystemStatus = StatusCode.FATAL
    self.shutdownChillerPump()


# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump ---------------------------------------------
  def shutdownChillerPump (self) :
    """
      procedure to shutdown the Chiller and Pump:
      * set Chiller Temperature to the stop value
         - for non emergency shutdown (status <=2) wait for Chiller to cool down
         - raw RPM value needed for this step
      * set Pump RPM to the stop value
      * shutdown Pump 
         - shutdown Pump first
      * shutdown Chiller
         - shutdown Chiller in the end

      Shutdown conditions:
      1) Emergency (status = FATAL, no cool down)
      2) Runtime error (status = ERROR or PANIC)
      3) End of run (status = OK or WARNING)
    """

    strPumpStopRPM = '10'
    strChiStopTemp = '20'
    try:
      strPumpStopRPM = self._istRunCfg.get( 'Pump', 'StopRPM' )
      strChiStopTemp = self._istRunCfg.get( 'Chiller', 'StopTemperature' )
    except:
      if self._intSystemStatus < StatusCode.WARNING :
        self._intSystemStatus = StatusCode.WARNING

      raise KeyError("Sections: Pump, Chiller, Key: StopRPM, StopTemperature not present in configure: %s" % \
                     self._istRunCfg.name() )

    #
    # Dictionary to keep the shutdown procedure
    # Key: Chiller and Pump commands 
    # Value: information for logging
    #
    strCommandDict = { 'cChangeSetpoint=' + strChiStopTemp : 'Chiller change set point to ' + strChiStopTemp,
                       'iRPM=' + strPumpStopRPM :            'Pump change RPM to '+strPumpStopRPM,
                       'iStop' :                             'Pump shutting down', 
                       'cStop' :                             'Chiller shutting down'}

    for strcommand, strlog in strCommandDict.items() :
      # send the command to the corresponding device
      self.sendcommand( strcommand )

      # write information into logging file
      logging.info( strlog );

      # wait for 1 seconds after each command
      time.sleep(1) 

      # for non emergency shutdown, first cool down the chiller before shutting down the whole system 
      if self._intSystemStatus < StatusCode.FATAL and 'cChangeSetpoint' in strcommand :
        intTimeCool = 600 # in seconds 
        try : 
          intTimeCool = 60 * int( self._istRunCfg.get( 'Chiller', 'StopCoolTime' ) ) # parameter in minutes
        except :
          pass
        logging.info( 'Chiller cooling down for {:3d}'.format( intTimeCool // 60 ) + ' minutes ' ) 
        time.sleep( intTimeCool )

# ------------------------------------------------------------------------------
# Function: run one loop of Chiller Pump ---------------------------------------
  def runChillerPumpOneLoop(self, name = "Chiller") :
    """ 
      main routine of every loop running the Chiller and Boost Pump
      set the name parameter if not running the default "Chiller"
    """
    intChiNLoops  = 0
    try:
      intChiNLoops  = int( self._istRunCfg.get( name, 'NLoops' ) )
    except:
      raise KeyError("Sections: "+ name + ", Key: NLoops not present in configure: %s" % \
                     self._istRunCfg.name() )

    logging.info("Section: "+ name + ", number of loops " + str(intChiNLoops) )

    # don't run any loop if it is set to 0 or negative
    if intChiNLoops <= 0: return

    strTemperatureList = [ ]
    strTimePeriodList  = [ ]
    try:
      # split values by ',' and then remove the white spaces.
      strTemperatureList = [ x.strip(' ') for x in self._istRunCfg.get( name, 'Temperagures' ).split(',') ]
      strTimePeriodList  = [ x.strip(' ') for x in self._istRunCfg.get( name, 'TimePeriod'   ).split(',') ]
    except:
      raise KeyError("Section: "+ name + ", Key: Temperagures, TimePeriod not present in configure: %s" % \
                     self._istRunCfg.name() )

    intNTemperature = len( strTemperatureList )
    if intNTemperature != len(strTimePeriodList) :
      logging.warning( ' Length of temperature list ' + str(intNTemperature) + ' != ' + \
                       ' Length of time period list ' + str( len( strTimePeriodList ) ) + '. Set to Min.' )
      if len( strTimePeriodList ) < intNTemperature :
        intNTemperature = len( strTimePeriodList )
    
    for iloop in range(intChiNLoops) :
      logging.info( ' Chiller, Pump running at loop no. ' + str(iloop) )
      for itemp in range(intNTemperature) :
        # changing the Chiller Temperature to a corresponding value
        logging.info( ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        self.sendcommand( 'cChangeSetpoint=' + strTemperatureList[itemp] )

        logging.info( ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        for itime in range( int(strTimePeriodList[itemp]) ):
          logging.info( ' Chiller waiting at ' + str(itime) + 'th minute.' )

          #
          # sleep for one minute, check system status every second
          #
          for i in range( 60 ):
             # check second by second the status of the system
             if self._intSystemStatus > StatusCode.ERROR: return 
             time.sleep( 1 ) # in seconds


# ------------------------------------------------------------------------------
# Function: run Chiller Pump ---------------------------------------------------
  def runChillerPump(self) :
    """
      main routine to run Chiller Pump with user set loops
    """

    strPumpRunRPM = '22'
    try:
      strPumpRunRPM = self._istRunCfg.get( 'Pump', 'RunRPM' )
    except:
      raise KeyError("Sections: Pump, Key: RunRPM, not present in configure: %s" % \
                     self._istRunCfg.name() )

    #
    # Unlock before sending commands to inverter (Pump)
    # do it once at a beginning of a run
    #
    self.sendcommand( 'iUnlockDrive' )
    self.sendcommand( 'iUnlockParameter' )
    self.sendcommand( 'iRPM=' + strPumpRunRPM )
 
    for strsectionname in [ name for name in self._istRunCfg.sections() if "Chiller" in name ]:
      self.runChillerPumpOneLoop( name = strsectionname )

      # constantly check the status of the system
      if self._intSystemStatus > StatusCode.ERROR: return 
 

# ------------------------------------------------------------------------------
# Function: record temperature -------------------------------------------------
  def recordTemperature(self) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """
    fltTUpperLimit =  60 # upper limit in C for liquid temperature
    fltTLowerLimit = -55 # lower limit in C for liquid temperature
    intFrequency   =  10 # one data point per ? seconds
    intDataPerRead =  29 # number of data points every time user read, ~1 data point / 1 second
    intIdxTLiquid  =   0 # index of the thermocouple connected to liquid temperature, 0 - 3

    try: 
      fltTUpperLimit = float( self._istRunCfg.get( 'Thermocouple', 'LiquidUpperThreshold' ) )
      fltTLowerLimit = float( self._istRunCfg.get( 'Thermocouple', 'LiquidLowerThreshold' ) )
      intFrequency   = int  ( self._istRunCfg.get( 'Thermocouple', 'Frequency' ) )
      intDataPerRead = int  ( self._istRunCfg.get( 'Thermocouple', 'DataPerRead' ) )
      intIdxTLiquid  = int  ( self._istRunCfg.get( 'Thermocouple', 'IdxLiquidTemperature' ) )

      if   intFrequency <              1 : 
        logging.warning( self._strclassname + ' setting Frequency ' + intFrequency + ' < 1. Set to 1.')
        intFrequency = 1
      elif intFrequency > intDataPerRead : 
        logging.warning( self._strclassname + ' setting Frequency ' + intFrequency + ' > ' + \
                         intDataPerRead + '. Set to ' + intDataPerRead + '.')
        intFrequency = intDataPerRead

      if intIdxTLiquid < 0 and intIdxTLiquid > 3 :
        logging.error( self._strclassname + ' IdxLiquidTemperature '+ intIdxTLiquid + ' not in [0, 3]. Check! ')
        return
    except:
      raise KeyError( ' Section: Thermocouple, Key: LiquidUpperThreshold, LiquidLowerThreshold, Frequency not found in %s ' % \
                      self._istRunCfg.cfgname() )
    

    istThermocouple = self._istDevHdl.getdevice( 'Thermocouple' )
    if istThermocouple is None:
      logging.error( self._strclassname + ' Thermocouple not found in device list! ')
      return

    #
    # keep reading data until the process is killed or 
    # kill the process if the global status is more serious than an ERROR
    #
    while (self._intSystemStatus <= StatusCode.ERROR) : 
      #
      # read thermocouple data, every read takes ~25 seconds for 29 data points
      # 
      self.sendcommand( 'tRead' )

      for idata in range( intDataPerRead ) :
        if idata % intDataPerRead == 0 : 
          fltTempTup = list( istThermocouple.last( idata ) )
          logging.data( 'Thermocouple T1: %5.2f, T2: %5.2f, T3: %5.2f, T4: %5.2f ' % \
                        (fltTempTup[1], fltTempTup[2], fltTempTup[3], fltTempTup[4]) )

          # keep on track the liquid temperature read out
          # needed by humidity function 
          self._fltTempLiquid = fltTempTup[ intIdxTLiquid ]

          if self._fltTempLiquid < fltTLowerLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' < lower limit ' + fltTLowerLimit + '! Return! ')
            self._intSystemStatus = StatusCode.PANIC
          if self._fltTempLiquid > fltTUpperLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' > upper limit ' + fltTUpperLimit + '! Return! ')
            self._intSystemStatus = StatusCode.PANIC


# ------------------------------------------------------------------------------
# Function: record humidity ----------------------------------------------------

  def recordHumidity(self) :
    """
      recording the humidity inside the box
    """

    fltStopUpperLimit = 5.0 # upper limit in % for humidity to stop the system
    fltWarnUpperLimit = 2.0 # upper limit in % for humidity to warn the system
    intFrequency      =  10 # one data point per ? seconds

    try: 
      fltStopUpperLimit = self._istRunCfg.get( 'Humidity', 'StopUpperThreshold' )
      fltWarnUpperLimit = self._istRunCfg.get( 'Humidity', 'WarnUpperThreshold' )
      intFrequency      = self._istRunCfg.get( 'Humidity', 'Frequency' )
      if istFrequency < 1:
        logging.warning( self._strclassname + ' Humidity reading frequency ' + str( intFrequency ) + '! set to 1.')
    except:
      pass

    istHumidity = self._istDevHdl.getdevice( 'Humidity' )
    if istHumidity is None:
      logging.error( self._strclassname + ' Humidity not found in device list! ')
      return


    while( self._intSystemStatus <= StatusCode.ERROR ) :
      self.sendcommand( 'hRead' )
      if self._fltTempLiquid < 0.:
        fltHumidity = istHumidity.last()
        if( fltHumidity > fltStopUpperLimit ): 
          logging.error( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                         ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + 
                         '% upper limit! Return! ')
          self._intSystemStatus = StatusCode.PANIC
          return
        elif( fltHumidity > fltWarnUpperLimit ): 
          logging.warning( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                           ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + '%')
          self._intSystemStatus = StatusCode.ERROR

      time.sleep( intFrequency - 1 )


  def runRoutine(self) :
    """
      Run main routine
    """
    # start Chiller Pump, it they haven't started
    self.sendcommand( 'cStart' )
    time.sleep(1)
    self.sendcommand( 'iStart' )
    time.sleep(1)

    #
    # run preset Chiller and Pump routine using two separated processing
    # one for Chiller Pump running,
    # the other for Temperature and Humidity recording
    # 
    mpList = []
    mpList.append( mp.Process(target = self.recordTemperature) )
    mpList.append( mp.Process(target = self.recordHumidity) )
    mpList.append( mp.Process(target = self.runChillerPump) )

    for p in mpList:
      p.start()
    
    # wait until Chiller Pump running finishes
    mpList[2].join()

    # shutdown Chiller and Pump
    self.shutdownChillerPump()

    # TODO: use a better way to stop recording ???
    mpList[0].terminate()
    mpList[1].terminate()


def data(self, message, *args, **kws):
    self.log(21, message, *args, **kws) 

def main():
  """
    test running the whole routine
  """
  
  logging.basicConfig(filename='test.log', level=logging.DEBUG, \
                      format='%(asctime)s %(levelname)s: %(message)s', \
                      datefmt='%m/%d/%Y %I:%M:%S %p')

  logging.addLevelName( 21, "DATA")
  logging.Logger.data = data


  #runPseudo = False
  runPseudo = True
  #if '-pseudo' in sys.argv[1:]
  #  runPseudo = True
  tc = clsChillerRun( runPseudo )
  tc.runRoutine()


if __name__ == '__main__' :
  main()

