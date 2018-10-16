'''
  Python class ArduinoDevice.py
  
Description: ------------------------------------------------------------------
   This file contains the class construct to perform I/O with the USB connected
Arduino UNO V3 and the DF Robot relay shield attached to the Arduino shield.
The Arduino monitors the analog voltage from the flowmeter (Proteus 08004BN1)
and via the DF Robot relays control the open/close state of the 3 actuator 
valves (Swagelok SS-62TS4-41DC) located at the coolant I/O end of the stave.

History: ----------------------------------------------------------------------
   V1.0 - Aug-2018  First public release.

Environment: ------------------------------------------------------------------
   This program is written in Python 3.6.  Python can be freely downloaded
from http://www.python.org/.  This program has been tested on PCs running 
Windows 10.

Author List: -------------------------------------------------------------------
  R. McKay    Iowa State University, USA  mckay@iastate.edu
  J. Yu       Iowa State University, USA  jieyu@iastate.edu
  W. Heidorn  Iowa State University, USA  wheidorn@iastate.edu
  
Notes: -------------------------------------------------------------------------
   To install the serial module on your local computer, go to 
https://github.com/pyserial/pyserial and install by typing: 
pip3.6 install pyserial in a DOS command window.

Dictionary of abbreviations: ---------------------------------------------------
    bol - boolean
  cls - class
  flt - float
  int - integer
  lst - list
  str - string

'''

# Import section --------------------------------------------------------------

import serial             # Serial communications over USB ports.
import logging            # Flexible event logging functions/classes.
import time
from enum import IntEnum  # Class to define enumerators.
import random             # Generate pseuo-random numbers.

# User defined classes
from ChillerDevices import  clsDevice# Allows reading from devices.
from ChillerPseudoDevices import clsPseudoDevice
# Class global variables/enumerators


# ------------------------------------------------------------------------------
#  Use enumerators for possible states of actuator valve: open and close.
class valveState(IntEnum):
  OPEN = 0
  CLOSE = 1
  
# ------------------------------------------------------------------------------
class clsArduino (clsDevice):
  def __init__(self, strName, strPort, intBaud=9600, bytesize=8, parity='N', stopbits=1, 
               timeout=None):
    '''
      Constructor function for the Arduino.  Set the USB communication protocal and the
    power up state of the actuator valves.  Note: the Arduino upon power up sets the
    actuator valves to: Bypass - open, Input=Output - close.
    '''
    
    super().__init__(strName, strPort, intBaud, bytesize, parity, stopbits, timeout)
    self._strClassName = '< Arduino >'
    self.strName = 'Arduino'
    self._enumBypassValve = valveState.OPEN  # Power up state of the bypass valve.
    self._enumInValve = valveState.CLOSE     # Power up state of the input valve.
    self._enumOutValve = valveState.CLOSE    # Power up state of the output valve.
    self._lstValveState = ['Open', 'Close']   # Possible states of valves.
    self._value = 0

  def read(self, strCmdName, strCmdPara="",fltTempsfltRPS=[[],[]]):
    fltCurrentTemps = fltTempsfltRPS[0]
    logging.debug( self._strClassName + ' Sending command ' + strCmdName + ' to device ' + self.strName )
    staveTemp = fltCurrentTemps[3] #This should be the outflow
    
    if strCmdName == 'F':
      rate1 = clsArduino.readFlowRate(self, staveTemp) #This can be made better
      time.sleep(2)
      rate2 = clsArduino.readFlowRate(self, staveTemp) #This can be made better
      time.sleep(2) 
      rate3 = clsArduino.readFlowRate(self, staveTemp) #This can be made better
      self._value = (rate1+rate2+rate3)/3.

    elif strCmdName == 'V':
      bolTog = clsArduino.toggleValves(self)
      self._value = bolTog

    elif strCmdName == 'S':
      bolOn = clsArduino.status(self)
      self._value = bolOn

    logging.debug( self._strClassName + 'Command received')
  def last(self):
    return self._value

# ------------------------------------------------------------------------------
  def readFlowRate(self, fltCoolantTemp):
    '''
      Read the flowrate from the Arduino.  The Arduino has converted the flowmeter 
    analog voltage to a digital value. The flowmeter value must be converted to
    the correct flow rate.  The conversion is a linear equation:
      flow rate = slope * flowmeter value + offset.
    The offset is a function of the viscosity (i.e. temperature) of the coolant.
    The offset is a linear equation:
      offset = slope * temperature + fudge factor.
    The flow rate units are liters/minute.  Coolant temperature is Celsius.
      
      The value returned is a text string of the computed flow rate.  IF there
    was an error in reading the flowmeter analog value, return -1.00 for flow rate.
    '''
    # Flow rate approximation is as given by: 
    # F(V,T) = c0+c1V+c2T+c3VT+c4V^2+c5T^2+c6V^2T+c7VT^2+c8V^2T^2  #### Yale Calibration Oct 15 2018
    c0,c1,c2,c3,c4,c5,c6,c7,c8 = -0.424,1.393,0.00220,-0.00484,-0.0587,-1.12e-5,.00126,1.91e-5,-8.51e-8
    self._pdev.write(('F\n').encode())
    logging.debug(self._strClassName + ': Sent command F (read Flowrate) to Arduino')

    # Read the returned text.  Should return "OK X.XX"
    byteline = self._pdev.readline()
    strReturnText = byteline.decode()
    #strReturnText = self._pdev.readline() 
       
    if "OK" in strReturnText:
      intIndex = strReturnText.index("K") + 2        # Find end of "OK " in text.
      fltFlowValue = float(strReturnText[intIndex:])  # Convert text value to float.
      T = fltCoolantTemp
      V = fltFlowValue
      fltFlowRate = c0+c1*V+c2*T+c3*V*T+c4*V*V+c5*T*T+c6*V*V*T+c7*V*T*T+c8*V*V*T*T
      if fltFlowRate < 0:
        fltFlowRate = 0.
      logging.info("<HIDDEN> Arduino Voltage: "+str(round(fltFlowValue,3)))
    else:
      fltFlowRate = -1.0      
      logging.warning(' Received for flowrate: ' + strReturnText)
      
    return fltFlowRate
    
# ------------------------------------------------------------------------------
  def toggleValves(self):
    '''
      Toggle the 3 actuator valves.  The in & out valves are toggled to be in opposite state 
    (open,closed) to the bypass valve.  Hence, if the bypass valve is open, the in/out valves 
    are closed and vice versa.  Since there is no reading of the state of each actualtor 
    valves, the code assumes the valves are in a proper state and just toggles from one state 
    to the other.
    
    The value return is boolean: True if operation completed, False if error.
    '''

    self._pdev.write(('V\n').encode())
    logging.debug(self._strClassName + ' Sent command V (toggle Valves) to Arduino')

    # Read the returned text.  Should return "OK" 
    byteline = self._pdev.readline()
    strReturnText = byteline.decode()
    if "OK" in strReturnText:
      # Update the assumed state of the actuator valves.
      self._enumBypassValve = not self._enumBypassValve
      self._enumInValve = not self._enumInValve
      self._enumOutValve = not self._enumOutValve
      bolResult = True
      logging.info(' Toggled valves to: Bypass:' + self._lstValveState[self._enumBypassValve] + \
                   ' Input:' + self._lstValveState[self._enumInValve] + \
                   ' Output:' + self._lstValveState[self._enumOutValve])
    else:
      logging.error(' <ERROR> Invalid response from Arduino to toggle actuators.')
      bolResult = False
    
    return bolResult

# ------------------------------------------------------------------------------
  def status(self):
    '''
      Acquire the state of the 3 actuator valves (i.e. open or close).
      
      Return a list of the actuator states: open or close.  If error then
    return [?,?,?]
    '''
    
    self._pdev.write(('S').encode())    
    logging.debug(self._strClassName + " Acquire Arduino status.")
    
    # Read the returned text.  Should return "OK Bypass:OC In:OC Out:OC"
    #   where OC = Open or Close.
    strReturnText = self._pdev.read(33)
    if "OK" in strReturnText:
      intIndex = strReturnText.index(":",3) + 1   # Find end of "Bypass:" in text.
      strBypass = strReturn[index:index+5]
      intIndex = strReturnText.index(":",12) + 1  # Fine the end of "In:" in text.
      strInput = strReturn[index:index+5]
      intIndex = strReturnText.index(":",20) + 1  # Fine the end of "Out:" in text.
      strOutput = strReturn[index:index+5]
    
    # Set this code's values for actuator valves to match what Arduino sent back.
      if strBypass == 'Open':
        self._enumBypassValve = valveState.OPEN
      else:
        self._enumBypassValve = valveState.CLOSE
      strBypass = self._lstVavleState[self._enumBypassValve]
    
      if strInput == 'Open':
        self._enumInValve = valveState.OPEN
      else:
        self._enumInValve = valveState.CLOSE
      strInput = self._lstVavleState[self._enumInValve]

      if strOutput == 'Open':
        self._enumOutValve = valveState.OPEN
      else:
        self._enumOutValve = valveState.Close
      strOutput = self._lstVavleState[self._enumOutValve]

      lstResult = [strBypass, strInput, strOutput]
      
      logging.info(' Valve states: ' + \
                   ' Bypass:' + strBypass + \
                   ' Input:' + strInput + \
                   ' Output:' + strOutput)
    else:
      logging.error(' <ERROR> Invalid response from Arduino to toggle actuators.')
      lstResult = ['?', '?', '?']
    
    return lstResult        

# ------------------------------------------------------------------------------
class clsPseudoArduino(clsPseudoDevice):
  def __init__(self, strname):
    '''
      Construtor for Pseudo Arduino.  Set the power up state of the actuator valves.
    '''
    self._strClassName = 'Arduino'
    self.strName = 'Arduino'
    self._enumBypassValve = valveState.OPEN  # Power up state of the bypass valve.
    self._enumInValve = valveState.CLOSE     # Power up state of the input valve.
    self._enumOutValve = valveState.CLOSE    # Power up state of the output valve.
    self._value = 5 
    random.seed()   # Initalize the random number generator.

  def read(self, strCmdName, strCmdPara="",fltTempsfltRPS=[[],[]]):
    fltCurrentTemps = fltTempsfltRPS[0]
    fltRPS = fltTempsfltRPS[1]

    logging.debug( self._strClassName + ' Sending command ' + strCmdName + ' to device ' + self.strName )
    staveTemp = fltCurrentTemps[3]

    if strCmdName == 'F':
      rate = clsPseudoArduino.readFlowRate(self, staveTemp) #This can be made better
      self._value = rate

    elif strCmdName == 'V':
      bolTog = clsPseudoArduino.toggleValves(self)
      self._value = bolTog

    elif strCmdName == 'S':
      bolOn = clsPseudoArduino.status(self)
      self._value = bolOn

    logging.debug( self._strClassName + 'Command received')
  def last(self):
    return self._value

    
# ------------------------------------------------------------------------------
  def readFlowRate(self, fltCoolantTemp):
    '''
      Fake an Arduino flow rate reading. For 90% of the time return a flow rate that
    is about 1 liter/minute.  For 10% of the time return -1.0 to simulate an error.
    '''
 
    fltNum = random.random()
    if fltNum < 0.99:             # Operation OK.
      fltVoltage = random.random()*0.05+ 1.
      fltFlowRate = -0.19 + 1.18*fltVoltage - 0.0019*fltCoolantTemp +2.6e-5*fltCoolantTemp*fltCoolantTemp
      logging.info("<HIDDEN> Arduino Voltage: "+str(round(fltNum,3)))
    else:
      fltFlowRate = -1.0


    time.sleep(2)
    return fltFlowRate 

# ------------------------------------------------------------------------------
  def toggleValves(self):
    '''
      Fake an Arduino toggling the actuator valves. For 90% of the time toggle 
    actuator states & return boolean True.  For 10% of the time return False to 
    simulate an error.
    '''

    fltNum = random.random()
    if fltNum < 0.9:             # Operation OK.
      self._enumBypassValve = not self._enumBypassValve
      self._enumInValve = not self._enumInValve
      self._enumOutValve = not self._enumOutValve
      bolResult = True
    else:                        # Give a chance of failure.
      bolResult = False
    
    return bolResult

# ------------------------------------------------------------------------------
  def status(self):
    '''
      Return the fake actuator valves' state.  For 90% of the time return the 
    actuator states and for 10% of the time return False to simulate an error.
    '''
        
    fltNum = random.random()
    if fltNum < 0.9:             # Operation OK.
      strBypass = self._lstValveState[self._enumBypassValve]
      strInput = self._lstValveState[self._enumInputValve]
      strOutput = self._lstValveState[self._enumOutputValve]
      lstResult = [strBypass, strInput, strOutput]
    else:                        # Give a chance of failure.
      lstResult = ['?', '?', '?']
    
    return lstResult

