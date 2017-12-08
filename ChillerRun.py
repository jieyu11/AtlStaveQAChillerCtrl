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
  OK      = 0  # -> all devices are fine
  ERROR   = 1  # -> Puts the system into a normal shutdown
  FATAL   = 2  # -> Turns off the Chiller and Pump right away
  DONE    = 3  # -> Says that both the Chiller and Pump are both off, Kill all the processes
#  def __lt__(self, other):
#    if self.__class__ is other.__class__:
#      return self.value < other.value
#    return NotImplemented
# ------------------------------------------------------------------------------
# Class ProcessCode -------------------------------------------------------------

class ProcessCode (IntEnum) :
  """
    This defines the values of the global intStatusArray, which keeps track
    of the individual processes.
  """
  OK        = 0  # -> process has been petted, meaning it is running normally
  SLEEP     = 1  # -> process needs to be petted, otherwise it will cause a timeout warning
  DEAD      = 2  # -> process has not been petted for 60 seconds. It is now considered dead
                   #The system will be put in the appropriate shutdown state
  HOLD      = 3  # -> the chillerRun process is waitining to be reactivated
  ERROR1    = 4  # -> process has other specific error
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
  def funcInitialize(self, strDevNameList, bolRunPseudo,fltCurrentTemps) : #TODO get rid of fltCurrentTemps here
    '''
    This is funcInitializeialized at the start of each running process. In each process the
    devices are stated in the funcInitializeialization and their configuration occurs. If 
    this is not done in the local process or done in a separate process the
    devices will not communicate!!!
    '''
    self._strclassname = '< RUNNING >' 
    
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

    # last temperature value for liquid from thermocouple, needed for humidity sensor 
    # if liquid temperature is lower than 0., humidity cannot be too high.
    self._fltTempLiquid = 0.

# ------------------------------------------------------------------------------
# Function: sendcommand --------------------------------------------------------
  def sendcommand(self, strUserCommand,intStatusCode,fltCurrentTemps) :
    """
      function to send command to any of the devices
    """
    try:
      logging.debug(' Start to send user command ' + strUserCommand )
      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( strUserCommand )
      logging.debug('sending command %s %s %s' % (strdevname, strcmdname, strcmdpara) )
      self._istDevHdl.readdevice( strdevname, strcmdname, strcmdpara,fltCurrentTemps)
    except:
      if intStatusCode.value == StatusCode.OK:  
        intStatusCode.value = StatusCode.ERROR

# -----------------------------------------------------------------------------
# Listener Process ------------------------------------------------------------
  def procListener (self, queue, intStatusArray,strLogName) :
    """
      Process that reads the queue and then puts whatever read to the log file
      with a name strLogName.
    """
    root = logging.getLogger()# Defines the logger
    #h = logging.handlers.RotatingFileHandler(strLogName,'a',1000,10) # Creates a rotating file handler to control how the queue works
    h = logging.FileHandler(strLogName,'a')
    f = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')# Creates format of all logged material
    h.setFormatter(f)# Sets format of the handler
    root.addHandler(h) #Adds the handler to the logger
    while True:
      self.funcResetDog(0,intStatusArray)
      try:
        # This sets conditions to quit the procListener process when the listener recieves None in the queue.
        record = queue.get()
        if record is None:
          break
        logger = logging.getLogger(record.name) #This finds the name of the log in the queue
        logger.handle(record) # Handles the log, printing it to the strLogName File
        print(record.asctime + " "+ record.levelname+" "+record.message) # Prints the log to the screen
      except Exception:
        import sys, traceback
        print('Whoops! Problem:', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# -----------------------------------------------------------------------------
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
# Function: Start Chiller Pump -------------------------------------------------
  def startChillerPump (self,queue,intStatusCode,intStatusArray,fltCurrentTemps) :
    """
      Procedure to start the Chiller and Pump:
      * Start Chiller 
      * Unlock Pump(Drive, Parameter)
      * Start Pump
      * Set Pump RPM to 22
    """
    logging.info(self._strclassname + " Starting Chiller and Pump") 
    
    # Start Pump and Chiller if necessary TODO Make it conditional if they are already on
    cmdList = ['cStart','iUnlockDrive','iUnlockParameter','iStart']
    for cmd in cmdList:
      self.sendcommand(self, cmd, intStatusCode,fltCurrentTemps)
      time.sleep(5) 
      self.funcResetDog(3,intStatusArray)

    strPumpRunRPM = '22'
    try:
      strPumpRunRPM = self._istRunCfg.get( 'Pump', 'RunRPM' )
    except:
      logging.warning("Sections: Pump, Key: RunRPM, not present in configure: %s" % \
                     self._istRunCfg.name() )

    #
    # Unlock before sending commands to inverter (Pump)
    # do it once at a beginning of a run
    #
 
    self.sendcommand(self, 'iRPM=' + strPumpRunRPM ,intStatusCode,fltCurrentTemps)
    logging.info(self._strclassname + " Pump change RPM to "+strPumpRunRPM)

# ------------------------------------------------------------------------------
# Function: Humidity Wait ------------------------------------------------------
  def humidityWait (self, intStatusCode, intStatusArray,fltCurrentTemps) :
    '''
      Changes the set temperature to 10 C in the event that the stave was set to a low
      temperature but it has too high humidity.
    '''
    intSetTemp = fltCurrentTemps[0]
    intWaitTemp = 10       
    self.sendcommand(self, 'cChangeSetpoint=' + str(intWaitTemp),intStatusCode ,fltCurrentTemps)
    fltCurrentTemps[0] = intWaitTemp
    logging.warning("< RUNNING > Due to high humidity, TSet changed to " + str(intWaitTemp)+' C')
    while intStatusCode.value == StatusCode.OK and intStatusArray[2] == ProcessCode.ERROR1:
      time.sleep(1)
      self.funcResetDog(3,intStatusArray)
    logging.warning("< RUNNING > Stave humidity is now low enough for cold settings. Reverting back to original set temp "+str(intSetTemp)+' C')
    self.sendcommand(self, 'cChangeSetpoint=' + str(intSetTemp),intStatusCode ,fltCurrentTemps)
    fltCurrentTemps[0] = intSetTemp
# ------------------------------------------------------------------------------
# Function: Chiller Wait -------------------------------------------------------
  def chillerWait (self, intTime, intStatusCode, intStatusArray,fltCurrentTemps,bolWaitInput=False,bolShutdown=False) :
    '''
      Checks the temperature at the stave core. If it has held its value for 
      more than 5 minutes it allows the system to continue.
    '''
    intWaitTime = intTime # temperature change wait time in minutes
    intEquiTime = 1       # temperature equillibrium wait time in minutes

    fltStaveTemp = (fltCurrentTemps[1]+fltCurrentTemps[2])/2  #Get the current average stave temp from inlet and outlet
    fltSetTemp   = fltCurrentTemps[0]                         #Get the set Temperature

    #Calculate what percent of the actual temp will be based upon the set temp
    #Effectively it is around 30% at -55 and around 1-2% at 20 and 50
    fltWaitPercent = (3.72622 -0.13636925*fltSetTemp+0.00207182*fltSetTemp*fltSetTemp)/fltSetTemp
    #Calculate Boundaries of the set temp
    fltSetTempUp = fltSetTemp + abs(fltWaitPercent*fltSetTemp)+2 
    fltSetTempDwn = fltSetTemp - abs(fltWaitPercent*fltSetTemp)-2 

    #When our temp has falled within the boundaries this loop ends
    while fltStaveTemp > fltSetTempUp or fltStaveTemp < fltSetTempDwn:
      logging.info( "< RUNNING > Chiller waiting for "+str(intWaitTime)+ " min to get to set Temp. Range("  \
                    +str(round(fltSetTempUp,2))+","+str(round(fltSetTempDwn,2))+") Current Temp. = "+str(round(fltStaveTemp,2)))
      for i in range( 60 * intWaitTime):
        if intStatusCode.value > StatusCode.ERROR or intStatusCode.value == StatusCode.ERROR and bolShutdown==False: return
        if intStatusArray[2] == ProcessCode.ERROR1:
          self.humidityWait(self,intStatusCode,intStatusArray,fltCurrentTemps)
        time.sleep(1)
        self.funcResetDog(3,intStatusArray)
      fltStaveTemp = (fltCurrentTemps[1]+fltCurrentTemps[2])/2
    logging.info("< RUNNING > Stave reached Temperature " + str(round(fltStaveTemp,2)) + " C, within Range("  \
                    +str(round(fltSetTempUp,2))+","+str(round(fltSetTempDwn,2))+") ")

    #Check to see if the temperature has stabilized before ending the wait
    fltStaveTempOld = fltStaveTemp+2
    while fltStaveTemp > fltStaveTempOld+1 or fltStaveTemp <fltStaveTempOld -1:
      fltStaveTempOld = fltStaveTemp 
      logging.info("< RUNNING > Chiller waiting "+str(intEquiTime)+" min to reach equillibrium")
      for i in range( 60 * intEquiTime):
        if intStatusCode.value > StatusCode.ERROR or intStatusCode.value == StatusCode.ERROR and bolShutdown==False : return
        time.sleep(1)
        self.funcResetDog(3,intStatusArray)
      fltStaveTemp = (fltCurrentTemps[1]+fltCurrentTemps[2])/2

    #Check to see if the code is to wait for a user's input
    if bolWaitInput == True and intStatusCode.value==StatusCode.OK:
      intStatusArray[3] = ProcessCode.HOLD # Makes the watchdog ignore this process as it waits for user input
      logging.info("----------     The system is holding the current set Temp "+str(fltSetTemp)+" C")
      print("**********     USER:To Release, type release and hit enter")
      while intStatusArray[3] == ProcessCode.HOLD and intStatusCode.value==StatusCode.OK:
        time.sleep(1)
      self.funcResetDog(3,intStatusArray)
      logging.info("----------     The system has been released.")

# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump ---------------------------------------------
  def shutdownChillerPump (self,queue,intStatusCode,intStatusArray,fltCurrentTemps) :
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
      1) Emergency (status = ERROR) causes normal shutdown
      2) Major Emergency (status = FATAL) does not allow for cooldown
      3) End of run (status = DONE) signals to all processes that the program is done
    """
    #
    strPumpStopRPM = '10' #RPM
    strChiStopTemp = '20' #Degree C
    try:
      strPumpStopRPM = self._istRunCfg.get( 'Pump', 'StopRPM' )
      strChiStopTemp = self._istRunCfg.get( 'Chiller', 'StopTemperature' )
    except:
      logging.warning("Sections: Pump, Chiller, Key: Stop RPM, StopTemperature not present in configure: "+self._istRunCfg.name()+" Using Default values(10RPM, 20C)") 

    #
    # Dictionary to keep the shutdown procedure
    # Key: Chiller and Pump commands 
    # Value: information for logging
    #
    

    strChiStopTemp = str(round(fltCurrentTemps[4]))  # Set to actual room Temperature...


    strCommandDict = { 'cChangeSetpoint=' + strChiStopTemp : self._strclassname + ' Changing Chiller set point to ' + strChiStopTemp + ' C. ',
                       'iRPM=' + strPumpStopRPM :            self._strclassname + ' Pump change RPM to '+strPumpStopRPM,
                       'iStop' :                             self._strclassname + ' Pump shutting down', 
                       'cStop' :                             self._strclassname + ' Chiller shutting down'}

    for strcommand, strlog in strCommandDict.items() :
      time.sleep(5) 
      # send the command to the corresponding device
      self.sendcommand(self, strcommand, intStatusCode,fltCurrentTemps)

      # write information into logging file
      logging.info( strlog ) 
      if 'cChangeSetpoint' in strcommand:
        fltCurrentTemps[0] = float(strChiStopTemp)

      # for non emergency shutdown, first cool down the chiller before shutting down the whole system 
      if intStatusCode.value < StatusCode.FATAL and 'cChangeSetpoint' in strcommand :
        intTimeCool = 600 # in seconds
        fltCurrentTemps[0] = float(strChiStopTemp) 
        try : 
          intTimeCool = 60 * int( self._istRunCfg.get( 'Chiller', 'StopCoolTime' ) ) # parameter in minutes
        except :
          pass
        bolWaitInput =False
        bolShutdown =True
        self.chillerWait(self,intTimeCool//60,intStatusCode,intStatusArray,fltCurrentTemps,bolWaitInput,bolShutdown)
        logging.info( self._strclassname + ' Chiller cooling down for {:3d}'.format( intTimeCool // 60 ) + ' minutes ' )  
        for i in range( intTimeCool ):
          # check second by second the status of the system
          if intStatusCode.value != StatusCode.ERROR: break 
          time.sleep( 1 ) # in seconds
          self.funcResetDog(3,intStatusArray)
    intStatusCode.value = StatusCode.DONE  
        
# ------------------------------------------------------------------------------
# Function: run one loop of Chiller Pump ---------------------------------------
  def runChillerPumpLoops(self,queue,intStatusCode,intStatusArray,fltProgress,fltCurrentTemps,bolWaitInput ,name = "Chiller") :
    """ 
      main routine of every loop running the Chiller and Boost Pump
      set the name parameter if not running the default "Chiller"
    """
    
    intChiNLoops  = 0
    try:
      intChiNLoops  = int( self._istRunCfg.get( name, 'NLoops' ) )
    except:
      logging.fatal("Sections: "+ name + ", Key: NLoops not present in configure: %s" % \
                     self._istRunCfg.name() )
      intStatusCode.value = StatusCode.FATAL
    logging.info("---------- Section: "+ name + ", number of loops " + str(intChiNLoops) )    


    # don't run any loop if it is set to 0 or negative
    if intChiNLoops <= 0: return

    try:
      # split values by ',' and then remove the white spaces.
      strTemperatureList = [ x.strip(' ') for x in self._istRunCfg.get( name, 'Temperagures' ).split(',') ]
      strTimePeriodList  = [ x.strip(' ') for x in self._istRunCfg.get( name, 'TimePeriod'   ).split(',') ]
    except:
      intStatusCode.value = StatusCode.FATAL
      logging.fatal("Section: "+ name + ", Key: Temperagures, TimePeriod not present in configure: %s" % \
                     self._istRunCfg.name() )
      return

    intNTemperature = len( strTemperatureList )
    fltProgressStep = float(100 / (intChiNLoops * intNTemperature))
    if intNTemperature != len(strTimePeriodList) :
      logging.warning( ' Length of temperature list ' + str(intNTemperature) + ' != ' + \
                       ' Length of time period list ' + str( len( strTimePeriodList ) ) + '. Set to Min.' )
      if len( strTimePeriodList ) < intNTemperature :
        intNTemperature = len( strTimePeriodList )
    
    for iloop in range(intChiNLoops) :
      logging.info('----------     Chiller, Pump running loop no. ' + str(iloop+1)+'/'+str(intChiNLoops) )
      for itemp in range(intNTemperature) :
        # changing the Chiller Temperature to a corresponding value 
        self.sendcommand(self, 'cChangeSetpoint=' + strTemperatureList[itemp],intStatusCode ,fltCurrentTemps)
        logging.info(self._strclassname +  ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        fltCurrentTemps[0] = float(strTemperatureList[itemp])
        self.chillerWait(self,1,intStatusCode,intStatusArray,fltCurrentTemps,bolWaitInput)
        logging.info(self._strclassname + ' Chiller at set temp. Waiting ' + strTimePeriodList[itemp] + ' minutes.')
        for i in range( 60 * int(strTimePeriodList[itemp])):
          if intStatusCode.value > StatusCode.OK: return
          time.sleep(1)
          self.funcResetDog(3,intStatusArray)

        fltProgress.value += fltProgressStep
    logging.info('----------     Chiller, Pump looping finished!' )
 
# ------------------------------------------------------------------------------
# Function: run Chiller Pump ---------------------------------------------------
  def runChillerPump(self,queue,intStatusCode,intStatusArray,fltProgress,fltCurrentTemps,intLoggingLevel,bolWaitInput,bolRunPseudo) :
    """
      main routine to run Chiller Pump with user set loops
     """

    # Configures the processes handler so that it will log
    self.funcLoggingConfig(queue,intLoggingLevel)
    # Configures the connected devices and their corresponding ports
    self.funcInitialize(self,["Chiller","Pump"], bolRunPseudo,fltCurrentTemps)
    time.sleep(10)

    self.startChillerPump (self,queue,intStatusCode,intStatusArray,fltCurrentTemps)

    for strsectionname in [ name for name in self._istRunCfg.sections() if "Chiller" in name ]:
      self.runChillerPumpLoops(self,queue, intStatusCode,intStatusArray,fltProgress,fltCurrentTemps,bolWaitInput, name = strsectionname) 
      # constantly check the status of the system 
      if intStatusCode.value > StatusCode.OK: 
        logging.warning("----------     Shutdown has been Triggered, Beginning Shutdown") 
        self.shutdownChillerPump(self,queue,intStatusCode,intStatusArray,fltCurrentTemps)
        return

    logging.info(self._strclassname + " Chiller Loops Have Finished, Beginning Shutdown") 
    self.shutdownChillerPump(self,queue,intStatusCode,intStatusArray,fltCurrentTemps)
    
# ------------------------------------------------------------------------------
# Function: record temperature -------------------------------------------------
  def recordTemperature(self,queue,intStatusCode,intStatusArray,fltCurrentTemps,intLoggingLevel,bolRunPseudo) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """

    self.funcLoggingConfig(queue,intLoggingLevel)

    self.funcInitialize(self,["Thermocouple"], bolRunPseudo,fltCurrentTemps)
    #time.sleep(20)

    # Default values
    fltTUpperLimit =  60 # upper limit in C for liquid temperature
    fltTLowerLimit = -55 # lower limit in C for liquid temperature
    intFrequency   =  29 # one data point per ? seconds
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
        logging.fatal( self._strclassname + ' IdxLiquidTemperature '+ intIdxTLiquid + ' not in [0, 3]. Check! ')
        intStatusCode.value = StatusCode.FATAL
        return
    except:
      logging.warning( ' Section: Thermocouple, Key: LiquidUpperThreshold, LiquidLowerThreshold, Frequency not found! Using defaults!')
         
    istThermocouple = self._istDevHdl.getdevice( 'Thermocouple' )
    if istThermocouple is None:
      logging.fatal( self._strclassname + ' Thermocouple not found in device list! ')
      intStatusCode.value = StatusCode.FATAL
      return

    # keep reading data until the process is killed or 
    # kill the process if the global status is more serious than an ERROR
    while ( intStatusCode.value < StatusCode.DONE) : 
      self.funcResetDog(1,intStatusArray)
      # read thermocouple data, every read takes ~25 seconds for 29 data points
      self.sendcommand(self,'tRead',intStatusCode,fltCurrentTemps)

      for idata in range( intDataPerRead ) :
          fltTempTup = list( istThermocouple.last( idata) ) 
          logging.info( '<DATA> Thermocouple T1: {:5.2f}, T2: {:5.2f}, T3: {:5.2f}, T4: {:5.2f} '.format( \
                        fltTempTup[0], fltTempTup[1], fltTempTup[2], fltTempTup[3]) ) 

          for i in range(4): #Adds the current temperatures into the global temps
            fltCurrentTemps[i+1]=fltTempTup[i]
          
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
    # after finishing running
    logging.info( self._strclassname + ' Temperature finished recording. ' )

# ------------------------------------------------------------------------------
# Function: record humidity ----------------------------------------------------
  def recordHumidity(self,queue,intStatusCode,intStatusArray,fltCurrentHumidity,fltCurrentTemps,intLoggingLevel,bolRunPseudo) :
    """
      recording the humidity inside the box
    """
    self.funcLoggingConfig(queue,intLoggingLevel) 
    self.funcInitialize(self,["Humidity"], bolRunPseudo,fltCurrentTemps)
    time.sleep(20)

    #Default values
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
      logging.warning("Section: Humidity, Key: StopUpperThreshold, WarnUpperThreshold, or Frequency, not found! Using defaults!")

    istHumidity = self._istDevHdl.getdevice( 'Humidity' )
    if istHumidity is None:
      logging.fatal( self._strclassname + ' Humidity not found in device list! ')
      intStatusCode.value = StatusCode.FATAL
      return
  
    while(intStatusCode.value < StatusCode.DONE ) :
      if intStatusArray[2] != ProcessCode.ERROR1:
        self.funcResetDog(2,intStatusArray)
      elif fltCurrentHumidity.value < fltStopUpperLimit:
        self.funcResetDog(2,intStatusArray)
 
      self.sendcommand(self, 'hRead',intStatusCode,fltCurrentTemps )
      fltHumidity = istHumidity.last() 
      logging.info( '<DATA> Humidity {:4.2f}'.format( fltHumidity ) )

      fltCurrentHumidity.value = fltHumidity #Sets global humidity

      if fltCurrentTemps[0] < 0.:
        if fltHumidity > fltStopUpperLimit : 
          logging.warning( self._strclassname + ' Chiller temp setting '+ str( fltCurrentTemps[0] ) +
                           ' box humidity ' + str( round(fltHumidity,1) ) + ' % > ' + str( fltStopUpperLimit ) + 
                           ' %! System will wait for humidity to decrease!')
          intStatusArray[2] = ProcessCode.ERROR1 
        elif fltHumidity > fltWarnUpperLimit : 
          logging.warning( self._strclassname + ' Chiller temp setting '+ str( fltCurrentTemps[0] ) +
                           ' box humidity ' + str( round(fltHumidity,1) ) + ' % > ' + str( fltWarnUpperLimit ) + ' %') 


      time.sleep( intFrequency - 1 )
    logging.info( self._strclassname + ' Humidity finished recording. ' )

# ------------------------------------------------------------------------------
# Function: Watchdog -----------------------------------------------------------
  def funcResetDog (intProcess,intStatusArray): #Puts the WatchDog into OK, which stops an error
    '''
    Each process has an assigned spot in the intStatusArray. Every 30 seconds 
    the array is checked by the watchdog. The watchdog then sets all processes 
    spots to ProcessCode.SLEEP. In each process loop there is funcResetDog that
    sets the spot to ProcessCode.OK. 
    '''
    if intStatusArray[intProcess] == ProcessCode.HOLD:
      while intStatusArray[intProcess] == ProcessCode.HOLD:
        time.sleep(1)
    intStatusArray[intProcess] = ProcessCode.OK

  def funcError1Dog (intProcess,intStatusArray): # Gives the Watchdog an error sign, not currently in use
    
    intStatusArray[intProcess] = ProcessCode.ERROR1

  def procWatchDog (self,queue, intStatusCode, intStatusArray,fltProgress,bolSendEmail,intLoggingLevel):
    '''
      The Watchdog is the system protection protocol. It has 2 purposes,
      1. to keep track of errors
      2. to notify the operators when end conditions are met
      Errors
        The system currently is written to deal mainly with timeout errors, though
        it will be easy to add in more complicated errors as well.

        TimeOut- The global intStatusArray is used for this. Every 30 seconds the
        watchdog looks at each process's value on the intStatusArray and then sets
        the value to 0. In each process's routine, there is a function called
        PetDog, which sets the value to 1. If the value is still at 0 after 30 seconds
        the watchdog sends out a warning. After sending out the warning, the watchdog
        changes the value of intCurrentState. Currently there are 3 values for each
        process in this array.
        intCurrentState = OK, normal state
                          SLEEP, Timed out once!...
                          DEAD, Timed out twice!... ->Send Email, and/or begin shutdown->Process is considered dead

        Others- Currently there are no specific error codes, though using higher values of intStatusArray
        or intCurrentState could be used to give that information with the WackDog function
      Emailing
        This uses the SendMail.py macro to send emails. Once an email has been
        sent it will change sentMessage to True and not send any more... because
        the system will be waiting for personal intervention.  
    '''
    strWatchDog = '< WATCHDOG >'
    self.funcLoggingConfig(queue,intLoggingLevel)
    
    #default mailList
    mailList = ['wheidorn@iastate.edu']# This is the list of email addresses the program will send emails too
    self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', [])
    try: 
      mailList = [ x.strip(' ') for x in self._istRunCfg.get( 'Email', 'Users' ).split(',') ]
    except:
      logging.warning('Unable to find email list in Config File, Using Default: wheidorn@iastate.edu')
    
    if bolSendEmail == True:
      logging.info(strWatchDog  +' Will notify: '+str(mailList))
    else:
      logging.info(strWatchDog +' Will notify: Local User')

    def mail(strTitle,strMessage):#This sends an email out if bolSendEmail == true
      if bolSendEmail == True:  
        print('Sending Message: '+strTitle+': '+strMessage)
        for p in mailList: 
          clsSendEmails.funcSendMail(clsSendEmails,p,strTitle,strMessage)
          logging.info(strWatchDog+' Email sent to '+ p) 
          time.sleep(1)

    strProcesses = ['Listener','Temperature Recorder','Humidity Recorder','RunChillerPump']
    intCurrentState = [ProcessCode.OK,ProcessCode.OK,ProcessCode.OK,ProcessCode.OK]
    sentMessage = False

    intFrostCounter = 0
    while intStatusCode.value < StatusCode.DONE:      
      logging.debug( strWatchDog + ' Checking all process statuses')
      i = 0
      for p in intStatusArray:

        #How to deal with high humidity during a run
        if p == ProcessCode.ERROR1 and i == 2:
          logging.warning(strWatchDog+' FROST DANGER! The system will begin shutdown in '+ str((20- intFrostCounter)/2)+ ' min if the humidity does not drop. ')
          intFrostCounter += 1
          intCurrentState[i] = ProcessCode.ERROR1
          if intFrostCounter >= 20:
            logging.error( strWatchDog+' PROCESS: '+strProcesses[i]+' Humidity did not drop soon enough. Begin Shutdown')
            intStatusCode.value = StatusCode.ERROR #Begin Normal shutdown
            intCurrentState[i] = ProcessCode.OK #Put the process back into the OK state... so it will continue taking data
          

        #How to deal with a second timeout 
        elif p == ProcessCode.SLEEP and intCurrentState[i] == ProcessCode.SLEEP:
          logging.error(strWatchDog+' PROCESS: '+ strProcesses[i]+' is still Timed Out!!!!')
          if i == 0 or i == 1 or i == 2:# If it is the logger, or one of the two recorders start shutdown
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessCode.DEAD
          else:# If it is the chiller loop alert the authorities, but do not shutdown
            logging.error(strWatchDog+' PROCESS: '+strProcesses[i]+' Killing System! ALERT THE AUTHORITIES!!!')  
            mail('Major Error!!!!!!!!','The watchdog lost track of the Chiller and Pump control!!!!')
            sentMessage = True
            intCurrentState[i] = ProcessCode.DEAD

        #How to deal with a single timeout
        elif p == ProcessCode.SLEEP and intCurrentState[i] == ProcessCode.OK: #Flags and Sends a timeout warning and sets the state to timed out
          logging.warning(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!!')
          intCurrentState[i] = ProcessCode.SLEEP
          if i == 0:# If the listener times out, we should just put it into shutdown, because we will no longer be logging
            print(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!! Triggering Shutdown')
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessCode.DEAD

        #Resetting all petted processes
        elif p == ProcessCode.OK:
          intCurrentState[i] = ProcessCode.OK

        elif p == ProcessCode.HOLD and intCurrentState[i]==ProcessCode.OK: #Flags and Sends a Chiller has been held message
          if i == 3:
            logging.warning(strWatchDog+' Noticed Chiller was held. Sending Reminders!')
            mail('REMINDER!','The Chiller has reached the set temperature!')
          intCurrentState[i]=ProcessCode.HOLD

        intStatusArray[i] = intCurrentState[i]
        #Resets all non error or higher process statuses to SLEEP
        if p == ProcessCode.OK:        
          intStatusArray[i] = ProcessCode.SLEEP
        i += 1 

      #Messaging due to shutdown conditions being met
      for sec in range(30):
        time.sleep(1)
        if intStatusCode.value == StatusCode.ERROR and sentMessage == False:
          mail('ERROR Shutdown Triggered!!','The system is shutting down normally.\
                The program was '+str(fltProgress.value)+' % complete.')
          sentMessage = True
        if intStatusCode.value == StatusCode.FATAL and sentMessage == False:
          mail('FATAL Shutdown Triggered!!','The system was shut down due to a fatal error.\
                It has not had time to properly cool! The program was '+str(fltProgress.value)+' % complete.')
          sentMessage = True
        if intStatusCode.value == StatusCode.DONE and sentMessage == False:
          mail('DONE Shutdown!!','The system has been shutdown. The program was completed with no fuss!')
          sentMessage = True
