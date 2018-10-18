'''
	Program ChillerCtrl.py
	
Description: ------------------------------------------------------------------
	This is the main (top) Python routine to control the thermo evaluation of 
ATLAS inner dector stave supports.  The test equipment/devices communicate via 
USB ports on the controlling computer running Windows 10.

	The devices/equipment used are:
	
	Flir A655sc IR camera;
	FTS Systems RC211B0 recirculating cooler;
	Lenze ESV751N02YXC NEMA 4x inverter drive; 
	Liquiflo H5FSPP4B002606US-8(-60) booster pump;
	3/4 HP, 1800RPM, 60Hz, 3-phase, PVN56T17V5338B B motor;
	Omega HH314A Humidity/Temperature Meter;
	Omega HH147U Data Logger Thermometer;
	Arduino UNO Rev 3 shield with a DFRobot relay shield;
	Proteus 08004BN1 flow meter;
	Swagelok SS-62TS4-41DC actuator valves.

History: ----------------------------------------------------------------------
  V1.0 - Oct-2017  First public release.
  V1.1 - Nov-2017  Added chiller Wait function to hold temperatures until user releases.
  V1.2 - Dec-2017  Made many of the user commands give better responses.
                   Added the debug help and the ability to hold any process so that 
                   the watchdog doesn't crash. Hopefully this allows the user to
                   freeze the program if batteries need to be replaced in either of
                   the connected probes. i.e. Omega meters. 
                   Fixed safety features for chiller failure.
  V1.3 - Apr-2018  Added ability to change chiller set temperature and booster pump
                   RPS (Rotation Per Second) during a programmed run. 
                   Combined all of the informational user commands into one -info. 
                   Made email messages more descriptive.
                   Fixed bug where errors in sending commands crashed everything.
  V1.4 - Jul-2018  Added code for the Arduino UNO to read the flow meter and control 
                   the three actuators at stave coolant I/O end.
  V2.0 - Aug-2018  Restructured code to 9 processes
				   Updated comments and modified screen messages to operater.
  V2.1 - Sep-2018  Replaced Omega HH147U with Omega HH109A.
Environment: ------------------------------------------------------------------
	This program is written in Python 3.6.  Python can be freely downloaded from 
http://www.python.org/.  This program has been tested on PCs running Windows 10.

Author List: -------------------------------------------------------------------
	R. McKay    Iowa State University, USA  mckay@iastate.edu
	J. Yu       Iowa State University, USA  jieyu@iastate.edu
	W. Heidorn  Iowa State University, USA  wheidorn@iastate.edu
	
Notes: -------------------------------------------------------------------------
   A normal shutdown is defined by the chiller returning the coolant to room 
   temperature before the chiller & booster pump are shutdown.  (They still have
   power.)  At that time all the spawned proceses are killed and the program ends.
   
   A critical shutdown is defined by the chiller & booster pump stopping with no
   action to return the coolant to room temperature.  All spawned process are
   killed.  This leaves the coolant (and stave) at the temperature when the
   emergency shutdown was issued.  An example of such a critical shutdown, is
   the case of the chiller issueing a low fluid error condition.  The program
   will issue a critical shutdown for such a case.

Dictionary of abbreviations: ---------------------------------------------------
	bol - boolean
	cmd - command
	flt - float
	gbl - global
	int - integer
	lst - list
	 mp - multiProcess
   proc - process
	str - string

'''

# Import section ---------------------------------------------------------------

import logging                 # logging:             https://docs.python.org/3.6/howto/logging.html
import sys                     # system specific:     https://docs.python.org/3.6/library/sys.html
import time                    # Time access:         https://docs.python.org/3.6/library/time.html
from datetime import datetime, timedelta  # Date and time types: https://docs.python.org/3.6/library/datetime.html
from multiprocessing import Process, Value, Array   # https://docs.python.org/3.6/library/multiprocessing.html
import multiprocessing as mp          # Multiprocessing threading interface.
from functools import total_ordering  # Allow to define rich comparison. i.e. __lt__().

# User defined classes
from ChillerRun import *     # This is our own code. States what each process does.

# Global data section ----------------------------------------------------------

gblstrPyVersion = "3.6"    # Version of Python enterpreter used.
gblstrCodeVersion = "2.1"  # Version of this Python program.

# Define the upper & lower coolant temperature limits we expect to ever encounter.
# The current coolant, 3m Novec HFE-7100, actual limits are: -135C to 61C.
gblfltTempUpperLimit = 50.0
gblfltTempLowerLimit = -60.0

# Define the upper & lower limits we expect to operate the booster pump.  
# Units are rotations per second - RPS or Hertz.
gblfltBoostPumpUpperLimit = 40.0
gblfltBoostPumpLowerLimit = 1.0
gblfltFlowUpperLimit = 1.5

# Convert True/False boolean values to Yes/No text.
gblstrNoYes = ['No','Yes']
  
intLoggingLevel = logging.INFO # Set level for logger to report: DEBUG,INFO,WARNING,ERROR,CRITICAL.

# The following two variables are used in ChillerCtrl.py and ChillerRun.py
# Time format: %m = month, %d = day, %Y = year, %I = 12-hour, %M = minute, %S = seconds, %p = AM|PM
gblstrStartTime = str(time.strftime('%m/%d/%Y %I:%M:%S %p',time.localtime()))
gblstrStartTimeVal = time.time()
# ------------------------------------------------------------------------------


# Splash banner ----------------------------------------------------------------
def banner(strLogFilename):
  '''
    This is a banner that is displayed on the computer screen upon startup.
  '''
  print('\n  ' + '-'*72)
  print('  |' + ' '*70 + '|')
  print('  |' + ' '*26 + 'Chiller Controller' + ' '*26 + '|')
  print('  |' + ' '*70 + '|')
  print('  |' + ' '*29 + 'Version: ' + str(gblstrCodeVersion) + ' '*29 + '|')
  print('  |' + ' '*25 + 'Python Version: ' + str(gblstrPyVersion) + ' '*26 + '|')      
  print('  |' + ' '*70 + '|')
  print('  ' + '-'*72 + '\n')
  print("       Creating Log file: " + strLogFilename)


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

# User Commands ----------------------------------------------------------------
def procUserCommands(intStatusCode, intProcessStates, intSettings, fltTemps, fltHumidity, fltRPS,fltProgress,procList, bolRunPseudo):
  '''
    This is a list of user commands that will be active once the system has been
    started. It can change the shutdown state of the chiller, kill the processes,
    give process status, and give the progress of the chiller loop program.

    These user commands become active once all the working processes have been
    started by the main and it takes over the main process.
 
    ************* Info about user commands *************

    help      - Prints to the screen the list of valid commands shown below.
    shutdown  - Sets the global status code to ERROR. This means the chiller & booster pump
                 will go through a normal shutdown. i.e. return coolant to room temperature.
    eshutdown - Sets the global status code to FATAL. This means the chiller and
                 pump will go through the shutdown commands and the system will shutdown 
                 without returning the coolant to room temperature.
    info      - Prints to the screen the current: code status, loop progress, temperatures.
    tav       - Toggle the 3 actuator valves located at the coolant I/O end of the stave.
                 Each time this command is issued, the 3 actuators flip to one of two states.
    tset      - Change the set temperature of coolant in chiller.
    pset      - Change the booster pump rotations/second.
    kill      - Sets the global status code to DONE, this means all the process
                 will believe the chiller/pump finished its loop and all the processes will quit,
                 including this one which will then put the system in a kill all processes loop,
                 ending the program.
    pkill     - Kill a single specific process.
    release   - Changes the process status and releases the held temperature.
    phold     - Set a process in a hold state.
    prelease  - Release a held process.
    fr        - Reads the current flow rate value from the Arduino interface.

  '''
  # List all the commands & brief description of their function.  This is the text
  # displayed on screen when user types help.
  cmdList = f''' Command list:
    info      = Shows: Current progress of the preprogrammed loop,
                       Current status of all running processes,
                       last temp, humidity, and set temp values.
    kill      = Stops all processes, does not shutdown pump or chiller.
    pkill     = Kills a process.
    eshutdown = Stops the chiller and then pump without temperature change.
    shutdown  = Sets the system into a shutdown mode.
    tset r    = Changes temperature of chiller to r; range({gblfltTempLowerLimit},{gblfltTempUpperLimit}).
    pset r    = Changes booster-pump RPS to r; range({gblfltBoostPumpLowerLimit},{gblfltBoostPumpUpperLimit}).
    release   = Releases a hold on the temperature.
    phold     = Puts a process into the hold state.
    prelease  = Releases a process from the hold state.
    tav       = Toggle Actuator Valves.
    fr        = Read current Flow Rate.
    help      = Prints this list of commands. \n'''
  lstPheld = []  # List of process(es) put on hold.  Used in phold & prelease commands.
  
  while intStatusCode.value < StatusCode.DONE: 
    strVal= input("\nInput> ")  # Prompt user for input.
    strVal= strVal.lower()      # Force input text to lower case.
    
    if 'help' in strVal:
        print(cmdList)
      
    elif 'shutdown' in strVal:                 # Find shutdown in input,
        intStatusCode.value = StatusCode.SHUTDOWN #  normal shutdown.
    elif 'abort' in strVal:
        intStatusCode.value = StatusCode.ABORT

    elif strVal== 'info':

      strGlbStatus=['OK      ','SHUTDOWN','ERROR   ','ABORT   ','FATAL   ','KILLED  ','DONE    ']
      strGlbSetting=['START','ROUTINE','HWAIT','WAIT','SHUTDOWN','DONE!']
      print(f"\n Current Setting: {strGlbSetting[intSettings[Setting.STATE]]} ")
      print(f"\n   Global Status: {strGlbStatus[intStatusCode.value]} " \
            f"  Using PseudoData?: {gblstrNoYes[bolRunPseudo]}")
      strStatusVals=['OK','Sleep','DEAD (:,()','Held','Waiting for Humidity to decrease']
      i = 0# Iterator for processes
      for p in procList:
        if p.name == 'WatchDog':  # No need to print watchdog status - must be active.
          print(f"   Process: {p.name}  PID: {str(p.pid).zfill(5)}  ALIVE: " \
                                                        + gblstrNoYes[(p.is_alive())])            
        else:  
          print(f"   Process: {p.name}  PID: {str(p.pid).zfill(5)}  ALIVE: " \
              + f"{gblstrNoYes[(p.is_alive())]}  PStatus: {strStatusVals[intProcessStates[i]]}")
          i+=1

      fltRunningTime = round((time.time()-gblstrStartTimeVal), 2)
      intDays, intHours, fltMins = lstDeltaTime(fltRunningTime)
      print("\n    Loop Progress: " + str(round(fltProgress.value,2)) + '%')
      print(" Program Started: " + str(gblstrStartTime))
      print(f" Current Run Time: {intDays} days, {intHours} hours, {round(fltMins,3)} minutes")
        
      if fltProgress.value >= 100:
        print(" Loop Progress: Finished")
      elif fltProgress.value > 0.0:
        fltEstimatedTime = round(fltRunningTime/fltProgress.value*100., 2)
        intDays, intHours, fltMins = lstDeltaTime(fltEstimatedTime)
        print(f" Estimated loop time remaining:{intDays} days,{intHours} hours, {round(fltMins,3)} minutes")
      print("\n Current Temps")
      i = 0
      strTempNames = ["TSet","TRes","Tin ","Tout","Tbox","Troo","Thum1","Thum2"]
      for p in fltTemps:
        print("     " + strTempNames[i] + ": " + str(round(p, 1)) + u"\u00B0C")
        i += 1
      print(" Humidity: " + str(round(fltHumidity.value, 2)) + " %")
      print(" Pump Set: " + str(fltRPS[0])+ " rps")
      print(" FlowRate: " + str(round(fltRPS[1],3))+ " l/min")

    elif 'tav' in strVal:                       # Found actuator valve toggle command.
      print(f"Actuator valves switched to other state.")
      intSettings[Setting.TOGGLE] = True

    elif 'set' in strVal:                       # Found set in input.
      newValue = strVal.strip("tpset ")  # Get new value & convert to real number.
      if 'ts' in strVal:                        # Set chiller temperature to new value.
        try:
          newValue = float(newValue)         # Convert to real number.
          if newValue > gblfltTempUpperLimit or newValue < gblfltTempLowerLimit:
            print(f"\aGiven value outside of bounds ({gblfltTempLowerLimit},{gblfltTempUpperLimit})")
          else:
            fltTemps[0] = newValue
            intSettings[Setting.TCHANGE] = True
            print(f" Chiller Setpoint temperature changed to {round(newValue,1)}" + u"\u00B0C")
        except:
          print(f"\aInvalid value. Value must be between " \
                          f"{gblfltTempLowerLimit} and {gblfltTempUpperLimit}")
      elif 'ps' in strVal:              # Set booster pump rotations per second to new value.
        strVal= strVal.lstrip('pset ')  # Strip off command and save value.
        try:
          newValue = float(strVal)
          if newValue < gblfltBoostPumpLowerLimit or newValue > gblfltBoostPumpUpperLimit:
            print(f"\aGiven value outside of bounds ({gblfltBoostPumpLowerLimit}, " \
                                                   f"{gblfltBoostPumpUpperLimit})")
          else:
            fltRPS[0] = newValue
            intSettings[Setting.PCHANGE] = True
            print(f" Booster Pump RPS Changed to {newValue}")
        except:
          print(f"\aInvalid value. Value must be between " \
                          f"{gblfltBoostPumpLowerLimit} and {gblfltBoostPumpUpperLimit}")
      elif 'fs' in strVal:             #Set booster pump into flow mode and set flow rate
        strVal =strVal.lstrip('fset ') #Strip off command and save value.
        try:
          newValue = float(strVal)
          if newValue > gblfltFlowUpperLimit or newValue < 0:
            print(f"\aInvalid value. Value must be between 0 and {gblfltFlowUpperLimit}")
            pass
          else:
            continue
            #fltRPS[2] = newValue
        except:
          print(f"\aInvalid value. Value must be between 0 and {gblfltFlowUpperLimit}")
      else:
        print("\aInvalid set command. Use: tset r or pset r, where r is real number.\n")
    
    elif 'kill' in strVal: # Find kill in input,
      if 'p' in strVal:    #  check for pkill.
        lstPnames=[]       #   true - perform killing a process.
        i = 1
        for p in procList:
          lstPnames.append(f"{i}:{p.name}") 
        strProcessVal = input(f" Type the process you wish to kill:\n {lstPnames}:")
        intProcessVal = int(strProcessVal) - 1  # List index is zero based.
        procList[intProcessVal].terminate()
      if 's' in strVal:
        return
      else:                #  Perform program kill operation.
        strProcessVal = input("\a\t ********** WARNING! **********\n" \
                              "This kills the program! It will leave the chiller " \
                              "& booster pump in their current state! Proceed? (y/n) ")
        strProcessVal = strProcessVal.lower()
        if 'y' in strProcessVal:
          intStatusCode.value = StatusCode.KILLED          

    elif strVal== 'release':
      intProcessStates[Process.ROUTINE]= ProcessState.OK
      
    elif strVal== 'phold':   # Put a process on hold.
      lstPnames = []         # List of processes except watchdog.
      i = 1
      for p in procList:
        if p.name != 'WatchDog':
          lstPnames.append(f"{i}:{p.name}")
          i += 1
      strProcessVal = input(f" Type the process number you wish to make the watchdog ignore:\n  {lstPnames}: ")
      intProcessVal = int(strProcessVal) - 1  # List index is zero based.
      intProcessStates[intProcessVal] = ProcessState.HOLD
      lstPheld.append(lstPnames[intProcessVal])
      
    elif strVal== 'prelease':   # Release a held process.
      strProcessVal = input(f" Type the process number you wish to reinstate the watchdog:\n  {lstPheld}: ")
      intProcessVal = int(strProcessVal) - 1  # List index is zero based.
      intProcessStates[intProcessVal] = ProcessState.OK
      
    elif strVal == 'fr':
      fltFlowRate = 3.21
      print(f"\n Flow rate = {fltFlowRate} l/m");
        
    elif strVal== '':
      i = 0  # Do nothing.  User just hit enter with no text.
    elif strVal== 'superkill':
      return
    else:
      print("\n\a*** Illegal input. Type help for list of valid commands. ***\n")
# ------ End of input query -----------------------------------------------------

# -------------------------Initial Setting Options ------------------------------
# ------------------------------------------------------------------------------
def runPseudo():
  '''
    Ask the user if they want to run a simulated (pseudo) mode for debugging or
    actual live real time mode.  If actual real time mode, inform user the state 
    the devices/equipment must be in to run properly.
  '''
  strVal= input(" USER: Do you wish to run with pseudo data? (y/n/q) ")
  if strVal.lower() == 'y':
    return True
  elif strVal.lower() == 'q':
    stopRun()
  else:
    input(" USER: Check the status of the... \n\n \
         Booster Pump   == Is it set to remote state?\n \
         Chiller        == Is it set to remote state and PUMP & REFR are enabled?\n \
         Valves         == Are all open?\n \
         Temp. Logger   == Power on and in PC mode?\n \
         Humidity probe == Power on & not in auto power off mode?\n \
         Arduino        == Power on & USB connected to computer?\n\n \
    When all are set, press enter")
    print('\n')
  return False

# ------------------------------------------------------------------------------
def routine():
  '''
    Ask the user if they want to run a routine.
  '''
  strVal= input(" USER: Do you wish to run a routine from ChillerRunConfig.txt? (y/n/q) ")
  if strVal.lower() == 'y':
    return True
  elif strVal.lower() == 'q':
    stopRun()
  else:
    return False


# ------------------------------------------------------------------------------
def waitInput():
  '''
    Ask the user if they want to the chiller to wait once it gets to a set temp.
  '''
  strVal= input(" USER: Do you want to have the chiller hold when it reaches set temperatures? (y/n/q) ")
  if strVal.lower() == 'y':
    return True
  elif strVal.lower() == 'q':
    stopRun()
  else:
    return False

# ------------------------------------------------------------------------------
def sendEmail():
  '''
    Ask the user if they want to send notification emails.
  '''
  strVal= input(" USER: Do you wish to send emails to notify when shutdown occurs? (y/n/q) ")
  if strVal.lower() == 'y':
    return True
  elif strVal.lower() == 'q':
    stopRun()
  else:
    return False

# ------------------------------------------------------------------------------
def stopRun(mpList=[]):
  '''
    The system has reach a DONE state via normal operations or fatal state or 
    user command to terminate. Splash info on the terminal confirming operations have stopped.
  '''
  print("\n\a*** CHILLER SHUTDOWN. Terminating ANY remaining processes ***")
  logging.info("*** CHILLER SHUTDOWN. Terminating ANY remaining processes ***")

  # Look to see if the list of process has been defined.  If list is populated, then
  # there are process active. Kill them.  Splash notice to user terminal and exit
  # this program.
  try:
    for p in mpList:
      p.terminate()
  except NameError:
      logging.info("User decided to quit before starting processes.")

  print("***    All processes have terminated. Have a nice day!    ***")
  sys.exit()  # Exits the program and returns terminal to normal user interface.


# ------------------------------------------------------------------------------
# ---------------------------- MAIN ROUTINE ------------------------------------
# ------------------------------------------------------------------------------
def main():
  '''
    Main routine for controlling the thermo evaluation of ATLAS staves.  All 
    devices controlling the coolant system and devices monitoring the temperature
    and humidity are separate process.  Here these processes are started and at the
    end of the evaluation OR if the user commands a shutdown, stopped.  It all starts
    with asking the user a few questions about the intended mode of operation.
  '''
  
  # Generate name of log File and define the log file format.  
  # %Y = year, %m = month, %d = day, %I = 12 hour clock, %M = minute, %S = seconds, %p = AM|PM.
  strLogFilename = str(time.strftime('%Y-%m-%d_%I-%M%p_',time.localtime())) + 'ChillerRun.log'
  logging.basicConfig(filename = strLogFilename, level = intLoggingLevel, \
                        format = '%(asctime)s %(levelname)s: %(message)s', \
                       datefmt = '%m/%d/%Y %I:%M:%S %p')
                       
  # Print code version info to the log file.
  logging.info('Python version: ' + gblstrPyVersion)
  logging.info('Chiller Control Code version: ' + gblstrCodeVersion + '\n')

  banner(strLogFilename)  # Splash banner page on screen.

  # Ask the user questions about conditions to run the system.  Should the user
  # change their mind of conditions, loop back and repeat the questions.  OR if
  # the user has second thoughts about running at all, exit this program.
  bolSysSet = False             # Assume the run conditions are not set.
  while bolSysSet == False:
    print("\n")                 # Just to separate questions from previous text.
    bolRunPseudo = runPseudo()  # Ask if desire to run simulation.
    bolRoutine   = routine()    # Ask if wanting to run a routine.
    if bolRoutine == True:
      bolWaitInput = waitInput()  # Ask whether to run autonomous routine.
    else:
      bolWaitInput = False
    bolSendEmail = sendEmail()  # Ask whether to send information emails to people.
    
    # Regurgitate back to user the options chosen.  Give user chance to modify.
    print("\n Current Settings:\n")
    print(f"   Using PseudoData: {gblstrNoYes[bolRunPseudo]}")
    print(f"      Using Routine: {gblstrNoYes[bolRoutine]}")
    print(f"      Holding Temps: {gblstrNoYes[bolWaitInput]}")
    print(f"      Sending Email: {gblstrNoYes[bolSendEmail]}\n")
    strVal= input(" USER: Keep settings and begin? OR quit now? (y/n/q) ")
    if strVal.lower() == 'y':    # User satisfied so, proceed.
      bolSysSet = True
    elif strVal.lower() == 'q':  # User chose to quit now.
      stopRun()      

  # Define the multiprocessing shared global data.  Value & Array memory require a typecode for the
  # data held in the shared data structure.  'i' = signed integer, 'd' = double precision float.
  queue = mp.Queue(-1)                      # This must be set for the logger to work. VERY IMPORTANT.
  intStatusCode = Value('i',StatusCode.OK)  # Start Status of the system.
  # Must set a starting status for each process created later.  Assume all is OK.
  intOK = ProcessState.OK   # Just to condense the shared intProcessStates list statement.
  #   Current process are: [listener, temp, humidity, chiller, bst pump, Arduino, routine]
  intProcessStates = Array('i',[ intOK,intOK,intOK,intOK,intOK,intOK,intOK])

  intSettings = Array('i',[SysSettings.BOOT,False,False,0])  #  intSettings[0] = Current system setting
                                                             #  intSettings[1] = Need to change TSet?
                                                             #  intSettings[2] = Need to change PSet?
                                                             #  intSettings[3] = Valve Setting?

  fltTemps = Array('d',[20,20,20,20,20,20,20,20]) # Set temperature values at room temperature: 
                                                  #   fltTemps[0]   = Chiller SetTempValue,
                                                  #   fltTemps[1]   = Chiller TempValue
                                                  #   fltTemps[2-5] = Temperature Recorder Temps,
                                                  #   fltTemps[6-7] = Humidity Logger Temps
  fltHumidity = Value('d',100)             # Start humidity value of 100%.
  fltRPS = Array('d',[10,10])                     #   fltRPS[0]   = Booster Pump Set Value rps
                                                  #   fltRPS[1]   = Arduino Flow Rate

  fltProgress = Value('d',0)                      # Start progress value. 0% at beginning.

  mpList = [] # Empty process list to be filled by each process.

  # The listener process that allows logging from all processes.
  mpList.append(mp.Process(target = clsChillerRun.procListener, name = 'Listener', \
                             args =(clsChillerRun, queue, intProcessStates, strLogFilename)))

  # The Temp Rec process reads temperature data from the Temp Recorder.
  mpList.append(mp.Process(target = clsChillerRun.recordTemperature, name = 'Temp Rec', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, fltTemps, \
                                    intLoggingLevel, bolRunPseudo)))

  # The Humi Rec process reads humidity data from the Humidity Recorder.
  mpList.append(mp.Process(target = clsChillerRun.recordHumidity, name = 'Humi Rec', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, fltTemps, fltHumidity, \
                                    intLoggingLevel, bolRunPseudo)))

  # The Arduino process reads the RPS data and changes valve settings.
  mpList.append(mp.Process(target = clsChillerRun.procArduino, name = 'Arduino ', \
                             args =(clsChillerRun,queue,intStatusCode,intProcessStates, intSettings, fltTemps, \
                                    fltRPS, intLoggingLevel, bolRunPseudo)))

  # The Chiller  process runs the chiller and reads chiller reservoir temp.
  mpList.append(mp.Process(target = clsChillerRun.chillerControl, name = 'Chiller ', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, fltTemps, \
                                    intLoggingLevel, bolRunPseudo)))

  # The Pump process runs the booster pump.
  mpList.append(mp.Process(target = clsChillerRun.pumpControl, name = 'BstrPump', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, \
                                    fltTemps, fltRPS, intLoggingLevel, bolRunPseudo)))

  # The Routine process controls the Booster Pump and Chiller
  mpList.append(mp.Process(target = clsChillerRun.procRoutine, name = 'Routine ', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, \
                                    fltTemps, fltHumidity, fltRPS, fltProgress, intLoggingLevel, \
                                    bolWaitInput, bolRoutine, bolRunPseudo, gblstrStartTimeVal)))
 
  #The Watchdog process checks that all of the other processes are running
  procShortList = mpList
  mpList.append(mp.Process(target = clsChillerRun.procWatchDog, name = 'WatchDog', \
                             args =(clsChillerRun, queue, intStatusCode, intProcessStates, intSettings, fltTemps,\
                    fltHumidity, fltRPS, fltProgress, bolSendEmail,\
                    intLoggingLevel,gblstrStartTime,gblstrStartTimeVal,procShortList)))

  # Depending if operating live or pseudo (simulation), print the correct notice.
  if bolRunPseudo:
    print("\n\n  ******************* STARTING Simulation PROCESSES *******************")
  else:
    print("\n\n  ******************* STARTING PROCESSES *******************")
  print("---------------------------------------------------------------------------")

  # Splash on the terminal each process info as they are started.    
  for p in mpList: # A loop that starts all of the process with a wait time
    p.start()
    print(f" Process: {p.name} PID: {p.pid} ALIVE?: {gblstrNoYes[p.is_alive()]}")
    #time.sleep(5) # Necessary to stop things from overlapping while each process starts

    time.sleep(0.5) #TODO Temporary
    print("\n---------------------------------------------------------------------------")
 
  intSettings[Setting.STATE] = SysSettings.START
  # Depending if operating live or pseudo (simulation), print the correct notice.
  if bolRunPseudo:
    print("\n\n  ******************* Begin Simulation operations *******************")
  else:
    print("\n\n  ******************* Begin operations *******************")

  # At this point all processes should be started. The routine procUserCommands now monitors 
  # the command window for user input.  The system will run until it goes into a DONE state
  # or is aborted by user.
  procUserCommands(intStatusCode, intProcessStates, intSettings, fltTemps, fltHumidity, fltRPS,fltProgress,mpList, bolRunPseudo)
                   

  # The system has reach a DONE state via normal operations or fatal state or 
  # user command to terminate. Splash info on the terminal confirming operations have stopped.
  stopRun(mpList)

# ------------------------------------------------------------------------------
# --------------------------- It all starts here -------------------------------
# ------------------------------------------------------------------------------
if __name__ == '__main__' : 

  # The 'spawn' start method is required to make the code work on both mac and
  # windows. In mac the default method is 'fork' which is not possible on
  # a windows computer.

  mp.set_start_method('spawn') 

  main()

