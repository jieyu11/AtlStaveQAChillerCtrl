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
from tkinter import ttk
from ChillerRdDevices import *
from ChillerRdCmd import *

class clsDeviceGUI:
  def __str__(self):
    print( 'Class name: ' + self._name );

  def __init__(self, strname, istDeviceHdl = None, istCommand = None):
    """
      function of initialization for any device
    """
    self._name = strname
    self._istDeviceHdl = istDeviceHdl
    self._istCommand = istCommand

    self._topwindow = Tk()
    
    # setup the style for every widget
    # check styles: http://wiki.tcl.tk/37701
    ttk.Style().theme_use('clam')

    # define the size of the window and the
    # position on the screen with
    # widthxheight+xoffset+yoffset
    self._topwindow.geometry("400x400+300+300")
    self._topwindow.title("Stave QA System")

    # start and stop bottoms
    # row = 0 is covered by head
    self.setupHead()

    self._frameChiller  = None
    self._framePump     = None
    self._frameHumidity = None
    self._frameThermocouple = None
    if istDeviceHdl is not None :
      for strdevname in istDeviceHdl.getdevicenames() : 
        if strdevname == 'Chiller':
          self._frameChiller = Frame( self._topwindow, bg = "White")
          self.setupChiller( intRow = 1, intColumn = 0 )
        elif strdevname == 'Pump':
          self._framePump = Frame( self._topwindow, bg = "Red" )
          self.setupPump( intRow = 2, intColumn = 0 )
        elif strdevname == 'Humidity':
          self._frameHumidity = Frame( self._topwindow, bg = "Grey" )
          self.setupHumidity(  intRow = 2, intColumn = 1 )
        elif strdevname == 'Thermocouple':
          self._frameThermocouple = Frame( self._topwindow, bg = "Green" )
          self.setupThermocouple(  intRow = 1, intColumn = 1 )
     else :
       logging.error( 'No devices have been found for GUI!!! ' );

  def runRoutine(self) :
    """
      read the routine config file and execute run routine
    """
    print ('Running the designed loops!!!!')

  def stop(self) :
    """
      function to stop all running devices, esp. Pump and Chiller
      it can be called out of emergency OR
      the run routine is finished
    """
    if self._istCommand is not None and self._istDeviceHdl is not None:
      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( 'iStop' )
      logging.info( 'Stopping the Pump' );
      istDeviceHdl.readdevice(strdevname, strcmdname, strcmdpara)

      strdevname, strcmdname, strcmdpara = self._istCommand.getdevicecommand( 'cStop' )
      logging.info( 'Stopping the Chiller' );
      istDeviceHdl.readdevice(strdevname, strcmdname, strcmdpara)

    elif self._istCommand is None:
      logging.error( 'No Command Instance found for GUI!!! ' );
    elif self._istDeviceHdl is None:
      logging.error( 'No Device Instance found for GUI!!! ' );
      
  def 


  def setupHead(self) :
    """
      function to set up start and stop buttons
    """
    self._frameRun = Frame( self._topwindow )
    self._frameRun.grid(row = 0, column = 0, padx = 4, pady = 2, sticky = W)
    _runButton = Button(self._frameRun, text=" RUN ", command = self.runRoutine )
    _runButton.grid(row = 0, column = 0, fg="Green", font = "Arial 16 bold")

    self._frameStop = Frame( self._topwindow )
    self._frameStop.grid(row = 0, column = 1, padx = 4, pady = 2, sticky = W)
    _stopButton = Button(self._frameStop, text=" STOP! ", command = self.stop )
    _stopButton.grid(row = 0, column = 0, fg="Red", font = "Roman 18 bold italic")

  def setupChiller(self, intRow=1, intColumn=0):
    """
      function to set up Chiller frame GUI
    """
    self._frameChiller.grid(row = intRow, column = intColumn, sticky = W)
    #self._frameChiller.grid(row = 1, column = 0, sticky = W)
    Label( self._frameChiller, text = " CHILLER ", bg = "Blue", fg = "Magenta" ).grid(row = 0, column = 0, padx = 5, pady = 3, sticky=E )

    Label( self._frameChiller, text = "Status: ", bg = "Blue" ).grid(row = 1, column = 0, padx = 2, sticky=W )
    Entry( self._frameChiller, width=20, bg = "Blue").grid(row=1, column=1)
    Label( self._frameChiller, text = "Set Point: ", bg = "Blue" ).grid(row = 2, column = 0, padx = 2, sticky=W )
    Entry( self._frameChiller, width=20, bg = "Blue").grid(row=2, column=1)
    Label( self._frameChiller, text = "Change Set Point: " , bg = "Blue").grid(row = 3, column = 0, padx = 2, sticky=W )
    Entry( self._frameChiller, width=20, bg = "Blue").grid(row=3, column=1)


  def setupPump(self):
    """
      function of reading device data
    """
      self._framePump.title("Pump")
      self._framePump.grid(row = 0, column = 0, sticky = W)
      Label( self._framePump, text = "Set Point: " ).grid(row = 0, column = 0, padx = 2, sticky=W )


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
      flttemperatures = (0,0,0,0)
      istThermo = istDeviceHdl.getdevice( "Thermocouple" )
      if istThermo is not None:
        flttemperatures = istThermo.last()

      self._frameThermocouple.title("Thermocouple")
      self._frameThermocouple.grid(row = 1, column = 0, sticky = W)

      Label( self._frameThermocouple, text = " Status " ).grid(row = 0, column = 0, padx = 4, pady = 2, sticky=W )

      Label( self._frameThermocouple, text = " Ambient (#circ C) " ).grid(row = 1, column = 0, padx = 2, sticky=W )
      Button( self._frameThermocouple, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( flttemperatures[0] ).pack()
      Label( self._frameThermocouple, text = " Box     (#circ C) " ).grid(row = 2, column = 0, padx = 2, sticky=W )
      Button( self._frameThermocouple, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( flttemperatures[1] ).pack()
      Label( self._frameThermocouple, text = " Inlet   (#circ C) " ).grid(row = 3, column = 0, padx = 2, sticky=W )
      Button( self._frameThermocouple, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( flttemperatures[2] ).pack()
      Label( self._frameThermocouple, text = " Outlet  (#circ C) " ).grid(row = 4, column = 0, padx = 2, sticky=W )
      Button( self._frameThermocouple, text = " = ", command = lambda : \
              messagebox.showinfo( message = str( flttemperatures[3] ).pack()


