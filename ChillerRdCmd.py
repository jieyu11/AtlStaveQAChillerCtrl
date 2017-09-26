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
	   ?
		
	Dictionary of abbreviations: ------------------------------------------------
	   cmd = command
		config = configure
		dev = device
		idx = index
	   str = string
		val = value
	
	
"""

#  Import section --------------------------------------------------------------
import configparser   # Configurable parser functions/classes.
import logging        # Flexible event logging funtions/classes.
import re             # Regular expression operations.

# ########################### Global data section ##############################


# ########################### Function section #################################


# ########################### Class section ####################################
class clsCommands:
# ------------------------------------------------------------------------------
# function __init__ ( strcmdname ): 
#   Initialize the class clsCommands.
#   Source of commands is text configuration file: ChillerEquipmentCommands.txt.
#
  def __init__(self, strcmdname):
    """
      function of initialization
    """
    self.strname = strcmdname
    # section name for short named
    # check ChillerEquipmentCommands.txt for the name
    self.__shortname =  "ShortName"

    # allow_no_value=True: key having no value allowed
    # RawConfigParser: KEY not turned to lower case: key
    #                  if lower case keys preferred, use ConfigParser
    self.__cmdconf = configparser.RawConfigParser( allow_no_value=True )
    self.__cmdconf.read( strcmdname )
    logging.info( 'Loading command file: ' + strcmdname );

    # fixing the inline comment problem
    for strsection in self.__cmdconf.sections():
      logging.info('Configure: ' + strsection)
      for strkey in self.__cmdconf[strsection]:
        strvalcomment = self.__cmdconf[strsection][strkey]
        #
        # assuming inline comments starting with '#'
        #
        strval = [x for x in strvalcomment.split('#')][0].strip()
        self.__cmdconf.set(strsection, strkey, strval)
        logging.info(' - ' + strkey + ' '+ strval)

    # check if __shortname is defined in the command config file,
    # if not print the error !!
    if self.__shortname not in self.__cmdconf.sections() :
      logging.error(' Command configuration having no ' + self.__shortname + ' section!! ')
      logging.error(' Needed to interpret the input commands, please check ' + self.strname )

    logging.info( ' ---- ---- ---- ---- ');

# ------------------------------------------------------------------------------
# function getdevicecommand( strdevcmd ):
#   provide shortened command name, e.g. cStop
#   return tuple of (device name, command name)
#   e.g. return (Chiller, Stop)
#
  def getdevicecommand(self, strdevcmd):
    """
      function to get a value by providing the shorted command name: strdevcmd
      the first character of the input strdevcmd represents the device shortname
      the rest is the command defined in the command configuration file.
      e.g. cStop = Chiller Stop
      return a tuple (device name, command name)
    """
    __strshname  = strdevcmd[0]    # the first character to indicate the device
    __strcmdname = strdevcmd[1:]   # the rest of the string is the command 
    strcmdpar    = ''              # if found an equal sign, it means the command should follow a value
    if "=" in strdevcmd:
      idx = strdevcmd.index("=")
      strcmdpar = strdevcmd[idx+1:]
      __strcmdname = strdevcmd[1:idx]
      print ("index = at "+str(idx) )
    print( "!!! short name " + __strshname + " command name " + __strcmdname + " value " + strcmdpar )

    #TODO: some commands have value attached to it
    #TODO: need to split the command using re.split('(\d.*)', __strcmdname ) first
    strdevname = ''
    if __strshname not in self.__cmdconf[ self.__shortname ] :
      logging.error(' - ' + __strshname + ' not found in section '+ self.__shortname + ' config file: ' + self.strname )
      return ('','')
    else :
      strdevname = self.__cmdconf[ self.__shortname ][ __strshname ]
    
    strcmdval = ''
    if __strcmdname not in self.__cmdconf[ strdevname ]:
      logging.error(' - ' + __strcmdname + ' not found in section ' + strdevname + ' config file: ' + self.strname )
      return ('','')
    else :
      strcmdval = self.__cmdconf[ strdevname ][ __strcmdname ]

    return (strdevname, strcmdval, strcmdpar)

# ------------------------------------------------------------------------------
# function sections():
#   return the list of the section (devices) names
#
  def sections(self):
    """
      function to get the list of the sections in the config file
    """
    return self.__cmdconf.sections()

# ------------------------------------------------------------------------------
# function keys(strsection):
#   provide the section (device) name
#   return the list of keys for this section (device)
#
  def keys(self, strsection):
    """
      function to get the list of the sections in the config file
    """
    if strsection not in self.__cmdconf.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return []
    return list( self.__cmdconf[sections].keys() )
 
