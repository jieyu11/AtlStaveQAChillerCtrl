"""
	Program ChillerCtrl.py
	
Description: ------------------------------------------------------------------
	A Python script to control the coolant chiller equipment.  The chilling
equipment is composed of: FTS Systems RC211B0 recirculating cooler; a 
Lenze ESV751N02YXC NEMA 4x inverter drive; a 3/4 HP, 1800RPM, 60Hz, 3-phase,
PVN56T17V5338B B motor; and a Liquiflo H5FSPP4B002606US-8(-60) booster pump.

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
from ChillerRun import *
from multiprocessing import Process, Value, Array # https://docs.python.org/3.6/library/multiprocessing.html
import multiprocessing as mp

from enum import IntEnum
from functools import total_ordering

# Global data section ----------------------------------------------------------

strpyversion = "3.6"
strcodeversion ="V1.0"
loggingLevel = logging.INFO
strStartTime = str(time.strftime( '%m/%d/%Y %I:%M:%S %p',time.localtime()))
strStartTimeVal = time.time()

# Module data section ----------------------------------------------------------

# Local data section -----------------------------------------------------------

# Main code section ------------------------------------------------------------

# ------------------------------- LOG ------------------------------------------

logName = str(time.strftime( '%Y-%m-%d_%I-%M%p_',time.localtime()))+'ChillerRun.log'

logging.basicConfig(filename=logName,
                    level=loggingLevel, \
                    format='%(asctime)s %(levelname)s: %(message)s', \
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logging.info('Python version: ' + strpyversion )

# ------------------------------------------------------------------------------
# System Loading ---------------------------------------------------------------
def intro():
  '''
    This is a short intro that the system will show upon startup
  '''
  print('---------------------------------------------------------------------------\n\n')
  print('                           Chiller Controller                              \n')
  print('                             Version  :'+str(strcodeversion))
  print('                             PyVersion: '+str(strpyversion)+'\n\n')
  print('---------------------------------------------------------------------------\n') 
  print("**********     Creating Log " + logName)

# ------------------------------------------------------------------------------
# Function User Commands -------------------------------------------------------

def procUserCommands(queue,intStatusCode,fltProgress,procList,runPseudo):
  '''
    This is a list of commands that will be active once the system has been started
  '''
  while intStatusCode.value < StatusCode.DONE:
    print(" ")
    print("__General_Commands_During_Operation__")
    print("progress  = shows how far into the loop the system is")
    print("status    = shows current status of all running processes")
    print("kill      = stops all processes, does not shutdown pump or chiller")
    print("eshutdown = stops the chiller and then pump without full cooldown")
    print("shutdown  = sets the system into a shutdown mode") 
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
      print("     System Started: "+str(strStartTime ))
      print("     Current Run Time: " + str(time.time()-strStartTimeVal))
      #print("     Estimated loop time remaining... " + str((((time.time()-strStartTimeVal)/(0.0001+fltProgress.value))/0.60)-(time.time()/60)) + ' min')
    if val == 'help':
      print("__Full_list_of_Commands__")
      print("pkill     = kills an individual process")
      print("kill      = stops all processes, does not shutdown pump or chiller")
      print("eshutdown = stops the chiller and then pump without full cooldown")
      print("shutdown  = sets the system into a shutdown mode")
      print("progress  = shows how far into the loop the system is")
      print("status    = shows current status of all running processes")
      print("help      = shows all other commands")
 
    if val == 'pkill':
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
  mpList.append( mp.Process(target = clsChillerRun.procListener,name = 'Listener', \
                            args =(clsChillerRun,queue,intStatusArray,logName)) )  
  mpList.append( mp.Process(target = clsChillerRun.recordTemperature,name = 'Temp Rec', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,loggingLevel,runPseudo,)) )
  mpList.append( mp.Process(target = clsChillerRun.recordHumidity,name = 'Humi Rec', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,loggingLevel,runPseudo)) )
  mpList.append( mp.Process(target = clsChillerRun.runChillerPump,name = 'RunChill', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,fltProgress,loggingLevel,runPseudo,)) ) 
  mpList.append( mp.Process(target = clsChillerRun.funcWatchDog, name = 'WatchDog', \
                            args =(clsChillerRun,queue,intStatusCode,intStatusArray,verbose,loggingLevel)) )
  
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

if __name__ == '__main__' : 
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
