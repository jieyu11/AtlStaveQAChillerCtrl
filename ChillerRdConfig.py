"""
reading configuration file
"""
# function __init__ ( strconfname ): 
#   initialize the class clsConfig
#   using config file name
# function get( strsection, strkey )
#   read the value by providing the section name and key name
#

import configparser
import logging
class clsConfig:
  def __init__(self, strconfname):
    """
      function of initialization
    """
    self.strname = strconfname
    # allow_no_value=True: key having no value allowed
    # RawConfigParser: KEY not turned to lower case: key
    #                  if lower case keys preferred, use ConfigParser
    self.__config = configparser.RawConfigParser( allow_no_value=True )
    self.__config.read( strconfname )
    logging.info( 'Loading configuration file: ' + strconfname );

    # fixing the inline comment problem
    for strsection in self.__config.sections():
      logging.info('Configure: ' + strsection)
      for strkey in self.__config[strsection]:
        strvalcomment = self.__config[strsection][strkey]
        #
        # assuming inline comments starting with '#'
        #
        strval = [x for x in strvalcomment.split('#')][0].strip()
        self.__config.set(strsection, strkey, strval)
        logging.info(' - ' + strkey + ' '+ strval)


  def get(self, strsection, strkey):
    """
      function to get a value by providing the section name and key name
    """
    if strsection not in self.__config.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return ""
    if strkey not in self.__config[ strsection ]:
      logging.error(' - ' + strkey + ' not found in config section: ' + strsection )
      return ""
    return self.__config[ strsection ][ strkey ]

  def sections(self):
    """
      function to get the list of the sections in the config file
    """
    return self.__config.sections()

  def keys(self, strsection):
    """
      function to get the list of the sections in the config file
    """
    if strsection not in self.__config.sections():
      logging.error(' - ' + strsection + ' not found in config file: ' + self.strname )
      return []
    return list( self.__config[sections].keys() )
 
