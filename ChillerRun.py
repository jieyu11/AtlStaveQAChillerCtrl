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

import logging
import logging.handlers
import configparser
import time
import sys
from ChillerRdDevices import *
from ChillerRdConfig  import *
from ChillerRdCmd     import *
from SendEmails       import *


# https://docs.python.org/3.6/library/multiprocessing.html
from multiprocessing import Process, Value, Array
import multiprocessing as mp

from enum import IntEnum
from functools import total_ordering
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
  def __lt__(self, other):
    if self.__class__ is other.__class__:
      return self.value < other.value
    return NotImplemented
# ------------------------------------------------------------------------------
# Class ProcessCode -------------------------------------------------------------

class ProcessCode (IntEnum) :
  """
    This defines the values of the global intStatusArray, which keeps track
    of the individual processes.
  """
  OK      = 0  # -> process has been petted, meaning it is running normally
  SLEEP   = 1  # -> process needs to be petted, otherwise it will cause a timeout warning
  DEAD    = 2  # -> process has not been petted for 60 seconds. It is now considered dead
                   #The system will be put in the appropriate shutdown state
  ERROR1  = 3  # -> process has other specific error
 
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
  def init(self, strdevnamelist, runPseudo) :
    '''
    This is initialized at the start of each running process. In each process the
    devices are stated in the initialization and their configuration occurs. If 
    this is not done in the local process or done in a separate process the
    devices will not communicate!!!
    '''
    self._strclassname = '< RUNNING >' 
    
    # configuration of how the devices are connected to the PC
    self._istConnCfg = clsConfig( 'ChillerConnectConfig.txt', strdevnamelist)


    # pass the configuration of how the devices connection
    # to the device handler 
    self._istDevHdl = clsDevicesHandler( self._istConnCfg, strdevnamelist,runPseudo )

    # interpretation of machine readable commands into human readable commands
    # and vice versa
    self._istCommand = clsCommands( 'ChillerEquipmentCommands.txt', strdevnamelist)

    # configuration of the running routine 
    self._istRunCfg = clsConfig( 'ChillerRunConfig.txt', strdevnamelist )

    # last temperature value for liquid from thermocouple, needed for humidity sensor 
    # if liquid temperature is lower than 0., humidity cannot be too high.
    self._fltTempLiquid = 0.

# ------------------------------------------------------------------------------
# Function: sendcommand --------------------------------------------------------
  def sendcommand(self, strusercommand,intStatusCode) :
    """
      function to send command to any of the devices
    """
    try:
      logging.debug(' Start to send user command ' + strusercommand )
      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( strusercommand )
      logging.debug('sending command %s %s %s' % (strdevname, strcmdname, strcmdpara) )
      self._istDevHdl.readdevice( strdevname, strcmdname, strcmdpara)
    except:
      #if intStatusCode.value < StatusCode.ERROR:  
      #  intStatusCode.value = StatusCode.ERROR
      raise ValueError('Could not find user command: %s in %s' % (strusercommand, self._istCommand.cfgname() ))
# -----------------------------------------------------------------------------
# Listener Process ------------------------------------------------------------
  def procListener (self, queue, intStatusArray,logName) :
    """
      Process that reads the queue and then puts thing to a file
    """
    root = logging.getLogger()# Defines the logger
    h = logging.handlers.RotatingFileHandler(logName,'a',1000000,10) # Creates a rotating file handler to control how the queue works
    f = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')# Creates format of all logged material
    h.setFormatter(f)# Sets format of the handler
    root.addHandler(h) #Adds the handler to the logger
    while True:
      self.funcPetDog(0,intStatusArray)
      try:
        # This sets conditions to quit the procListener process when the listener recieves None in the queue.
        record = queue.get()
        if record is None:
          break
        logger = logging.getLogger(record.name) #This finds the name of the log in the queue
        logger.handle(record) # Handles the log, printing it to the logName File
        print(record.asctime + " "+ record.levelname+" "+record.message) # Prints the log to the screen
      except Exception:
        import sys, traceback
        print('Whoops! Problem:', file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# -----------------------------------------------------------------------------
# Function: process_configure -------------------------------------------------
  def p_config(queue,loggingLevel) :
    """
       function that must be present in any process that uses the logger
    """
    h = logging.handlers.QueueHandler(queue) #Connects the handler to the main queue
    root = logging.getLogger() #Creates a new logging process root
    root.addHandler(h) # Connects the logging process to the handler
    root.setLevel(loggingLevel) # This sets what level is logged in each process

# ------------------------------------------------------------------------------
# Function: Start Chiller Pump -------------------------------------------------
  def startChillerPump (self,queue,intStatusCode) :
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
      self.sendcommand(self, cmd, intStatusCode)
      time.sleep(5)
   
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
 
    self.sendcommand(self, 'iRPM=' + strPumpRunRPM ,intStatusCode)
    logging.info(self._strclassname + " Pump change RPM to "+strPumpRunRPM)

# ------------------------------------------------------------------------------
# Function: Shut down Chiller Pump ---------------------------------------------
  def shutdownChillerPump (self,queue,intStatusCode,intStatusArray) :
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
     
    strPumpStopRPM = '10'
    strChiStopTemp = '20'
    try:
      strPumpStopRPM = self._istRunCfg.get( 'Pump', 'StopRPM' )
      strChiStopTemp = self._istRunCfg.get( 'Chiller', 'StopTemperature' )
    except:
      #if intStatusCode.value < StatusCode.WARNING: 
      #  intStatusCode.value = StatusCode.WARNING
      raise KeyError("Sections: Pump, Chiller, Key: StopRPM, StopTemperature not present in configure: %s" % \
                     self._istRunCfg.name() )

    #
    # Dictionary to keep the shutdown procedure
    # Key: Chiller and Pump commands 
    # Value: information for logging
    #
    strCommandDict = { 'cChangeSetpoint=' + strChiStopTemp : self._strclassname + ' Chiller change set point to ' + strChiStopTemp,
                       'iRPM=' + strPumpStopRPM :            self._strclassname + ' Pump change RPM to '+strPumpStopRPM,
                       'iStop' :                             self._strclassname + ' Pump shutting down', 
                       'cStop' :                             self._strclassname + ' Chiller shutting down'}

    for strcommand, strlog in strCommandDict.items() :
      time.sleep(5) 
      # send the command to the corresponding device
      self.sendcommand(self, strcommand, intStatusCode )

      # write information into logging file
      logging.info( strlog ) 

      # for non emergency shutdown, first cool down the chiller before shutting down the whole system 
      if intStatusCode.value < StatusCode.FATAL and 'cChangeSetpoint' in strcommand :
        intTimeCool = 600 # in seconds 
        try : 
          intTimeCool = 60 * int( self._istRunCfg.get( 'Chiller', 'StopCoolTime' ) ) # parameter in minutes
        except :
          pass
        logging.info( self._strclassname + ' Chiller cooling down for {:3d}'.format( intTimeCool // 60 ) + ' minutes ' ) 
        #!!!!!time.sleep( intTimeCool )
        for i in range( intTimeCool ):
          # check second by second the status of the system
          if intStatusCode.value > StatusCode.ERROR: break 
          time.sleep( 1 ) # in seconds
          self.funcPetDog(3,intStatusArray)
    intStatusCode.value = StatusCode.DONE  
        
# ------------------------------------------------------------------------------
# Function: run one loop of Chiller Pump ---------------------------------------
  def runChillerPumpOneLoop(self,queue,intStatusCode,intStatusArray,fltProgress, name = "Chiller") :
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
    logging.info("---------- Section: "+ name + ", number of loops " + str(intChiNLoops) )    

    fltProgressStep = float(100 / (intChiNLoops * 4))


    # don't run any loop if it is set to 0 or negative
    if intChiNLoops <= 0: return

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
      logging.info('----------     Chiller, Pump running loop no. ' + str(iloop+1)+'/'+str(intChiNLoops) )
      for itemp in range(intNTemperature) :
        # changing the Chiller Temperature to a corresponding value 
        self.sendcommand(self, 'cChangeSetpoint=' + strTemperatureList[itemp],intStatusCode )
        logging.info(self._strclassname +  ' Changing Chiller set point to ' + strTemperatureList[itemp] + ' C. ' )
        logging.info(self._strclassname + ' Chiller waiting ' + strTimePeriodList[itemp] + ' minutes.')
        for i in range( 60 * int(strTimePeriodList[itemp])):
          if intStatusCode.value > StatusCode.OK: return
          time.sleep(1)
          self.funcPetDog(3,intStatusArray)

        fltProgress.value += fltProgressStep
    logging.info('----------     Chiller, Pump looping finished!' )
 
# ------------------------------------------------------------------------------
# Function: run Chiller Pump ---------------------------------------------------
  def runChillerPump(self,queue,intStatusCode,intStatusArray,fltProgress,loggingLevel,runPseudo) :
    """
      main routine to run Chiller Pump with user set loops
     """
   
    # Configures the processes handler so that it will log
    self.p_config(queue,loggingLevel)
    # Configures the connected devices and their corresponding ports
    self.init(self,["Chiller","Pump"], runPseudo)

    self.funcPetDog(3,intStatusArray) 
    self.startChillerPump (self,queue,intStatusCode)
    self.funcPetDog(3,intStatusArray) 
    for strsectionname in [ name for name in self._istRunCfg.sections() if "Chiller" in name ]:
      self.runChillerPumpOneLoop(self,queue, intStatusCode,intStatusArray,fltProgress, name = strsectionname)
      self.funcPetDog(3,intStatusArray)
      # constantly check the status of the system 
      if intStatusCode.value > StatusCode.OK: 
        logging.warning("----------     Shutdown has been Triggered, Beginning Shutdown") 
        self.shutdownChillerPump(self,queue,intStatusCode,intStatusArray)
        return

    logging.info(self._strclassname + " Chiller Loops Have Finished, Beginning Shutdown") 
    self.shutdownChillerPump(self,queue,intStatusCode,intStatusArray)
    
# ------------------------------------------------------------------------------
# Function: record temperature -------------------------------------------------
  def recordTemperature(self,queue,intStatusCode,intStatusArray,loggingLevel,runPseudo) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """

    self.p_config(queue,loggingLevel)

    self.init(self,["Thermocouple"], runPseudo)

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

    # keep reading data until the process is killed or 
    # kill the process if the global status is more serious than an ERROR
    while ( intStatusCode.value < StatusCode.DONE) : 
      self.funcPetDog(1,intStatusArray)
      # read thermocouple data, every read takes ~25 seconds for 29 data points
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
            intStatusCode.value = StatusCode.ERROR

          if self._fltTempLiquid > fltTUpperLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' > upper limit ' + fltTUpperLimit + '! Return! ') 
            intStatusCode.value = StatusCode.ERROR
    # after finishing running
    logging.info( self._strclassname + ' Temperature finished recording. ' )

# ------------------------------------------------------------------------------
# Function: record humidity ----------------------------------------------------
  def recordHumidity(self,queue,intStatusCode,intStatusArray,loggingLevel,runPseudo) :
    """
      recording the humidity inside the box
    """
    self.p_config(queue,loggingLevel) 
    self.init(self,["Humidity"], runPseudo)
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
  
    while(intStatusCode.value < StatusCode.DONE ) :
      self.funcPetDog(2,intStatusArray)
      self.sendcommand(self, 'hRead',intStatusCode )
      fltHumidity = istHumidity.last() 
      logging.info( '<DATA> Humidity {:4.1f}'.format( fltHumidity ) )
      if self._fltTempLiquid < 0.:
        if fltHumidity > fltStopUpperLimit : 
          logging.error( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                         ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + 
                         '% upper limit! Return! ')
          intStatusCode.value = StatusCode.ERROR 
          return
        elif fltHumidity > fltWarnUpperLimit : 
          logging.warning( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                           ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + '%')
          #intStatusCode.value = StatusCode.ERROR  

      time.sleep( intFrequency - 1 )
    logging.info( self._strclassname + ' Humidity finished recording. ' )

# ------------------------------------------------------------------------------
# Function: Watchdog -----------------------------------------------------------
    '''
    These functions are a part of the WatchDog system. Each process has an assigned
    spot in the array. Every 30 seconds the array is checked by the watchdog.
    The watchdog then sets all processes spots to 0. In each process loop there is
    funcPetDog that sets the spot to 1 which is the OK sign. There is also WackDog
    this will put the spot into a number that can be a given error.
    '''
  def funcPetDog (intProcess,intStatusArray): #Puts the WatchDog into OK, which stops an error
    intStatusArray[intProcess] = 1
  def funcPokeDog (intProcess,intStatusArray,intStatus): # Gives the Watchdog an error sign, not currently in use
    intStatusArray[intProcess] = intStatus

  def funcWatchDog (self,queue, intStatusCode, intStatusArray,bolSendEmail,loggingLevel):
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
    self.p_config(queue,loggingLevel)

    mailList = ['wheidorn@iastate.edu','wheidorn@gmail.com']# This is the list of email addresses the program will send emails too
    SE = clsSendEmails()
    def mail(strTitle,strMessage):#This sends an email out if bolSendEmail == true
      if bolSendEmail == True:  
        print('Sending Message: '+strTitle+': '+strMessage)
        for p in mailList: 
          SE.funcSendMail(p,strTitle,strMessage)
          logging.info(strWatchDog+' Email sent to '+ p) 
          time.sleep(1)

    strProcesses = ['Listener','Temperature Recorder','Humidity Recorder','RunChillerPump']
    intCurrentState = [ProcessCode.OK,ProcessCode.OK,ProcessCode.OK,ProcessCode.OK]
    sentMessage = False

    while intStatusCode.value < StatusCode.DONE:      
      logging.debug( strWatchDog + ' Checking all process statuses')
      i = 0
      for p in intStatusArray:

        #How to deal with a second Timeout          
        if p == ProcessCode.SLEEP and intCurrentState[i] == ProcessCode.SLEEP:
          logging.warning(strWatchDog+' PROCESS: '+ strProcesses[i]+' is still Timed Out!!!!')
          if i == 0 or i == 1 or i == 2:# If it is the logger, or one of the two recorders start shutdown
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessCode.DEAD
          else:# If it is the chiller loop alert the authorities, but do not shutdown
            logging.warning(strWatchDog+' PROCESS: '+strProcesses[i]+' Killing System! ALERT THE AUTHORITIES!!!')  
            mail('Major Error!!!!!!!!','The watchdog lost track of the Chiller and Pump control!!!!')
            sentMessage = True
            intCurrentState[i] = ProcessCode.DEAD

        #How to deal with a single timeout
        if p == ProcessCode.SLEEP and intCurrentState[i] == ProcessCode.OK: #Flags and Sends a timeout warning and sets the state to timed out
          logging.warning(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!!')
          intCurrentState[i] = ProcessCode.SLEEP
          if i == 0:# If the listener times out, we should just put it into shutdown, because we will no longer be logging
            print(strWatchDog+' PROCESS: '+ strProcesses[i]+' Timed Out!!!! Triggering Shutdown')
            intStatusCode.value = StatusCode.ERROR
            intCurrentState[i] = ProcessCode.DEAD

        #Resetting all petted processes
        if p == ProcessCode.OK:
          intCurrentState[i] = ProcessCode.OK

        #Resets all process statuses to SLEEP
        intStatusArray[i] = ProcessCode.SLEEP
        i += 1 

      #Messaging due to shutdown conditions being met
      for sec in range(30):
        time.sleep(1)
        if intStatusCode.value == StatusCode.ERROR and sentMessage == False:
          mail('ERROR Shutdown Triggered!!','The system is shutting down normally')
          sentMessage = True
        if intStatusCode.value == StatusCode.FATAL and sentMessage == False:
          mail('FATAL Shutdown Triggered!!','The system was shut down without time to properly cool!')
          sentMessage = True
        if intStatusCode.value == StatusCode.DONE and sentMessage == False:
          mail('DONE Shutdown!!','The system has been shutdown normally and all processes have been killed!')
          sentMessage = True
