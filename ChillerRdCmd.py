"""
reading configuration file
"""
# function __init__ ( strcmdname ): 
#   initialize the class clsCommands
#   using command configuration file
#
# function getdevicecommand( strdevcmd ):
#   provide shortened command name, e.g. cStop
#   return tuple of (device name, command name)
#   e.g. return (Chiller, Stop)
#
# function sections():
#   return the list of the section (devices) names
#
# function keys(strsection):
#   provide the section (device) name
#   return the list of keys for this section (device)
#

import configparser
import logging
class clsCommands:
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


  def getdevicecommand(self, strdevcmd):
    """
      function to get a value by providing the shorted command name: strdevcmd
      the first character of the input strdevcmd represents the device shortname
      the rest is the command defined in the command configuration file.
      e.g. cStop = Chiller Stop
      return a tuple (device name, command name)
    """
    __strshname  = strdevcmd[0]    # the first character
    __strcmdname = strdevcmd[1:]   # the rest of the string
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

    return (strdevname, strcmdval)

  def sections(self):
    """
      function to get the list of the sections in the config file
    """
    return self.__cmdconf.sections()

  def keys(self, strsection):
    """
      function to get the list of the sections in the config file
    """
    if strsection not in self.__cmdconf.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return []
    return list( self.__cmdconf[sections].keys() )
 
