"""
   Program ChillerRdCmd.py
	
	Description: ----------------------------------------------------------------
	   This file contains the class construct to build the command dictionary
	object for the slave device(s) connected to the controlling computer.  This
	file is one part of the controlling software for the automation control of
	the ATALS inner dectector stave Quality Control checks.  Specifically the
	thermo imaging checks of the stave.
		
	History: --------------------------------------------------------------------
	  v1.0 - First public release.
	  
	Environment: ----------------------------------------------------------------
	  This program is written in Python 3.6.2.  Python can be freely downloaded
	from http://www.python.org.  This program has been tested on PCs running 
	Windows 7.  
	
	Author List: ----------------------------------------------------------------
	   Jie Yu  Iowa State UNiversity, USA  jie.yu@cern.ch
		
	Notes: ----------------------------------------------------------------------
     Source of commands is text configuration file: ChillerEquipmentCommands.txt.

	Functions: ------------------------------------------------------------------
    * getdevicecommand( strdevcmd )
      - strdevcmd: human readable command, i.e. cStart
      - return: tuple of (device name, machine command, machine command's parameter)
    
    * devicenames()
      - return: list of the names of the devices
      -         i.e. [Chiller,Pump,Thermocouple,Humidity]
	   
    * devicekeys( strdevname )
      - strdevname: device name
      - return: list of keys (commands) for this device

    * cfgname()
      - return: the configuration file name
		
	Dictionary of abbreviations: ------------------------------------------------
	  cmd = command
		cfg = configure
		dev = device
		idx = index
	  str = string
		val = value
    ist = instance
"""

# Import section --------------------------------------------------------------
import configparser   # Configurable parser functions/classes.
import logging        # Flexible event logging funtions/classes.
import re             # Regular expression operations.


# Class section ---------------------------------------------------------------
class clsCommands:
  """
    Class to convert human readable commands to machine readable commands
  """

  def __init__(self, strcmdfilename,runPseudo):
    """
      function of initialization
      default: strcmdfilename = ChillerEquipmentCommands.txt
    """

    self._strname = strcmdfilename

    # define a class name for all instance
    self._strclassname = '< Command >'


    #
    # short name as part of the human readable command to represent a device
    # c = Chiller, i = inverter (Pump), h = Humidity, t = Thermocouple
    # 

    self.__shnamesection =  "ShortName"

    #
    # allow_no_value = True: key having no value allowed
    # RawConfigParser: upper case 'KEY' not turned to lower case: 'key'
    # if lower case keys preferred, use ConfigParser
    #

    self._istcmdcfg = configparser.RawConfigParser( allow_no_value=True )
    self._istcmdcfg.read( strcmdfilename )
    logging.info( self._strclassname + ' Loading command file: ' + strcmdfilename );

    #
    # load the configuration device by device
    # and key (command) by key
    #

    for strdevname in self._istcmdcfg.sections():
      logging.debug( self._strclassname + ' Device name: ' + strdevname)

      for strcmdkey in self._istcmdcfg[strdevname]:
        strvalcomment = self._istcmdcfg[strdevname][strcmdkey]

        #
        # fixing the inline comment problem
        # assuming the comments starting with '#'
        #
        strval = [x for x in strvalcomment.split('#')][0].strip()
        self._istcmdcfg.set(strdevname, strcmdkey, strval)
        logging.debug( self._strclassname + '  command, value: ' + strcmdkey + ' '+ strval)

    #
    # check if __shnamesection is defined in the command config file,
    # if not print the error !!
    #
    if self.__shnamesection not in self._istcmdcfg.sections() :
      logging.error( self._strclassname + ' Command configuration having no ' + self.__shnamesection + ' section! ')
      logging.error( self._strclassname + ' Needed to interpret the input commands, please check ' + self._strname )
      raise ValueError ( self._strclassname + ' ' + self.__shnamesection + ' section not found.' )


# ------------------------------------------------------------------------------
# function getdevicecommand( strdevcmd ):
#   provide shortened command name, e.g. cStop
#   return tuple of (device name, command name, command parameter)
#
  def getdevicecommand(self, strdevcmd):
    """
      function to get a value by providing the shorted command name: strdevcmd
      the first character of the input strdevcmd represents the device shortname
      the rest is the command defined in the command configuration file.
      e.g. cStop              -> Chiller Stop
      e.g. cChangeSetPoint=20 -> Change Chiller set point to 20 C
      return a tuple (device name, command name, command parameter)
    """
    strshname  = strdevcmd[0]    # the first character to indicate the device
    strcmdname = strdevcmd[1:]   # the rest of the string is the command 
    strcmdpar    = ''              # if found an equal sign, it means the command should follow a value

    #
    # if a command has '=' in it meaning it sets a value
    # take off '=' before sending it to the device, because the command itself doesn't contain '='
    #

    if "=" in strdevcmd:
      idx = strdevcmd.index("=")
      strcmdpar = strdevcmd[idx+1:]
      strcmdname = strdevcmd[1:idx]
    logging.debug( self._strclassname + ' Short name ' + strshname + ', command name ' + strcmdname + ', value ' + strcmdpar )

    #
    # device name obtained through Short Name
    #
    strdevname = self._istcmdcfg[ self.__shnamesection ][ strshname ]
    
    strcmdval = ''
    if strcmdname not in self._istcmdcfg[ strdevname ]:
      logging.error( self._strclassname + ' Command ' + strcmdname + ' not found in section ' + strdevname + ' config file: ' + self._strname )
      return None
    else :
      strcmdval = self._istcmdcfg[ strdevname ][ strcmdname ]

    return (strdevname, strcmdval, strcmdpar)

# ------------------------------------------------------------------------------
# function devicenames():
#   return the list of the devices names
#
  def devicenames(self):
    """
      function to get the list of the devices names
      which are the section names in the configuration file
    """
    return self._istcmdcfg.sections()

# ------------------------------------------------------------------------------
# function devicekeys(strdevname):
#   provide the section (device) name
#   return the list of keys for this section (device)
#
  def devicekeys(self, strdevname):
    """
      function to get the list of the commands for each device
      which are the keys of the device section
    """
    if strdevname not in self._istcmdcfg.sections():
      logging.error( self._strclassname + ' Device ' + strdevname + ' not found in config file: ' + self._strname )
      return None
    return list( self._istcmdcfg[ strdevname ].keys() )
 

# ------------------------------------------------------------------------------
# function cfgname():
#   return the configuration file name
#
  def cfgname(self) :
    """
      function to return configuration file name
    """
    return self._strname

