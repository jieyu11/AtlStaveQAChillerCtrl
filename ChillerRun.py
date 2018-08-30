"""
Class clsChillerRun
	
  Description: 
  	A Python script to control run routine of the chiller, data recording of the 
    thermocouples and humidity readout.
  
  Authors and contacts:
  	J. Yu  Iowa State University,  USA  jieyu@iastate.edu
  	W. Heidorn Iowa State Univiersity, USA wheidorn@iastate.edu


  Notes:
  
  Dictionary of abbreviations: 
"""
# ------------------------------------------------------------------------------
# Import section ---------------------------------------------------------------

import logging          # Needed for logging to occur
import logging.handlers # Needed for multiprocess logging with a file handler
import time             
import sys
from enum import IntEnum
from functools import total_ordering
from datetime import timedelta 

# User Macros
from ChillerRdDevices import * #Allows reading from devices
from ChillerRdConfig  import * #Configures devices
from ChillerRdCmd     import * #Configures commands
from SendEmails       import * #Configures email sender

@total_ordering

# ------------------------------------------------------------------------------
# Class StatusCode -------------------------------------------------------------

class StatusCode (IntEnum) :
  """
    This defines is the value that is used for the global intStatusCode
    which will signal shutdown and type of shutdown
  """
  OK        = 0  # -> all devices are fine
  SHUTDOWN  = 1  # -> User puts the system into a normal shutdown
  ERROR     = 2  # -> Puts the system into a normal shutdown
  ABORT     = 3  # -> User turns off the Chiller and Pump right away
  FATAL     = 4  # -> Turns off the Chiller and Pump right away
  KILLED    = 5  # -> User kills program and all processes
  DONE      = 6  # -> Says that both the Chiller and Pump are both off, Kill all the processes

# ------------------------------------------------------------------------------
# Class SysSettings ------------------------------------------------------------

class SysSettings (IntEnum) :
  """
    This defines the first value of the global intSettings, which keeps track
    of the individual processes.
  """
  START     = 0 # System is starting
  ROUTINE   = 1 # System is running a routine
  HWAIT     = 2 # System is waiting for the humidity to decrease
  WAIT      = 3 # System is waiting for user commands
  SHUTDOWN  = 4 # System is shutting down
  DONE      = 5 # System is done shutting off

# ------------------------------------------------------------------------------
# Class SysSettings ------------------------------------------------------------

class Setting (IntEnum) :
  """
    This defines the values of the intSettings Array
  """
  STATE       = 0 
  TCHANGE     = 1 
  PCHANGE     = 2 
  TOGGLE    = 3 



# ------------------------------------------------------------------------------
# Class ProcessState -----------------------------------------------------------

class ProcessState (IntEnum) :
  """
    This defines the values of the global intStatusArray, which keeps track
    of the individual processes.
  """
  OK        = 0  # -> process has been activated, meaning it is running normally
  SLEEP     = 1  # -> process needs to be activated, otherwise it will cause a timeout warning
  DEAD      = 2  # -> process has not been activated for 60 seconds. Or it has
                      #had a terminal error. It is now considered dead and the
                      #system will be put in the appropriate shutdown state
  HOLD      = 3  # -> a process is currently waiting to be reactivated
  ERROR1    = 4  # -> process has a specific error currently used for frost warnings



# ------------------------------------------------------------------------------
# Class ProcessList ------------------------------------------------------------

class Process (IntEnum) :
  """
      Gives the integer value for each process 
  """
  LISTENER  = 0
  TEMP_REC  = 1
  HUMI_REC  = 2
  CHILLER   = 3
  PUMP      = 4
  ARDUINO   = 5
  ROUTINE   = 6
  WATCHDOG  = 7

# Delta Time -------------------------------------------------------------------
def lstDeltaTime(fltElapsedTime):
  """
  Compute the given elapsedTime in units of days, hours and minutes. The input
  is assumed to be in units of seconds.
  timedelta returns days and seconds.
  divmod returns [quotient, remainder].
  This function returns list of [day, hour, minute].
  """
  lstTime = timedelta(seconds=fltElapsedTime)       # Instance of timedelta.
  intDays = lstTime.days                            # Pull out number of days.
  intHours, fltMins = divmod(lstTime.seconds,3600)  # Get [hours, seconds]
  fltMins = fltMins/60

  return [intDays, intHours, fltMins]

# ------------------------------------------------------------------------------
# Class ChillerRun -------------------------------------------------------------
class clsChillerRun : 
  """
    Class to provide user interfaces for:
    * Running the Chiller Pump system routine
    * Recording temperature and humidity values
    * Shutdown Chiller Pump system
    * Close Thermocouple and Humidity readout 
    * Communication between processes
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
  def funcInitialize(self, strDevNameList, bolRunPseudo,intStatusCode) : 
    '''
    This is funcInitializeialized at the start of each running process. In each process the
    devices are stated in the funcInitializeialization and their configuration occurs. If 
    this is not done in the local process or done in a separate process the
    devices will not communicate!!!
    '''
    if intStatusCode.value > StatusCode.OK: return
    self._strclassname = '< RUNNING >' 
    try:
      if strDevNameList != ['Routine']:

        # configuration of how the devices are connected to the PC
        self._istConnCfg = clsConfig( 'ChillerConnectConfig.txt', strDevNameList)

        # pass the configuration of how the devices connection
        # to the device handler
        
        self._istDevHdl = clsDevicesHandler( self._istConnCfg, strDevNameList,bolRunPseudo )

        # interpretation of machine readable commands into human readable commands
        # and vice versa
        self._istCommand = clsCommands( 'ChillerEquipmentCommands.txt', strDevNameList)

        # configuration of the running routine 
        self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', strDevNameList )

      else:
        self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', ['Chiller'] )

    except:
      logging.fatal("FAILED TO INITIALIZE "+str(strDevNameList)+" Aborting! Please check connections!")
      intStatusCode.value = StatusCode.DONE

# ------------------------------------------------------------------------------
# Function: sendcommand --------------------------------------------------------
  def sendcommand(self, strUserCommand,intStatusCode,fltTemps) :
    """
      function to send command to any of the devices
    """
    logging.debug(' Start to send user command ' + strUserCommand )
    strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( strUserCommand )
    logging.debug('sending command %s %s %s' % (strdevname, strcmdname, strcmdpara) )
    if strdevname == 'Chiller':
      logging.debug('<==========||==Sent Command to Chiller')
    bolCommandSent = False
    nAttempts = 0
    while bolCommandSent == False: #Send Command Loop
      try:  #Try to send a command if it fails or gives an error try again. After 3 fails it kills everything
        self._istDevHdl.readdevice( strdevname, strcmdname, strcmdpara,fltTemps)
        bolCommandSent = True

      except:
        logging.info(' Send Command Failure! %s %s %s' % (strdevname, strcmdname, strcmdpara))
        nAttempts += 1
        time.sleep(1)
      if nAttempts > 2:
        intStatusCode.value = StatusCode.FATAL
        bolCommandSent = True

# -----------------------------------------------------------------------------
# Listener Process ------------------------------------------------------------
  def procListener (self, queue, intStatusArray,strLogName) :
    """
      Process that reads the queue and then puts whatever read to the log file
      with a name strLogName.
    """
    root = logging.getLogger()# Defines the logger
    h = logging.FileHandler(strLogName,'a')
    f = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')# Creates format of all logged material
    h.setFormatter(f)# Sets format of the handler
    root.addHandler(h) #Adds the handler to the logger
    while True:
      self.funcResetDog(Process.LISTENER,intStatusArray)
      try:
        # This sets conditions to quit the procListener process when the listener recieves None in the queue.
        record = queue.get()
        if record is None:
          break
        logger = logging.getLogger(record.name) #This finds the name of the log in the queue
        logger.handle(record) # Handles the log, printing it to the strLogName File

        if "TempReadings" in record.message: #Ignores reading out full temp log
          continue
        else:
          print(record.asctime + " "+ record.levelname+" "+record.message) # Prints the log to the screen
      except Exception:
        import sys, traceback
        print('Whoops! Problem:', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# Function: process_configure -------------------------------------------------
  def funcLoggingConfig(queue,intLoggingLevel) :
    """
       function that must be present in any process that uses the logger
    """
    h = logging.handlers.QueueHandler(queue) #Connects the handler to the main queue
    root = logging.getLogger() #Creates a new logging process root
    root.addHandler(h) # Connects the logging process to the handler
    root.setLevel(intLoggingLevel) # This sets what level is logged in each process

# ------------------------------------------------------------------------------
# Temperature Process ----------------------------------------------------------
  def recordTemperature(self,queue,intStatusCode,intStatusArray,fltTemps,intLoggingLevel,bolRunPseudo) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """
    print ("STARTING THERMO")
    #Connect to logger and initialize
    self.funcLoggingConfig(queue,intLoggingLevel)
    self.funcInitialize(self,["Thermocouple"], bolRunPseudo,intStatusCode)

    # Default values
    fltTUpperLimit =  50 # upper limit in C for liquid temperature
    fltTLowerLimit = -55 # lower limit in C for liquid temperature
    intFrequency   =  29 # one data point per ? seconds
    intDataPerRead =  29 # number of data points every time user read, ~1 data point / 1 second
    intIdxTLiquid  =   0 # index of the thermocouple connected to liquid temperature, 0 - 3

    try:  #Try to load values from the run config file
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
        logging.fatal( self._strclassname + ' IdxLiquidTemperature '+ intIdxTLiquid + ' not in [0, 3]. Check! ')
        intStatusCode.value = StatusCode.ABORT
        return
    except:
      logging.warning( ' Section: Thermocouple, Key: LiquidUpperThreshold, LiquidLowerThreshold, Frequency not found! Using defaults!')
         
    istThermocouple = self._istDevHdl.getdevice( 'Thermocouple' )
    if istThermocouple is None:
      logging.fatal( self._strclassname + ' Thermocouple not found in device list! ')
      intStatusCode.value >= StatusCode.ABORT
      return

    # keep reading data until the process is killed or 
    # kill the process if the global status is more serious than an SHUTDOWN
    while ( intStatusCode.value < StatusCode.KILLED) : 
      self.funcResetDog(Process.TEMP_REC,intStatusArray)
      # read thermocouple data, every read takes ~25 seconds for 29 data points
      self.sendcommand(self,'tRead',intStatusCode,fltTemps)

      for idata in range( intDataPerRead ) :
          fltTempTup = list( istThermocouple.last( idata) ) 
          logging.info( '<DATA> TempReadings T1: {:5.2f}, T2: {:5.2f}, T3: {:5.2f}, T4: {:5.2f} '.format( \
                        fltTempTup[0], fltTempTup[1], fltTempTup[2], fltTempTup[3]) ) 

          for i in range(4): #Adds the current temperatures into the global temps
            fltTemps[i+2]=fltTempTup[i]
          
          # keep on track the liquid temperature read out
          # needed by humidity function 
          self._fltTempLiquid = fltTempTup[ intIdxTLiquid ]

          if self._fltTempLiquid < fltTLowerLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' < lower limit ' + fltTLowerLimit + '! Return! ') 
            intStatusCode.value = StatusCode.ERROR

          if self._fltTempLiquid > fltTUpperLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' > upper limit ' + fltTUpperLimit + '! Return! ') 
            intStatusCode.value = StatusCode.ERROR
      logging.info('<DATA> Temps TSet: {:5.2f}, TRes: {:5.2f}, T1: {:5.2f}, T2: {:5.2f}, T3: {:5.2f}, T4: {:5.2f} '.format( \
                    fltTemps[0],fltTemps[1],fltTemps[2],fltTemps[3],fltTemps[4],fltTemps[5]) )
    # after finishing running
    logging.info( self._strclassname + ' Temperature finished recording. ' )

# ------------------------------------------------------------------------------
# Humidity Process -------------------------------------------------------------
  def recordHumidity(self,queue,intStatusCode,intStatusArray,intSettings,fltTemps,fltHumidity,intLoggingLevel,bolRunPseudo) :
    """
      recording the humidity inside the box
    """
    # Connect to logger and initialize
    self.funcLoggingConfig(queue,intLoggingLevel) 
    self.funcInitialize(self,["Humidity"], bolRunPseudo,intStatusCode)

    time.sleep(20) # Wait

    #Default values
    fltStopUpperLimit = 5.0 # upper limit in % for humidity to stop the system
    fltWarnUpperLimit = 2.0 # upper limit in % for humidity to warn the system
    intFrequency      =  30 # one data point per ? seconds

    try: 
      fltStopUpperLimit = float( self._istRunCfg.get( 'Humidity', 'StopUpperThreshold' ) )
      fltWarnUpperLimit = float( self._istRunCfg.get( 'Humidity', 'WarnUpperThreshold' ) )
      intFrequency      = int  ( self._istRunCfg.get( 'Humidity', 'Frequency' ) )
      if intFrequency < 1:
        logging.warning( self._strclassname + ' Humidity reading frequency ' + str( intFrequency ) + '! set to 1.')
        intFrequency = 1
    except:
      logging.warning("Section: Humidity, Key: StopUpperThreshold, WarnUpperThreshold, or Frequency, not found! Using defaults!")

    istHumidity = self._istDevHdl.getdevice( 'Humidity' )
    if istHumidity is None:
      logging.fatal( self._strclassname + ' Humidity not found in device list! ')
      intStatusCode.value = StatusCode.FATAL
      return
  
    oldSetting = [0,0] #Initial conditions

    while(intStatusCode.value < StatusCode.KILLED ) :
      self.funcResetDog(Process.HUMI_REC,intStatusArray)

      self.sendcommand(self, 'hRead',intStatusCode,fltTemps)
      fltHum = istHumidity.last()
      #TODO Make this also read out temperature data...
 
      logging.info( '<DATA> Humidity {:4.1f}'.format( fltHum ) )

      fltHumidity.value = fltHum #Sets global humidity

      # Warn or Set the system into a humidity wait due to high humidty
      if fltTemps[0] < 0. and intSettings[Setting.STATE] != SysSettings.HWAIT:
        if fltHumidity.value > fltStopUpperLimit: 
          logging.warning( self._strclassname + ' Chiller temp setting '+ str( fltTemps[0] ) +
                           ' box humidity ' + str( round(fltHumidity.value,1) ) + ' % > ' + str( fltStopUpperLimit ) + 
                           ' %! System will wait for humidity to decrease!') 
          oldSettings = [intSettings[Setting.STATE],fltTemps[0]]
          intSettings[Setting.STATE]= SysSettings.HWAIT #This puts the system into a humidity wait
          fltTemps[0] = 0.0 
          intSettings[Setting.TCHANGE] = True
        elif fltHumidity.value > fltWarnUpperLimit : 
          logging.warning( self._strclassname + ' Chiller temp setting '+ str( fltTemps[0] ) +
                           ' box humidity ' + str( round(fltHumidity.value,1) ) + ' % > ' + str( fltWarnUpperLimit ) + ' %') 
      # If we are not meeting the over humidity statement go back to normal
      elif intSettings[Setting.STATE] == SysSettings.HWAIT and intStatusCode.value == StatusCode.OK:
        intSettings[Setting.STATE] = oldSettings[0]
        fltTemps[0] = oldSettings[1]
        intSettings[Setting.TCHANGE] = True

      time.sleep( intFrequency - 1 )
    logging.info( self._strclassname + ' Humidity finished recording. ' )

# ------------------------------------------------------------------------------
# Chiller Process --------------------------------------------------------------
  def chillerControl(self,queue,intStatusCode,intStatusArray,intSettings,fltTemps,intLoggingLevel,bolRunPseudo) :
    """
      control the chiller
    """
    # Connect to logger and initialize
    self.funcLoggingConfig(queue,intLoggingLevel) 
    self.funcInitialize(self,["Chiller"], bolRunPseudo,intStatusCode)
    istTemp = self._istDevHdl.getdevice( 'Chiller' )

    #Turn on Chiller
    self.sendcommand(self, 'cStart',intStatusCode,fltTemps)
    logging.info ( self._strclassname + ' Chiller started. ')

    #Chiller idles 
    while intStatusCode.value < StatusCode.ABORT:
      #Check To Exit Loop
      if intSettings[Setting.STATE] > SysSettings.SHUTDOWN:
        break
      #Change Temperature
      elif intSettings[Setting.TCHANGE] == True:
        NewTemp = fltTemps[0]
        self.sendcommand(self, 'cChangeSetpoint=' + str(NewTemp), intStatusCode,fltTemps)
        intSettings[Setting.TCHANGE] = False
      #Do the idle thing(Check Chiller, and Read Temperature)
      else:
        self.sendcommand(self, 'cAlarmStat?', intStatusCode,fltTemps)

        if intStatusCode.value > StatusCode.ERROR: break
        self.sendcommand(self, 'cGetResTemp?',intStatusCode,fltTemps)
        ReservoirTemp = istTemp.last()
        fltTemps[1] = ReservoirTemp  #TODO Needs to be tested...

        if intStatusCode.value > StatusCode.ERROR: break
        time.sleep(2.8) #This may not be necessary
        self.funcResetDog(Process.CHILLER,intStatusArray)

    #Shutdown chiller
    time.sleep(5)
    self.sendcommand(self,'cStop',intStatusCode,fltTemps)
    logging.info( self._strclassname + ' Chiller finished shutdown. ') 

# ------------------------------------------------------------------------------
# Pump Process -----------------------------------------------------------------
  def pumpControl(self,queue,intStatusCode,intStatusArray,intSettings,fltTemps,fltRPS,intLoggingLevel,bolRunPseudo) :
    """
    control the pump  
    """
    # Connect to logger and initialize
    self.funcLoggingConfig(queue,intLoggingLevel) 
    self.funcInitialize(self,["Pump"], bolRunPseudo,intStatusCode)

    #Turn on Pump
    StartComs = ['iUnlockDrive','iUnlockParameter','iRPS=10','iStart']
    for Command in StartComs:
      self.sendcommand(self, Command,intStatusCode,fltTemps)
      time.sleep(1)
    logging.info ( self._strclassname + ' Pump started. ')

    #Pump idles 
    while intStatusCode.value < StatusCode.ABORT:
      #Check To Exit Loop
      if intSettings[Setting.STATE] > SysSettings.SHUTDOWN: break
      #Change RPS
      elif intSettings[Setting.PCHANGE] == True:
        NewRPS = fltRPS[0]
        self.sendcommand(self, 'iRPS=' + str(NewRPS), intStatusCode,fltTemps)
        intSettings[Setting.PCHANGE] = False
        time.sleep(5)
        self.funcResetDog(Process.PUMP,intStatusArray)
      #Do the idle thing(Check Pump, Wait)
      else:
        self.sendcommand(self, 'iStatus?', intStatusCode,fltTemps)
        if intStatusCode.value > StatusCode.ERROR: break
        time.sleep(5) #This may not be necessary
        self.funcResetDog(Process.PUMP,intStatusArray)

    #Shutdown pump
    self.sendcommand(self,'iStop',intStatusCode,fltTemps)
    logging.info( self._strclassname + ' Pump finished shutdown. ')



# ------------------------------------------------------------------------------
# Arduino Process --------------------------------------------------------------
  def procArduino(self,queue,intStatusCode,intStatusArray,intSettings,fltTemps,fltRPS,intLoggingLevel,bolRunPseudo) :
    """
    control the arduino  
    """

    # Connect to arduino UNO and initialize
    self.funcLoggingConfig(queue, intLoggingLevel)
    self.funcInitialize(self,["Arduino"],bolRunPseudo,intStatusCode)

    istArduino = self._istDevHdl.getdevice( 'Arduino' )
    while intStatusCode.value < StatusCode.KILLED:
      #Change valve state
      if intSettings[Setting.TOGGLE] == True:
        logging.info( self._strclassname + 'Toggling valve state.')
        self.sendcommand(self, 'aToggle',intStatusCode,fltTemps)
        intSettings[Setting.TOGGLE] = False

      #Do the idle thing (Read current RPS, Wait)
      else:
        self.sendcommand(self, 'aRPS?',intStatusCode,fltTemps)
        fltRps = istArduino.last()
        self.funcResetDog(Process.ARDUINO,intStatusArray)
        if fltRps < 0.7:
          logging.info( '<DATA> Arduino AprxFlRt = {:4.1f} l/min'.format( fltRps ) )
        else:
          logging.info( '<DATA> Arduino FlowRate = {:4.2f} l/min'.format( fltRps ) )
        fltRPS[1] = float(fltRps)
        if intStatusCode.value > StatusCode.FATAL:
          break

        #TODO Add in a check for pump settings vs flow rate... 
        # probably not necessary until actuator valves are in
        
        time.sleep(5)

    logging.info('< RUNNING > Arduino finished shutdown. ') 

# ------------------------------------------------------------------------------
# Routine Process --------------------------------------------------------------
  def procRoutine(self,queue,intStatusCode,intStatusArray,intSettings,fltTemps, \
                  fltHumidity,fltRPS,fltProgress,intLoggingLevel,bolWaitInput,bolRoutine,bolRunPseudo,fltStartTime):
    """
      main routine to run Chiller Pump with user set loops
    """

    # Configures the processes handler so that it will log
    self.funcLoggingConfig(queue,intLoggingLevel)
    self.funcInitialize(self,["Routine"],bolRunPseudo,intStatusCode)


    #Start Up Check
    if intSettings[Setting.STATE] == SysSettings.HWAIT: #Check humidity state and wait if necessary
      while intStatusCode.value == StatusCode.OK and intSettings[Setting.STATE] == SysSettings.WAIT:
        time.sleep(5)
        self.funcResetDog(Process.ROUTINE,intStatusArray)
        if intSettings[Setting.TCHANGE] == True and bolWaitInput == True:
          self.funcTempWait (self,1, intStatusCode, intStatusArray, intSettings, fltTemps, bolWaitInput)

    if bolRoutine == True:

      time.sleep(5) #Wait to start the routine after everything has been started
      #Load routine ------------
      intSettings[Setting.STATE] =SysSettings.ROUTINE
      #Get number of loops
      intChiNLoops  = 0
      name = 'Chiller'
      try:
        intChiNLoops  = abs(int( self._istRunCfg.get( name, 'NLoops' ) ) )
      except:
        logging.fatal("Sections: "+ name + ", Key: NLoops not present in configure: %s" % \
                       self._istRunCfg.name())
        intStatusCode.value = StatusCode.FATAL
        return
      logging.info("---------- Section: "+ name + ", number of loops " + str(intChiNLoops) )    

      #Get Temperature and Time Period Lists
      try:
        # split values by ',' and then remove the white spaces.
        strTemperatureList = [ x.strip(' ') for x in self._istRunCfg.get( name, 'Temperagures' ).split(',') ]
        strTimePeriodList  = [ x.strip(' ') for x in self._istRunCfg.get( name, 'TimePeriod'   ).split(',') ]
      except:
        logging.fatal("Section: "+ name + ", Key: Temperagures, TimePeriod not present in configure: %s" % \
                       self._istRunCfg.name() )
        intStatusCode.value = StatusCode.FATAL 
        return

      #Check List Lengths and cut to minimum
      intNTemperature = len( strTemperatureList )
      if intNTemperature != len(strTimePeriodList) :
        logging.warning( ' Length of temperature list ' + str(intNTemperature) + ' != ' + \
                         ' Length of time period list ' + str( len( strTimePeriodList ) ) + '. Set to Minimum' )
        if len( strTimePeriodList ) < intNTemperature :
          intNTemperature = len( strTimePeriodList )

      #Begin Looping
      fltProgressStep = float(100 / (intChiNLoops * intNTemperature))   
      for iloop in range(intChiNLoops) :
        logging.info('----------     Begin routine loop no. ' + str(iloop+1)+'/'+str(intChiNLoops) )
        for itemp in range(intNTemperature) :
          # changing the Chiller Temperature to a corresponding value
          fltTemps[0] = float(strTemperatureList[itemp]) #Change Set Temperature
          intSettings[Setting.TCHANGE] = True
          fltRPS[0] = self.funcPumpSetting(1,strTemperatureList[itemp]) #Change Pump Setting so its at 1 l/min
          intSettings[Setting.PCHANGE] = True
 
          # Begin waiting to reach the set temperature        
          self.funcTempWait (self,1, intStatusCode, intStatusArray, intSettings, fltTemps, bolWaitInput) 
          self.funcResetDog(Process.ROUTINE,intStatusArray)

          # Wait at set temp
          if intStatusCode.value == StatusCode.OK and bolWaitInput == False:
            logging.info(self._strclassname + ' Chiller at set temp. Waiting ' + strTimePeriodList[itemp] + ' minutes.')
            for i in range( 12 * int(strTimePeriodList[itemp])):
              if intStatusCode.value > StatusCode.OK: break
              time.sleep(5) 
              self.funcResetDog(Process.ROUTINE,intStatusArray)
          fltProgress.value += fltProgressStep
      logging.info('----------     Chiller, Pump looping finished!' )

    # Wait ---------------------
    else:
      intSettings[Setting.STATE] = SysSettings.WAIT
      fltProgress.value = 100
    while intStatusCode.value == StatusCode.OK and \
         (intSettings[Setting.STATE] == SysSettings.WAIT or intSettings[Setting.STATE] == SysSettings.HWAIT):
      time.sleep(5)
      self.funcResetDog(Process.ROUTINE,intStatusArray)
      if intSettings[Setting.TCHANGE] == True and bolWaitInput == True:
        self.funcTempWait (self,1, intStatusCode, intStatusArray, intSettings, fltTemps, bolWaitInput)

    #Shutdown
    intSettings[Setting.STATE] = SysSettings.SHUTDOWN
    if intStatusCode.value < StatusCode.ABORT:
      fltTemps[0] = 22 #Room Temperature
      intSettings[Setting.TCHANGE] = True
      self.funcTempWait (self,1, intStatusCode, intStatusArray, intSettings, fltTemps, bolWaitInput)
    fltRPS[0] = 10 #Slow RPSs
    intSettings[Setting.PCHANGE] = True
    time.sleep(5)

    #Tell All processes its time to shut off
    intStatusCode.value = StatusCode.DONE
    intSettings[Setting.STATE] = SysSettings.DONE
    logging.info('< RUNNING > Routine process finished.')


# Function: Stave Temp ---------------------------------------------------------
  def funcStaveTemp (fltTemps):
    """
    gives the temperature of the stave
    """ 
    fltStaveTemp = (fltTemps[2]+fltTemps[3])/2 #This reads temperature from the thermocouples
    if fltStaveTemp == 20:
      fltStaveTemp = fltTemps[1] #if nothing has updated use the temperature read by the chiller
    return fltStaveTemp

# Function: Temp Wait ----------------------------------------------------------
  def funcTempWait (self,intTime, intStatusCode, intStatusArray, intSettings, fltTemps, bolWaitInput):
    """
    This checks to see when the fluid temperature gets to the set temperature
    """

    Tancient = 0 #Oldest Temp Change
    Told = 0 #Next oldest Temp Change

    while True: #This loop stays until it is broken
      intWaitTime = intTime #Time to wait between checks to reach temperature should be >30seconds
      
      fltSetTemp = fltTemps[0]
      fltStaveTemp = self.funcStaveTemp(fltTemps)
      Tslope = 1000
      TslopeLevel = 0.1 # C/min

      intMaxWait = 90 # max time to wait before chiller ends the wait.      
      intCurrentWait = 0

      intFirstWait = 4 # Time to wait before checking for slope
      #Wait for 5 min for the chiller to start cooling stave
      logging.info( "< RUNNING > Changing Temperature from " + str(round(fltStaveTemp,2))+ " C to Tset: "\
                      + str(round(fltSetTemp,2))+ " C over 4 min")
      for i in range(2*intFirstWait): # 10 runs of 30seconds
        for j in range(6): # Check every 5 seconds  
          if intStatusCode.value > StatusCode.ERROR or \
              ((intStatusCode.value == StatusCode.SHUTDOWN or intStatusCode.value == StatusCode.ERROR) \
                and intSettings[Setting.STATE] != SysSettings.SHUTDOWN): return
          elif fltSetTemp != fltTemps[0]: break #If the set temp changes go back to the beginning                  
          time.sleep(5)
          self.funcResetDog(Process.ROUTINE, intStatusArray)
        Tancient = Told
        Told = fltStaveTemp
        fltStaveTemp = self.funcStaveTemp(fltTemps)
        Tmean = (Tancient+Told+fltStaveTemp)/3
        Tslope = ((Tmean-fltStaveTemp)+(Tancient-Tmean))/2

      #Wait for the slope to level off
      while abs(Tslope) > TslopeLevel:
        fltStaveTemp = self.funcStaveTemp(fltTemps)
        Tmean = (Tancient+Told+fltStaveTemp)/3
        Tslope = ((Tmean-fltStaveTemp)+(Tancient-Tmean))/2

        logging.info( "< RUNNING > Routine waiting for abs.temp. slope to flatten. Current: "\
                      +str(round(abs(Tslope),2))+' > '+str(TslopeLevel)+"  [C/min]")
        Tancient = Told
        Told = fltStaveTemp
        for j in range(2):
          #Calculate slope for an untested value
          fltStaveTemp = self.funcStaveTemp(fltTemps) 
          Tmean = (Tancient+Told+fltStaveTemp)/3
          Tslope = ((Tmean-fltStaveTemp)+(Tancient-Tmean))/2 
          Tancient = Told
          Told = fltStaveTemp

          for i in range(6 * intWaitTime): #The actual waiting
            if intStatusCode.value > StatusCode.ERROR or \
              ((intStatusCode.value == StatusCode.SHUTDOWN or intStatusCode.value == StatusCode.ERROR) \
                and intSettings[Setting.STATE] != SysSettings.SHUTDOWN): return
            elif fltSetTemp != fltTemps[0]: break #If the set temp changes go back to the beginning                  
            time.sleep(5)
            self.funcResetDog(Process.ROUTINE, intStatusArray)
        if intCurrentWait >= intMaxWait:
          logging.info( "< RUNNING > Routine wait ended after "+ str(intCurrentWait)+" min. The system took too long!")
          logging.info( "< RUNNING > Stave reached Temperature " + str(round(fltStaveTemp,2))+ " C from Tset: "\
                         + str(round(fltSetTemp,2))+ " C")
          return          
        elif fltSetTemp != fltTemps[0]: break
      logging.info( "< RUNNING > Stave reached Temperature " + str(round(fltStaveTemp,2))+ " C from Tset: "\
                         + str(round(fltTemps[0],2))+ " C")
     
      # Check to notify and hold or end wait    
      if bolWaitInput == True and intStatusCode.value==StatusCode.OK and intSettings[Setting.STATE]!=SysSettings.SHUTDOWN:
        intStatusArray[Process.ROUTINE] = ProcessState.HOLD # Makes the watchdog ignore this process as it waits for user input
        logging.info("----------     The system is holding the current set Temp "+str(fltSetTemp)+" C")
        print("**********     USER:To Release, type release and hit enter")
        while intStatusArray[Process.ROUTINE] == ProcessState.HOLD and intStatusCode.value<=StatusCode.OK:
          if fltSetTemp != fltTemps[0]: break
          time.sleep(5) 
        if fltSetTemp != fltTemps[0]: break
        logging.info("----------     The system has been released.")
        return
      else: return

# Function: Pump Setting -------------------------------------------------------
  def funcPumpSetting (flowRate,fluidTemp):
    """
    This takes a wanted flow rate value of novec and the fluid temperature
    to calculate the required chiller pump setting
    """
    #This will need to be figured out... TODO
    return 22.0
 
# ------------------------------------------------------------------------------ 
# Process Watchdog -------------------------------------------------------------
  def procWatchDog (self,queue, intStatusCode, intStatusArray, intSettings, fltTemps,\
                    fltHumidity, fltRPS, fltProgress, bolSendEmail,\
                    intLoggingLevel,strStartTime,strStartTimeVal,procShortList):
    '''
      The Watchdog is the system protection protocol. It has 2 purposes,
      1. Keep track of error conditions.
      2. Notify the operators when end of run conditions are met or fatal errors.

      Errors
        The system currently is written to deal mainly with timeout errors, though
        it will be easy to add in more complicated errors as well.

        TimeOut- The global intStatusArray is used for this. Every 30 seconds the
        watchdog looks at each process's value on the intStatusArray and then sets
        the value to 0. In each process's routine, there is a function called
        ActivateDog, which sets the value to 1. If the value is still at 0 after 30 seconds
        the watchdog sends out a warning. After sending out the warning, the watchdog
        changes the value of intCurrentState. Currently there are 3 values for each
        process in this array.
        intCurrentState = OK, normal state
                          SLEEP, Timed out once!...
                          DEAD, Timed out twice!... 
            If process status is DEAD, send Email notice, and/or begin shutdown.

        Hold- The user or the routine can set a process into the hold state from
        the terminal. In a hold state a process does nothing other than wait
        some time and see if it is still in that state. This may allow the user to
        change a battery or cable connection with the device from the pc. (It
        worked for the thermocouples in earlier versions). Hold is also utilized
        by the Routine to allow the system to hold at a set temperature to wait
        for a user.

        Error1- This error is used by a few processes. If the humidity sensor has
        too high of a value and the temp settings are too low, the runChill will
        put the temperature into a higher setting and wait for the humidity to
        drop. If it doesn't in 10 minutes it will put the system into SHUTDOWN.

        Others- Currently there are no specific error codes, though using higher values of intStatusArray
        or intCurrentState could be used to give that information with the WackDog function
      Emailing
        This uses the SendMail.py macro to send emails. Once an email has been
        sent it will change sentMessage to True and not send any more... because
        the system will be waiting for personal intervention.  
    '''
    strWatchDog = '< WATCHDOG >'
    self.funcLoggingConfig(queue,intLoggingLevel)
    
    # Set up email system -------------
    if bolSendEmail == True:

      # Create Mailing List
      defaultMailList = ['wheidorn@iastate.edu']# Default mailing list
      self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', [])
      try: 
        mailList = [ x.strip(' ') for x in self._istRunCfg.get( 'Email', 'Users' ).split(',') ]
        if mailList[0] == '': #Check to make certain an email was added
          mailList = defaultMailList
      except:
        logging.warning('Unable to find email list in Config File, Using Default: wheidorn@iastate.edu')
        mailList = defaultMailList 
      logging.info(strWatchDog  +' Will notify: '+str(mailList))

    else:
      logging.info(strWatchDog +' Will notify: Local User')

    # Create email message shell
    def mail(strTitle,strMessage):
      """
      A quick definition of the messaging shell
      """
      if bolSendEmail == True:  
        strStatusText = self.strStatus(intStatusCode, intStatusArray, intSettings,\
                                       fltTemps, fltHumidity, fltRPS, fltProgress, strStartTime,\
                                       strStartTimeVal, procShortList)
        print('Sending Message: '+strTitle+': '+strMessage + str(strStatusText))
        for person in mailList: 
          clsSendEmails.funcSendMail(clsSendEmails,person,strTitle,strMessage + strStatusText)
          logging.info(strWatchDog+' Email sent to '+ person) 
          time.sleep(1)
      else:
        strStatusText = self.strStatus(intStatusCode, intStatusArray, intSettings,\
                                       fltTemps, fltHumidity, fltRPS, fltProgress, strStartTime,\
                                       strStartTimeVal, procShortList)
        print('Watchdog Message: '+strTitle+': '+strMessage + str(strStatusText))

    # Set up watchdog's current state array for all the processes

    strProcesses = [process.name for process in procShortList]

    #strProcesses = ['Listener','Temperature Recorder','Humidity Recorder','Chiller','Pump','Arduino','Routine']
    intCurrentState = [ProcessState.OK]*(len(strProcesses))
    sentMessage = False # Only want to send one email...

    intFrostCounter = 0 
    maxFrostTime = 60

    #The main watchdog loop ------------
    while intStatusCode.value < StatusCode.DONE:      
      logging.debug( strWatchDog + ' Checking all process statuses')
      i = 0
      for process in intStatusArray:
        #How to deal with a second timeout 
        if process == ProcessState.SLEEP and intCurrentState[i] == ProcessState.SLEEP:
          logging.error(strWatchDog+' PROCESS: '+ strProcesses[i]+' is still Timed Out!!!!')
          if i == Process.CHILLER:# If it is the chiller alert the authorities, but do not shutdown
            logging.error(strWatchDog+' PROCESS: '+strProcesses[i]+' Killing System! ALERT THE AUTHORITIES!!!')  
            mail('Major Error!!!!!!!!','The watchdog lost track of the Chiller and Pump control!!!!')
            sentMessage = True
            intCurrentState[i] = ProcessState.DEAD
          else:# If it is the logger, or one of the two recorders start shutdown
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessState.DEAD

        #How to deal with a single timeout
        elif process == ProcessState.SLEEP and intCurrentState[i] == ProcessState.OK: #Flags and Sends a timeout warning and sets the state to timed out
          logging.warning(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!!')
          intCurrentState[i] = ProcessState.SLEEP
          if i == Process.LISTENER:# If the listener times out, we should just put it into shutdown, because we will no longer be logging
            print(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!! Triggering Shutdown')
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessState.DEAD

        #Resetting all activated processes
        elif process == ProcessState.OK:
          intCurrentState[i] = ProcessState.OK

        elif process == ProcessState.HOLD and intCurrentState[i]==ProcessState.OK: #Flags and Sends a Chiller has been held message
          if i == Process.ROUTINE:
            logging.warning(strWatchDog+' Noticed routine was held. Sending Reminders!')
            mail('REMINDER!','The Chiller has reached the set temperature!')
          intCurrentState[i]=ProcessState.HOLD

        intStatusArray[i] = intCurrentState[i]
        #Resets all non error or higher process statuses to SLEEP
        if process == ProcessState.OK:        
          intStatusArray[i] = ProcessState.SLEEP
        i += 1 

        #How to deal with high humidity during a run
      if intSettings[Setting.STATE] == SysSettings.HWAIT: 
        logging.warning(strWatchDog+' FROST DANGER! The system will begin shutdown in '+ str((maxFrostTime- intFrostCounter)/2)+ ' min if the humidity does not drop. ')
        intFrostCounter += 1
        if intFrostCounter >= maxFrostTime:
          logging.error( strWatchDog+' PROCESS: '+strProcesses[i]+' Humidity did not drop soon enough. Begin Shutdown')
          intStatusCode.value = StatusCode.ERROR #Begin Normal shutdown
          
      #Final Messaging due to StatusCode ----
      for sec in range(30):
        time.sleep(1)
        if intStatusCode.value == StatusCode.SHUTDOWN and sentMessage == False:
          mail('SHUTDOWN Shutdown Triggered!!','The system is shutting down normally.'\
                +' The program was '+str(fltProgress.value)+' % complete.\n')
          sentMessage = True
        elif intStatusCode.value == StatusCode.ERROR and sentMessage == False:
          mail('ERROR Shutdown Triggered!!','The system is shutting down normally.'\
                +' The program was '+str(fltProgress.value)+' % complete.\n')
          sentMessage = True
        elif intStatusCode.value == StatusCode.ABORT and sentMessage == False:
          mail('ABORT Shutdown Triggered!!','The system was shut down.'\
                +' It has not had time to properly cool! The program was '+str(fltProgress.value)+' % complete.\n')
          sentMessage = True
        elif intStatusCode.value == StatusCode.FATAL and sentMessage == False:
          mail('FATAL Shutdown Triggered!!','The system was shut down due to a fatal error.'\
                +' It has not had time to properly cool! The program was '+str(fltProgress.value)+' % complete.\n')
          sentMessage = True
        elif intStatusCode.value == StatusCode.KILLED and sentMessage == False:
          mail("KILLED chiller control system!!","The system has not been shutdown, the program has. Somebody didn't want to wait!\n")
          sentMessage = True
        elif intStatusCode.value == StatusCode.DONE and sentMessage == False:
          mail('DONE Shutdown!!','The system has been shutdown. The program was completed with no fuss!\n')
          sentMessage = True

# Function: funcResetDog -------------------------------------------------------
  def funcResetDog (intProcess,intStatusArray): #Puts the WatchDog into OK, which stops an error
    '''
    Each process has an assigned spot in the intStatusArray. Every 30 seconds 
    the array is checked by the watchdog. The watchdog then sets all processes 
    spots to ProcessState.SLEEP. In each process loop there is funcResetDog that
    sets the spot to ProcessState.OK. 
    '''
    if intStatusArray[intProcess] == ProcessState.HOLD:
      while intStatusArray[intProcess] == ProcessState.HOLD and intProcess != Process.ROUTINE :
        time.sleep(1)
    intStatusArray[intProcess] = ProcessState.OK
 
# Function: strStatus ----------------------------------------------------------
  def strStatus(intStatusCode, intStatusArray, intSettings, fltTemps, fltHumidity, \
                fltRPS, fltProgress, gblstrStartTime, gblstrStartTimeVal, procShortList):
    '''
    returns a string that is the current status of the system
    '''
    strMessage = []
    strGlbStatus = ['OK      ','SHUTDOWN','ERROR   ','ABORT   ','FATAL   ','KILLED  ','DONE    ']
    strStatusVals = ['OK','Sleep','DEAD (:,()','Held']
    strSystemSetting = ['START','ROUTINE','HWAIT','WAIT','SHUTDOWN','DONE']

    fltRunningTime = round((time.time() - gblstrStartTimeVal),2)
    intDays, intHours, fltMins = lstDeltaTime(fltRunningTime)

    strMessage.append(f"     Program Started: {str(gblstrStartTime)}\n")
    strMessage.append(f"     Run Time       : {intDays} days, {intHours} hours, {round(fltMins,2)} minutes\n")
    strMessage.append(f"     Loop Progress  : {str(fltProgress.value)}%\n")
    strMessage.append(f"     Global Status  : {strGlbStatus[intStatusCode.value]}\n\n") 
    strMessage.append(f"     Current Setting: {strSystemSetting[intSettings[Setting.STATE]]}\n")

    #print(intStatusArray[0])
    i = 0
    for p in procShortList:
      if str(p.name) == 'WatchDog':
        continue
      strMessage.append("     Process: "+str(p.name)+ ' Status: '+strStatusVals[intStatusArray[i]]+'\n')          
      i+=1
    strMessage.append("     Process: Watchdog  Status: OK\n")
    strMessage.append("     Current Temps")
    i = 0
    strTempNames = ["TSet","TRes","T1  ","T2  ","T3  ","T4  ","SVal"]
    for p in fltTemps:
      strMessage.append("  "+ strTempNames[i] +": "+ str(round(p,1))+u"\u00B0C")
      i+=1
    strMessage.append("\n     Humidity: " + str(round(fltHumidity.value,2)) + " %")
    strMessage.append("\n Pump Setting: " + str(round(fltRPS[0],2)) + " rps")
    strMessage.append("    Flow Rate: " + str(round(fltRPS[1],2)) + " l/min")
    strMessage = ''.join(strMessage) 
    return strMessage

