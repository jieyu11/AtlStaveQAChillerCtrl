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
Version = 'B.0.1'
pyVersion = '3.6'

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


class StatusCode (IntEnum) :
  OK      = 0  # -> all devices are fine
  PANIC   = 1  # -> Puts the system into a normal shutdown
  FATAL   = 2  # -> Turns off the Chiller and Pump right away
  DONE    = 3  # -> Says that both the Chiller and Pump are both off, Kill all the processes
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
  print("Python Version: %s, Program Version: %s" % (pyVersion,Version))

# -----------------------------------------------------------------------------
# Log File --------------------------------------------------------------------

logName = str(time.strftime( '%Y-%m-%d_%I-%M%p_',time.localtime()))+'ChillerRun.log'

#print("**********     Creating Log " + logName)
loggingLevel = logging.INFO

# -----------------------------------------------------------------------------
# Function User Commands -------------------------------------------------

def procUserCommands(queue,intStatusCode,fltProgress,procList,runPseudo):
  while intStatusCode.value < StatusCode.DONE:
    print(" ")
    print("__Commands_During_Operation__")
    print("kill = stops all processes, does not shutdown pump or chiller")
    print("eshutdown = stops the chiller and then pump without full cooldown")
    print("shutdown = sets the system into a shutdown mode")
    print("status = shows current status of all running processes")
    print("progress = shows how far into the loop the system is")
    print(" ")

    val = input("Input::: \n")
    if val == 'kill':
      processVal = input("WARNING! This just kills the program!It will leave the Chiller/Pump in their current state! Proceed? (y/n) \n")
      if processVal == 'y':
        intStatusCode.value = StatusCode.DONE

    if val == 'eshutdown':
      intStatusCode.value = StatusCode.FATAL

    if val == 'shutdown':
      intStatusCode.value = StatusCode.PANIC
    
    if val == 'status':
      print("     Global Status: "+str(intStatusCode.value)+"  Using PseudoData?: "+ str(runPseudo))
      for p in procList:
        print("     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive()))          
      
    if val == 'progress':
      if intStatusCode.value == StatusCode.OK:
        print("     Loop Progress: "+str(fltProgress.value)+'%')
      if intStatusCode.value > StatusCode.OK:
        print("     Loop Progress: Finished")

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
    #time.sleep(2)

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
# ------------------------------------------------------------------------------
# Functions: PetDog,WackDog ----------------------------------------------------
    '''
    These functions are a part of the WatchDog system. Each process has an assigned
    spot in the array. Every 30 seconds the array is checked by the watchdog.
    The watchdog then sets all processes spots to 0. In each process loop there is
    funcPetDog that sets the spot to 1 which is the OK sign. There is also WackDog
    this will put the spot into a number that can be a given error.
    '''
  def funcPetDog (intProcess,intStatusArray):
    intStatusArray[intProcess] = 1
  def funcWackDog (intProcess,intStatusArray,intStatus):
    intStatusArray[intProcess] = intStatus
# -----------------------------------------------------------------------------
# Listener Process ------------------------------------------------------------
  def procListener (self, queue, intStatusArray) :
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
  def p_config(queue) :
    """
       function that must be present in any process that uses the logger
    """
    h = logging.handlers.QueueHandler(queue) #Connects the handler to the main queue
    root = logging.getLogger() #Creates a new logging process root
    root.addHandler(h) # Connects the logging process to the handler
    root.setLevel(loggingLevel) # This sets what level is logged in each process

# -----------------------------------------------------------------------------
  def funcMessenger(self,queue,intStatusCode,verbose):
    """
      This process watches the status code. If an error occurs, then if verbose
      is set to true it will send emails to the email list.
    """
    
    self.p_config(queue)

    mailList = ['wheidorn@iastate.edu','wheidorn@gmail.com']
    SE = clsSendEmails()

    if verbose == True:
      while intStatusCode.value < StatusCode.DONE:
        time.sleep(1)
        if intStatusCode.value >= StatusCode.PANIC:
          for p in mailList: 
            SE.funcSendMail(p,"Shutting Down Chiller","The chiller has been triggered to shutdown")
            logging.info('< RUNNING > Messenger has sent email to '+ p) 
          break
 
    logging.info('< RUNNING > Messenger has finished')

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
    logging.info(self._strclassname + " Starting Chiller") 
    
# Start Pump and Chiller if necessary TODO Make it conditional if they are already on
    self.sendcommand(self, 'cStart' ,intStatusCode)
    time.sleep(1)  

    logging.info(self._strclassname + " Unlocking BoosterPump Drive, Starting Booster Pump")
    self.sendcommand(self, 'iUnlockDrive',intStatusCode )
    time.sleep(5)
    self.sendcommand(self, 'iUnlockParameter' ,intStatusCode)
    time.sleep(5)
    self.sendcommand(self, 'iStart',intStatusCode )
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
      1) Emergency (status = PANIC) causes normal shutdown
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
          if intStatusCode.value > StatusCode.PANIC: break 
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
        for itime in range( int(strTimePeriodList[itemp]) ):
          logging.info(self._strclassname +  ' Chiller waiting at ' + str(itime) + 'th minute.' )

          #
          # sleep for one minute, check system status every second
          #
          for i in range( 60 ):
             # check second by second the status of the system
             if intStatusCode.value > StatusCode.OK: return 
             time.sleep( 1 ) # in seconds
             self.funcPetDog(3,intStatusArray)
        fltProgress.value += fltProgressStep
    logging.info('----------     Chiller, Pump looping finished!' )
 
# ------------------------------------------------------------------------------
# Function: run Chiller Pump ---------------------------------------------------
  def runChillerPump(self,queue,intStatusCode,intStatusArray,fltProgress,runPseudo) :
    """
      main routine to run Chiller Pump with user set loops
     """
   
    # Configures the processes handler so that it will log
    self.p_config(queue)
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
        break

    logging.info(self._strclassname + " Chiller Loops Have Finished, Beginning Shutdown") 
    self.shutdownChillerPump(self,queue,intStatusCode,intStatusArray)

# ------------------------------------------------------------------------------
# Function: record temperature -------------------------------------------------
  def recordTemperature(self,queue,intStatusCode,intStatusArray,runPseudo) :
    """
      recording temperatures of ambient, box, inlet, outlet from the thermocouples
    """

    self.p_config(queue)

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
            intStatusCode.value = StatusCode.PANIC

          if self._fltTempLiquid > fltTUpperLimit:
            logging.error( self._strclassname + ' liquid temperature '+ self._fltTempLiquid +
                           ' > upper limit ' + fltTUpperLimit + '! Return! ') 
            intStatusCode.value = StatusCode.PANIC
    # after finishing running
    logging.info( self._strclassname + ' Temperature finished recording. ' )

# ------------------------------------------------------------------------------
# Function: record humidity ----------------------------------------------------
  def recordHumidity(self,queue,intStatusCode,intStatusArray,runPseudo) :
    """
      recording the humidity inside the box
    """
    self.p_config(queue) 
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
          intStatusCode.value = StatusCode.PANIC 
          return
        elif fltHumidity > fltWarnUpperLimit : 
          logging.warning( self._strclassname + ' at liquid temperature '+ str( self._fltTempLiquid ) +
                           ' box humidity ' + str( fltHumidity ) + '% > ' + str( fltStopUpperLimit ) + '%')
          #intStatusCode.value = StatusCode.ERROR  

      time.sleep( intFrequency - 1 )
    logging.info( self._strclassname + ' Humidity finished recording. ' )

# ------------------------------------------------------------------------------
# Function: Watchdog -----------------------------------------------------------
  def funcWatchDog (self,queue, intStatusCode, intStatusArray):
    strWatchDog = '< WATCHDOG >'
    self.p_config(queue)

    while intStatusCode.value < StatusCode.DONE:      
      logging.debug( strWatchDog + ' Checking all process statuses')
      i = 0
      for p in intStatusArray:
        i += 1 
        if p == 0:
          logging.warning(strWatchDog+' PROCESS '+ str(i)+' Timed Out!!!!')

      logging.debug( strWatchDog + ' All Okay!')
      logging.debug( strWatchDog + ' Resetting all process statuses to zero')
      for i in range(len(intStatusArray)):
        intStatusArray[i] = 0
      time.sleep(30)

# -----------------------------------------------------------------------------
def runRoutine( ) :
  """
    Run main routine
  """

  #First must run a short routine that allows the user to determine if it will run with PseudoData

  val = input("**********     USER:Do you wish to run with pseudo data? (y/n)\n")
  runPseudo = False
  if val == 'y':
    runPseudo = True
  if runPseudo == False:
    input("**********     USER: Check the status of the pump, chiller and pipes. If all are set press enter")
  
  val = input("**********     USER:Do you wish to send emails to notify when shutdown occurs? (y/n)\n")
  verbose = False
  if val == 'y':
    verbose = True
  
  queue = mp.Queue(-1)
  intStatusCode = Value('i',0)
  fltProgress = Value('d',0)   
  intStatusArray = Array('i',[1,1,1,1]) 
    #
    # run preset Chiller and Pump routine using two separated processing
    # one for Chiller Pump running,
    # the other for Temperature and Humidity recording
    # 
   
  mpList = []
  mpList.append( mp.Process(target = clsChillerRun.procListener,name = 'Listener', args =(clsChillerRun,queue,intStatusArray)) ) 
  #mpList.append( mp.Process(target = clsChillerRun.funcMessenger, name = 'Messengr', args =(clsChillerRun,queue,intStatusCode,verbose)) )
  mpList.append( mp.Process(target = clsChillerRun.recordTemperature,name = 'Temp Rec', args =(clsChillerRun,queue,intStatusCode,intStatusArray,runPseudo,)) )
  mpList.append( mp.Process(target = clsChillerRun.recordHumidity,name = 'Humi Rec', args =(clsChillerRun,queue,intStatusCode,intStatusArray,runPseudo)) )
  mpList.append( mp.Process(target = clsChillerRun.runChillerPump,name = 'RunChill', args =(clsChillerRun,queue,intStatusCode,intStatusArray,fltProgress,runPseudo,)) ) 
  mpList.append( mp.Process(target = clsChillerRun.funcWatchDog, name = 'WatchDog', args =(clsChillerRun,queue,intStatusCode,intStatusArray)) )
  
  print("**********     BEGINNING PROCESSES")
  print("---------------------------------------------------------------------------")
  for p in mpList:
    p.start()
    print("**********     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive())+" PseudoData?: "+str(runPseudo))    
    time.sleep(5)
    print("---------------------------------------------------------------------------")
 
  procUserCommands(queue,intStatusCode,fltProgress,mpList,runPseudo)

  print("**********     CHILLER SHUTDOWN, Terminating ANY Remaining Processes")

    # stops the Listener; Temperature and Humidity recorders are killed if they did not shut down properly
  for p in mpList:
    p.terminate()

  print("**********     ALL PROCESSES ARE SHUTDOWN! HAVE A NICE DAY!")


def main():
  """
    test running the whole routine
  """
  intro()
  print("**********     Creating Log " + logName)

  logging.basicConfig(filename=logName, 
                      level=loggingLevel, \
                      format='%(asctime)s %(levelname)s: %(message)s', \
                      datefmt='%m/%d/%Y %I:%M:%S %p')
 
  runRoutine()

if __name__ == '__main__' : 
  mp.set_start_method('spawn')
  main()
