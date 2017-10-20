"""
Class clsChillerRun
	
  Description: 
  	A Python script to control run routine of the chiller, data recording of the 
    thermocouples and humidity readout.
  
  Author and contact:
  	J. Yu  Iowa State University,  USA  jieyu@iastate.edu
  	W. Heidorn Iowa State Univiersity, USA wheidorn@iastate.edu


  Notes:
  
  Dictionary of abbreviations: 
"""


# ------------------------------------------------------------------------------
# Import section ---------------------------------------------------------------

import logging
import logging.handlers

import configparser

def data(self, message, *args, **kws):
  if self.isEnabledFor( DataLevel ):
    self._log( DataLevel, message, args, **kws) 

import time
import sys
from ChillerRdDevices import *
from ChillerRdConfig  import *
from ChillerRdCmd     import *

# https://docs.python.org/3.6/library/multiprocessing.html
#from multiprocessing import Process, Value
import multiprocessing as mp
from multiprocessing import Process, Value

from enum import IntEnum
from functools import total_ordering
@total_ordering
class StatusCode (IntEnum) :
  OK      = 0  # -> all devices are fine
  WARNING = 1  # -> e.g. Humidity reading not working
  ERROR   = 2  # -> e.g. Thermocouple temperature reading not working
  PANIC   = 3  # -> e.g. Chiller running at too high / low temperature
  FATAL   = 4  # -> emergency, e.g. Chiller running low liquid
  DONE    = 5  # -> Chiller, Pump both off
  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented
'''
Also I am adding in a global called intStatusCode, it will do the same thing as the StatusCode Class
'''
# -----------------------------------------------------------------------------
# Intro -----------------------------------------------------------------------
def intro():
  """
    A List of things printed when the program runs
  """
  print("------------------------- CHILLER CONTROL -------------------------")



# -----------------------------------------------------------------------------
# Listener Process ------------------------------------------------------------
def procListener (queue) :
  """
    Process that reads the queue and then puts thing to a file
  """

  logging.addLevelName( 21, "DATA")
  logging.Logger.data = data 

  root = logging.getLogger()
  h = logging.handlers.RotatingFileHandler('test.log','a',1000000,10)
  f = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
  h.setFormatter(f)
  root.addHandler(h)
  while True:
    try:
      record = queue.get()
      if record is None:
        break
      
      logger = logging.getLogger(record.name)
      logger.handle(record)
      print(record.asctime + " "+ record.levelname+" "+record.message)
    except Exception:
      import sys, traceback
      print('Whoops! Problem:', file=sys.stderr)
      traceback.print_exc(file=sys.stderr)

# -----------------------------------------------------------------------------
# Function: process_configure -------------------------------------------------
def p_config(queue) :
  """
       function that must be present in any process that uses the logger
  """
  h = logging.handlers.QueueHandler(queue)
  root = logging.getLogger()
  root.addHandler(h)
  root.setLevel(logging.INFO) # This sets what level is logged in each process

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
  def init(self, strdevnamelist, runPseudo = False) :

    self._strclassname = '< RUNNING >'
    #
    # Global status of the while system
    #

    self._intSystemStatus = StatusCode.OK

    #
    # configuration of how the devices are connected to the PC
    #

    self._istConnCfg = clsConfig( 'ChillerConnectConfig.txt', strdevnamelist)

    #
    # pass the configuration of how the devices connection
    # to the device handler 
    #

    self._istDevHdl = clsDevicesHandler( self._istConnCfg, strdevnamelist, runPseudo )


    #
    # interpretation of machine readable commands into human readable commands
    # and vice versa
    #

    self._istCommand = clsCommands( 'ChillerEquipmentCommands.txt', strdevnamelist )


    # 
    # configuration of the running routine
    # 

    self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', strdevnamelist )

    # last temperature value for liquid from thermocouple, needed for humidity sensor 
    # if liquid temperature is lower than 0., humidity cannot be too high.
    self._fltTempLiquid = 0.
    time.sleep(2)

# ------------------------------------------------------------------------------
# Function: sendcommand --------------------------------------------------------
  def sendcommand(self, strusercommand,intStatusCode) :
    """
      function to send command to any of a device
    """
    try:
      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( strusercommand )
      logging.debug('sending command %s %s %s' % (strdevname, strcmdname, strcmdpara) )
      self._istDevHdl.readdevice( strdevname, strcmdname, strcmdpara)
    except:
      if self._intSystemStatus < StatusCode.ERROR or intStatusCode.value < 2: 
        self._intSystemStatus = StatusCode.ERROR
        intStatusCode.value = 2
      raise ValueError('Could not find user command: %s in %s' % (strusercommand, self._istCommand.cfgname() ))


# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump in emergency --------------------------------
  def eShutdownChillerPump (self,queue,intStatusCode) :
    """
      Emergency Shut down
    """
    p_config(queue)
    logging.info( self._strclassname + ' Chiller Pump Need to shut down due to emergency!!! ')
    self._intSystemStatus = StatusCode.FATAL
    intStatusCode.value = 4
    self.shutdownChillerPump(intStatusCode)


# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump ---------------------------------------------
  def shutdownChillerPump (self,queue,intStatusCode) :
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
    print("**********     BEGINNING SHUTDOWN")
    strPumpStopRPM = '10'
    strChiStopTemp = '20'
    try:
      strPumpStopRPM = self._istRunCfg.get( 'Pump', 'StopRPM' )
      strChiStopTemp = self._istRunCfg.get( 'Chiller', 'StopTemperature' )
    except:
      if intStatusCode.value < StatusCode.WARNING: 
        intStatusCode.value = StatusCode.WARNING
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
      self.sendcommand(self, strcommand, intStatusCode )

      # write information into logging file
      logging.info( strlog );

      # wait for 1 seconds after each command
      time.sleep(1) 

      # for non emergency shutdown, first cool down the chiller before shutting down the whole system 
      if intStatusCode.value < StatusCode.FATAL and 'cChangeSetpoint' in strcommand :
        intTimeCool = 600 # in seconds 
        try : 
          intTimeCool = 60 * int( self._istRunCfg.get( 'Chiller', 'StopCoolTime' ) ) # parameter in minutes
        except :
          pass
        logging.info( 'Chiller cooling down for {:3d}'.format( intTimeCool // 60 ) + ' minutes ' ) 
        time.sleep( intTimeCool )

        #self._intSystemStatus = StatusCode.DONE
        intStatusCode.value = StatusCode.DONE

# ------------------------------------------------------------------------------
# Function: run one loop of Chiller Pump ---------------------------------------
  def runChillerPumpOneLoop(self,queue,intStatusCode, name = "Chiller") :
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
        #logging.info( ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        self.sendcommand(self, 'cChangeSetpoint=' + strTemperatureList[itemp],intStatusCode )

        logging.info( ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        for itime in range( int(strTimePeriodList[itemp]) ):
          logging.info( ' Chiller waiting at ' + str(itime) + 'th minute.' )

          #
          # sleep for one minute, check system status every second
          #
          for i in range( 60 ):
             # check second by second the status of the system
             if self._intSystemStatus > StatusCode.ERROR or intStatusCode.value > 2: return 
             time.sleep( 1 ) # in seconds


# ------------------------------------------------------------------------------
# Function: run Chiller Pump ---------------------------------------------------
  def runChillerPump(self,queue,intStatusCode) :
    """
      main routine to run Chiller Pump with user set loops
    """
    p_config(queue)
    self.init(self,["Chiller","Pump"], runPseudo = False)


    logging.info("---------- Beginning Chiller Pump Loop ----------") 
    

# Start Pump and Chiller if necessary TODO: Make it conditional if they are already on
    self.sendcommand(self, 'cStart' ,intStatusCode)
    time.sleep(1)
    self.sendcommand(self, 'iStart',intStatusCode )
    time.sleep(1)



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
    self.sendcommand(self, 'iUnlockDrive',intStatusCode )
    self.sendcommand(self, 'iUnlockParameter' ,intStatusCode)
    self.sendcommand(self, 'iRPM=' + strPumpRunRPM ,intStatusCode)
 
    for strsectionname in [ name for name in self._istRunCfg.sections() if "Chiller" in name ]:
      self.runChillerPumpOneLoop(self,queue, intStatusCode, name = strsectionname)

      # constantly check the status of the system 
      if self._intSystemStatus > StatusCode.ERROR or intStatusCode.value > 2: return 
    
    self.shutdownChillerPump(self,queue,intStatusCode)
# ------------------------------------------------------------------------------
# Function: record temperature -------------------------------------------------
  def recordTemperature(self,queue,intStatusCode) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """

    p_config(queue)
    print("**********     STARTING TEMP RECORDER")

    self.init(self,["Thermocouple"], runPseudo = False)

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
        logging.warning( self._strclassname + ' setting Frequency ' + str(intFrequency) + ' < 1. Set to 1.')
        intFrequency = 1
      elif intFrequency > intDataPerRead : 
        logging.warning( self._strclassname + ' setting Frequency ' + str(intFrequency) + ' > ' + \
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
    while ( intStatusCode.value <= 2) : 
      #
      # read thermocouple data, every read takes ~25 seconds for 29 data points
      # 
      self.sendcommand(self,'tRead',intStatusCode )

      for idata in range( intDataPerRead ) :
        if idata % intDataPerRead == 0 : 
          fltTempTup = list( istThermocouple.last( idata ) )
          #logging.data( 'Thermocouple T1: %5.2f, T2: %5.2f, T3: %5.2f, T4: %5.2f ' % \
          logging.info( '<DATA> Thermocouple T1: {:5.2f}, T2: {:5.2f}, T3: {:5.2f}, T4: {:5.2f} '.format( \
                        fltTempTup[0], fltTempTup[1], fltTempTup[2], fltTempTup[3]) )

          # keep on track the liquid temperature read out
          # needed by humidity function 
          self._fltTempLiquid = fltTempTup[ intIdxTLiquid ]

          if self._fltTempLiquid < fltTLowerLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' < lower limit ' + fltTLowerLimit + '! Return! ')
            self._intSystemStatus = StatusCode.PANIC
            intStatusCode.value = 3

          if self._fltTempLiquid > fltTUpperLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' > upper limit ' + fltTUpperLimit + '! Return! ')
            self._intSystemStatus = StatusCode.PANIC
            intStatusCode.value = 3
    # after finishing running
    logging.info( self._strclassname + ' Temperature finished recording. ' )

# ------------------------------------------------------------------------------
# Function: record humidity ----------------------------------------------------

  def recordHumidity(self,queue,intStatusCode) :
    """
      recording the humidity inside the box
    """
    p_config(queue)
    #### self.init(self)
    self.init(self,["Humidity"], runPseudo = False)
    time.sleep(1)
    fltStopUpperLimit = 5.0 # upper limit in % for humidity to stop the system
    fltWarnUpperLimit = 2.0 # upper limit in % for humidity to warn the system
    intFrequency      =  10 # one data point per ? seconds

    try: 
      fltStopUpperLimit = float( self._istRunCfg.get( 'Humidity', 'StopUpperThreshold' ) )
      fltWarnUpperLimit = float( self._istRunCfg.get( 'Humidity', 'WarnUpperThreshold' ) )
      intFrequency      = int  ( self._istRunCfg.get( 'Humidity', 'Frequency' ) )
      if intFrequency < 1:
        logging.warning( self._strclassname + ' Humidity reading frequency ' + str( intFrequency ) + '! set to 1.')
        intFrequency = 1
    except:
      pass

    istHumidity = self._istDevHdl.getdevice( 'Humidity' )
    if istHumidity is None:
      logging.error( self._strclassname + ' Humidity not found in device list! ')
      return
  
    while(intStatusCode.value <= 2 ) :
      self.sendcommand(self, 'hRead',intStatusCode )
      fltHumidity = istHumidity.last() 
      #logger.log(logging.INFO, '<DATA> Humidity {:4.1f}'.format( fltHumidity ))
      logging.info( '<DATA> Humidity {:4.1f}'.format( fltHumidity ) )
      if self._fltTempLiquid < 0.:
        #logging.info( '<DATA> Humidity {:4.1f}'.format( fltHumidity ) )
        if fltHumidity > fltStopUpperLimit : 
          logging.error( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                         ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + 
                         '% upper limit! Return! ')
          self._intSystemStatus = StatusCode.PANIC
          intStatusCode.value = 3
          return
        elif fltHumidity > fltWarnUpperLimit : 
          logging.warning( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                           ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + '%')
          self._intSystemStatus = StatusCode.ERROR
          intStatusCode.value = 3

      time.sleep( intFrequency - 1 )
    logging.info( self._strclassname + ' Humidity finished recording. ' )

# -----------------------------------------------------------------------------
def runRoutine( runPseudo = False ) :
  """
    Run main routine
  """
  queue = mp.Queue(-1)
  intStatusCode = Value('i',0)
  print("**********     STATUS(globalcode): " +str(intStatusCode.value))
    
    #
    # run preset Chiller and Pump routine using two separated processing
    # one for Chiller Pump running,
    # the other for Temperature and Humidity recording
    # 
   
    #self.recordTemperature(queue, intStatusCode)
    #self.recordHumidity(queue, intStatusCode)

  #istThermoRun = clsChillerRun(["Thermocouple"], runPseudo = runPseudo)
  #istHumideRun = clsChillerRun(["Humidity"], runPseudo = runPseudo)

  mpList = []
  mpList.append( mp.Process(target = procListener,name = 'Listener', args =(queue,))) 
  mpList.append( mp.Process(target = clsChillerRun.recordTemperature,name = 'Temp Rec', args =(clsChillerRun,queue,intStatusCode,)) )
  mpList.append( mp.Process(target = clsChillerRun.recordHumidity,name = 'Humi Rec', args =(clsChillerRun,queue,intStatusCode,)) )
  mpList.append( mp.Process(target = clsChillerRun.runChillerPump,name = 'run Chill', args =(clsChillerRun,queue,intStatusCode,)) )
    
  print("**********     BEGINNING PROCESSES")
  for p in mpList:
    p.start()
    print("**********     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive()))
    time.sleep(5)





  print("**********     WAITING FOR SHUTDOWN TRIGGER")
  mpList[3].join()


    # shutdown Chiller and Pump
 

  print("**********     CHILLER SHUTDOWN, TERMINATING REMAINING PROCESSES")
  time.sleep(30) #Time for both of the logging devices to shut down

    # stops the Listener; Temperature and Humidity recorders are killed if they did not shut down properly
  mpList[1].terminate()
  mpList[2].terminate()
  mpList[0].terminate()

  print("**********     ALL PROCESSES ARE SHUTDOWN! HAVE A NICE DAY!")


def main():
  """
    test running the whole routine
  """
  intro()


  logging.basicConfig(filename='test.log',
                      #stream=sys.stdout,  
                      level=logging.DEBUG, \
                      format='%(asctime)s %(levelname)s: %(message)s', \
                      datefmt='%m/%d/%Y %I:%M:%S %p')
 

  runPseudo = False
  #runPseudo = True
  #if '-pseudo' in sys.argv[1:]
    #runPseudo = True
  #tc = clsChillerRun( runPseudo )
  #tc.runRoutine()
  runRoutine()


if __name__ == '__main__' : 
  mp.set_start_method('spawn')
  main()

