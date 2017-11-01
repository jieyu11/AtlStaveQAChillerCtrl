"""
	Program ChillerCtrl.py
	
Description: ------------------------------------------------------------------
	A Python script to control the coolant chiller equipment.  The chilling
equipment is composed of: FTS Systems RC211B0 recirculating cooler; a 
Lenze ESV751N02YXC NEMA 4x inverter drive; a 3/4 HP, 1800RPM, 60Hz, 3-phase,
PVN56T17V5338B B motor; and a Liquiflo H5FSPP4B002606US-8(-60) booster pump.

  The code also is used to control and log data from an Omega HH314A Humidity 
Temperature Meter and an Omega HH147U Data Logger Thermometer.

This file contains the main body of code.  

History: ----------------------------------------------------------------------
	V1.0 - Oct-2017  First public release.
	
Environment: ------------------------------------------------------------------
	This program is written in Python 3.6.  Python can be freely downloaded from 
http://www.python.org/.  This program has been tested on PCs running Windows 10.

Author List: -------------------------------------------------------------------
	R. McKay  Iowa State University, USA  mckay@iastate.edu
	J. Yu  Iowa State University,  USA  jieyu@iastate.edu
	W. Heidorn  Iowa State University,  USA  wheidorn@iastate.edu
	
Notes: -------------------------------------------------------------------------

Dictionary of abbreviations: ---------------------------------------------------

"""

# Import section ---------------------------------------------------------------

import logging                  # logging:             https://docs.python.org/3.6/howto/logging.html
import sys                      # system specific:     https://docs.python.org/3.6/library/sys.html
import time                     # Time access:         https://docs.python.org/3.6/library/time.html
from datetime import datetime   # Date and time types: https://docs.python.org/3.6/library/datetime.html
from multiprocessing import Process, Value, Array # https://docs.python.org/3.6/library/multiprocessing.html
import multiprocessing as mp
from functools import total_ordering

from ChillerRun import *        # This is our own code. States what each process does

# Global data section ----------------------------------------------------------

strPyVersion = "3.6"
strCodeVersion ="V1.0"
intLoggingLevel = logging.INFO
strStartTime = str(time.strftime( '%m/%d/%Y %I:%M:%S %p',time.localtime()))
strStartTimeVal = time.time()
# -----------------------------------------------------------------------------
# Logging ---------------------------------------------------------------------

# Generate name of log File
strLogName = str(time.strftime( '%Y-%m-%d_%I-%M%p_',time.localtime()))+'ChillerRun.log'
# Setup log file
logging.basicConfig(filename=strLogName,
                    level=intLoggingLevel, \
                    format='%(asctime)s %(levelname)s: %(message)s', \
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Prints first header to the log file
logging.info('Python version: ' + strPyVersion )
logging.info('Chiller Control Code version: ' + strCodeVersion)

# ------------------------------------------------------------------------------
# System Loading ---------------------------------------------------------------
def intro():
  '''
    This is a short intro that the system will show upon startup
  '''
  print('---------------------------------------------------------------------------\n\n')
  print('                           Chiller Controller                              \n')
  print('                             Version  :'+str(strCodeVersion))
  print('                             PyVersion: '+str(strPyVersion)+'\n\n')
  print('---------------------------------------------------------------------------\n') 
  print("**********     Creating Log " + strLogName)

# ------------------------------------------------------------------------------
# Function User Commands -------------------------------------------------------

def procUserCommands(intStatusCode,intStatusArray,fltProgress,fltCurrentHumidity,fltCurrentTemps,procList,bolRunPseudo):
  '''
    This is a list of user commands that will be active once the system has been
  started. It can change the shutdown state of the chiller, kill the processes,
  give process status, and give the progress of the chiller loop program.

    These user commands become active once all the working processes have been
  started by the main and it takes over the main process.
  ''' 

  print(" ")
  print("     __General_Commands_During_Operation__")
  print("     progress  = shows how far into the loop the system is")
  print("     status    = shows current status of all running processes")
  print("     kill      = stops all processes, does not shutdown pump or chiller")
  print("     eshutdown = stops the chiller and then pump without full cooldown")
  print("     shutdown  = sets the system into a shutdown mode") 
  print("     temps     = shows last temp, humidity, and set temp values")
  print("     help      = prints list of commands ")

  while intStatusCode.value < StatusCode.DONE: 
    val = input("Input::: \n")
    
    # This option sets the global status code to DONE, this means all the process
    #will believe the chiller/pump finished its loop and all the processes will quit,
    #including this one which will then put the system in a kill all processes loop.
    #ending the program.
    if val == 'kill':
      processVal = input("WARNING! This just kills the program!It will leave the Chiller/Pump in their current state! Proceed? (y/n) \n")
      if processVal == 'y':
        intStatusCode.value = StatusCode.DONE
    
    # This option sets the global status code to FATAL. This means the chiller and
    #pump will go through the shutdown commands and the system will shutdown without
    #any cooldown time for the pipes or chiller.
    elif val == 'eshutdown':
      intStatusCode.value = StatusCode.FATAL
    
    # This option sets the global status code to ERROR. This means the chiller/ pump
    #will go through a normal shutdown.
    elif val == 'shutdown':
      intStatusCode.value = StatusCode.ERROR
    
    # This option prints lots of stuff about the processes, whether or not they
    #are using pseudo data, and what the current global status is.
    elif val == 'status':
      print("     Global Status: "+str(intStatusCode.value)+"  Using PseudoData?: "+ str(bolRunPseudo))
      i=0
      for p in procList:
        if i == 4:
          print("     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive()))            
        else:  
          print("     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive())+" PStatus: "+str(intStatusArray[i]))          
        i+=1
    # This option prints the current progress of the loop. It also attempts to
    #calcuate the remaining time of the loop( It is not that great at the beginning.)
    elif val == 'progress':
      if intStatusCode.value == StatusCode.OK:
        print("     Loop Progress: "+str(fltProgress.value)+'%')
      if intStatusCode.value > StatusCode.OK:
        print("     Loop Progress: Finished")
      print("     System Started: "+str(strStartTime ))
      print("     Current Run Time: " + str(round((time.time()-strStartTimeVal)/60,2))+" mins")
      print("     Estimated loop time remaining... " + str(round((((time.time()-strStartTimeVal)/(0.0001+fltProgress.value))/0.60)-((time.time()-strStartTimeVal)/60))) + ' mins')

    # Prints current temperature setting, temperature readings, and humidity reading
    elif val == 'temps':
      i = 0
      strTempNames = ["TSet","T1  ","T2  ","T3  ","T4  "]
      for p in fltCurrentTemps:
        print("     "+ strTempNames[i] +": "+ str(round(p,1))+" C")
        i+=1
      print("     Humi: "+str(round(fltCurrentHumidity.value,2))+" %")

    # Prints the list of commands
    elif val == 'help':
      print("     __Full_list_of_Commands__") 
      print("     kill      = stops all processes, does not shutdown pump or chiller")
      print("     eshutdown = stops the chiller and then pump without full cooldown")
      print("     shutdown  = sets the system into a shutdown mode")
      print("     progress  = shows how far into the loop the system is")
      print("     status    = shows current status of all running processes")
      print("     temps     = shows last temp, humidity, and set temp values")
      print("     help      = shows all commands")


    # A Debugging command that kills a single specified process 
    elif val == 'pkill':
      Pnames=[]
      for p in procList:
        Pnames.append(p.name) 
      processVal = input('Of '+str(Pnames)+ ' Type the process you wish to kill?\n')
      i = 0
      for p in Pnames: 
        if processVal == p:
          procList[i].terminate()
        i=i+1
# ------------------------------------------------------------------------------
# ---------------------------- MAIN ROUTINE ------------------------------------
def main( ) :
  """
    Run main routine
  """
  intro()

  #First must run a short routine that allows the user to determine if it will run with PseudoData
  val = input("**********     USER:Do you wish to run with pseudo data? (y/n)\n")
  bolRunPseudo = False
  if val == 'y' or val == 'Y':
    bolRunPseudo = True
  if bolRunPseudo == False:
    input("**********     USER: Check the status of the pump, chiller and pipes. If all are set press enter")
  
  #Second ask the user if they want to send emails...
  val = input("**********     USER:Do you wish to send emails to notify when shutdown occurs? (y/n)\n")
  bolSendEmail = False
  if val == 'y' or val == 'Y':
    bolSendEmail = True

  # The global variables
  queue = mp.Queue(-1)                      # This must be set for the logger to work. VERY IMPORTANT
  intStatusCode = Value('i',StatusCode.OK)  # Beginning Status of the system
  intStatusArray = Array('i',[ProcessCode.OK,ProcessCode.OK,ProcessCode.OK,ProcessCode.OK])     # Beginning process statuses

  fltProgress = Value('d',0)                # Beginning progress value  
  fltCurrentHumidity = Value('d',100)       # Beginning humidity value
  fltCurrentTemps = Array('d',[20,20,20,20,20])  # Beginning Temperature values the fltCurrentTemps[0]   = SetTempValue,
                                                 #                                  fltCurrentTemps[1-4] = Temperature Recorder Temps

  mpList = [] # Empty process list to be filled by each process

  # The listener process that allows logging from all processes
  mpList.append( mp.Process(target = clsChillerRun.procListener,name = 'Listener', \
                            args =(clsChillerRun,queue,intStatusArray,strLogName)) )

  # The Temp Rec process reads temperature data from the Temp Recorder  
  mpList.append( mp.Process(target = clsChillerRun.recordTemperature,name = 'Temp Rec', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,fltCurrentTemps,intLoggingLevel,bolRunPseudo,)) )

  # The Humi Rec process reads humidity data from the Humidity Recorder
  mpList.append( mp.Process(target = clsChillerRun.recordHumidity,name = 'Humi Rec', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,fltCurrentHumidity,fltCurrentTemps,intLoggingLevel,bolRunPseudo)) )

  # The RunChill process controls the chiller and booster pump
  mpList.append( mp.Process(target = clsChillerRun.runChillerPump,name = 'RunChill', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,fltProgress,fltCurrentTemps,intLoggingLevel,bolRunPseudo,)) ) 

  # The WatchDog process makes certain all other processes are currently running,
  #and in the event of problems shuts down the chiller, it also is used for messaging
  mpList.append( mp.Process(target = clsChillerRun.procWatchDog, name = 'WatchDog', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,bolSendEmail,intLoggingLevel)) )

  
  print("**********     BEGINNING PROCESSES")
  print("---------------------------------------------------------------------------")
  for p in mpList: #A loop that begins all of the process with a wait time
    p.start()
    print("**********     Process: "+str(p.name)+" PID: "+str(p.pid)+" ALIVE?: "+ str(p.is_alive())+" PseudoData?: "+str(bolRunPseudo))    
    time.sleep(5) #Necessary to stop things from overlapping while each process starts
    print("---------------------------------------------------------------------------")
 
  # At this point everything should be started. So the UserCommands now take over the
  #main process until the system goes into a DONE state.
  procUserCommands(intStatusCode,intStatusArray,fltProgress,fltCurrentHumidity,fltCurrentTemps,mpList,bolRunPseudo)

  print("**********     CHILLER SHUTDOWN, Terminating ANY Remaining Processes")

  # stops the Listener; Temperature and Humidity recorders are killed if they did not shut down properly
  for p in mpList:
    p.terminate()

  print("**********     ALL PROCESSES ARE SHUTDOWN! HAVE A NICE DAY!")

if __name__ == '__main__' : 

  # The 'spawn' start method is required to make the code work on both mac and
  #windows. In mac the default method is 'fork' which is not possible on
  #a windows computer.

  mp.set_start_method('spawn') 

  main()

# Upon startup print on computer screen this code version.
#
# Create a log text file for historical recording of actions and time stamp with
# temperture data from all temperature sensors. (humidity?) The log file will 
# have a date and code version header.  Notify user of success or read issues.
# 
# Open and read the configuration file.  This file contains all the settings for
# the chiller unit, booster pump, and RS-232 & USB:RS-485 serial interfaces.
# Notify user & log succes or issues.
#
# If no issues reading configuration file, 1st set the USB-serial ports.  Send a 
# status command to the equipment.  If no issues, set all devices to defined 
# configuration. Notify user & log success or issues setting devices.
#
# Open and read the command file for the chiller and booster pump.  Load the
# commands into a dictionary construct.  Notify user & log success or issues. 
# If issues reading the command file exit program.
# Internal to this program are specific commands: Loop, EndLoop, wait, & exit. 
# 
# In a infinite loop with shutdown hook, prompt user for a command and execute
# command. Log commands given.  At set frequency log the time, temperature(s),
# and humidity.
#
# Upon exit command, check chiller has been set to room temperature.  If not,
# do so.  Inform user of action and log status.  If chiller at room temperature
# log end of run, close log file and exit.
#
