"""
	Program ChillerCtrl.py
	
Description: ------------------------------------------------------------------
	A Python script to control the coolant chiller equipment.  The chilling
equipment is composed of: FTS Systems RC211B0 recirculating cooler; a 
Lenze ESV751N02YXC NEMA 4x inverter drive; a 3/4 HP, 1800RPM, 60Hz, 3-phase,
PVN56T17V5338B B motor; and a Liquiflo H5FSPP4B002606US-8(-60) booster pump.

This file contains the main body of code.  

History: ----------------------------------------------------------------------
	V1.0 - Jul-2017  First public release.
	
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
# logging: https://docs.python.org/3.6/howto/logging.html
import logging
# config: https://docs.python.org/3.6/library/configparser.html
import configparser
import sys
import time
from datetime import datetime
from ChillerRdDevices import *
from ChillerRdConfig import *
from ChillerRdCmd import *

# Global data section ----------------------------------------------------------

strpyversion = "3.6"; # differ from system python version
strconfname = 'ChillerConfig.txt'
strcmdname = 'ChillerEquipmentCommands.txt'
 
# Module data section ----------------------------------------------------------

# Local data section -----------------------------------------------------------

# Main code section ------------------------------------------------------------

# ------------------------------------------------------------------------------
# ------------------------------- LOG ------------------------------------------
strtime = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
logging.basicConfig(filename='Log_'+strtime+'.txt', level=logging.DEBUG, \
                    format='%(asctime)s %(levelname)s: %(message)s', \
                    datefmt='%m/%d/%Y %I:%M:%S %p')

logging.info('Python version: ' + strpyversion )
logging.info('Starting the program.');

# ------------------------------------------------------------------------------
# ------------------------------- CONFIG ---------------------------------------

istConf = clsConfig( strconfname )

# ------------------------------------------------------------------------------
# ------------------------------- DEVICES --------------------------------------

istDevHdl = clsDevicesHandler( istConf )

# ------------------------------------------------------------------------------
# ------------------------------ COMMANDS --------------------------------------
istCommand = clsCommands( strcmdname )
#strdevname, strcmdname = istCommand.getdevicecommand( 'hRead' )

#commands = ['cStart', 'cStop' ]
#commands = ['cSetpoint?', 'cChangeSetpoint']
#commands = ['hRead']
#commands = ['tRead']
#commands = ['iUnlockDrive', 'iStart', 'iStop']
commands = ['iStart', 'iStop']


# ------------------------------------------------------------------------------
# ---------------------------- MAIN ROUTINE ------------------------------------

for devcmd in commands : 
  strdevname, strcmdname = istCommand.getdevicecommand( devcmd )
  logging.info(' - OK, now perform command ' + strcmdname + ' on ' + strdevname )
  istDevHdl.readdevice( strdevname, strcmdname )
  for iw in range(0,20,10):
    print ("waiting %d seconds " % iw )
    time.sleep(10) # sleep 20 seconds




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
