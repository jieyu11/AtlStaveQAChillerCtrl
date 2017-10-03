"""
device class to read from / write to USB connected devices:
  chiller
  boost pump
  thermocouple couple
  humidity sensor
  IR camcera
"""
import time
import logging
from tkinter import *
from ChillerRdDevices import *

class clsDeviceGUI:
  def __init__(self, strname, istDeviceHdl = None):
    """
      function of initialization for any device
    """
    self._name = strname
    self._istDeviceHdl = istDeviceHdl

    self._topwindow = Tk()
    
    # setup the style for every widget
    # check styles: http://wiki.tcl.tk/37701
    ttk.Style().theme_use('clam')

    # define the size of the window and the
    # position on the screen with
    # widthxheight+xoffset+yoffset
    self._topwindow.geometry("400x400+300+300")

    if strname == "" :
      self._topwindow.title("Stave QA System")
    else:
      self._topwindow.title( strname )

    self._frameChiller  = None
    self._framePump     = None
    self._frameHumidity = None
    self._frameThermocouple = None
    if istDeviceHdl is not None :
      for strdevname in istDeviceHdl.getdevicenames() : 
        if strdevname == 'Chiller':
          self._frameChiller = Frame( self._topwindow, bg = "White")
          self.setupChiller( )
        elif strdevname == 'Pump':
          self._framePump = Frame( self._topwindow, bg = "Red" )
          self.setupPump( )
        elif strdevname == 'Humidity':
          self._frameHumidity = Frame( self._topwindow, bg = "Grey" )
          self.setupHumidity( )
        elif strdevname == 'Thermocouple':
          self._frameThermocouple = Frame( self._topwindow, bg = "Green" )
          self.setupThermocouple( )
     else :
       logging.error( 'No devices have been found for GUI!!! ' );

  def __str__(self):
    print( 'Class name: ' + self._name );

  def setupChiller(self):
    """
      function of reading device data
    """
      self._frameChiller.title("Chiller")
      self._frameChiller.grid(row = 0, column = 0, sticky = W)
      Label( self._frameChiller, text = "Set Point: " ).grid(row = 0, column = 0, padx = 2, sticky=W )

  def setupHumidity(self):
    """
      function of reading device data
    """
      self._frameHumidity.title("Humidity")
      self._frameHumidity.grid(row = 1, column = 1, sticky = E)
      Label( self._frameHumidity, text = "Relative Humidity (%)" ).grid(row = 0, column = 0, padx = 2, sticky=W )
      Button( self._frameHumidity, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( istDeviceHdl.readdevice("Humidity", "Read", ""))) ).pack()

  def setupThermocouple(self):
    """
      function of reading device data
    """
      self._frameThermocouple.title("Thermocouple")
      self._frameThermocouple.grid(row = 1, column = 0, sticky = W)
      Label( self._frameThermocouple, text = " Ambient (#circ C) " ).grid(row = 0, column = 0, padx = 2, sticky=W )
      Label( self._frameThermocouple, text = " Box     (#circ C) " ).grid(row = 1, column = 0, padx = 2, sticky=W )
      Label( self._frameThermocouple, text = " Inlet   (#circ C) " ).grid(row = 2, column = 0, padx = 2, sticky=W )
      Label( self._frameThermocouple, text = " Outlet  (#circ C) " ).grid(row = 2, column = 0, padx = 2, sticky=W )
      Button( self._frameThermocouple, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( istDeviceHdl.readdevice("Thermocouple", "Read", ""))) ).pack()


