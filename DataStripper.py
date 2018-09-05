'''
DataStripper. py --------------------------------------------------------------

Author: William Heidorn, Iowa State University, USA

A program that reads *.log files from the ISU chiller control system and
converts them into a readable csv file.

'''
import sys
import os


intCounter = 29
Toggle = False

#Defines the counter used which is a global used to correct the temperature time values 
def intCounterMinus():
  global intCounter
  intCounter += -1
def intCounterReset():
  global intCounter
  intCounter = 29

def GetDate( Line ):
  '''
    Calculates the date and returns the time in seconds assuming 0s is Jan 1, 0
  '''
  strDate = str(Line)[:10]  
  intYear = int(str(strDate)[6:])
  intMonth = int(str(strDate)[:2])
  intDay = int(str(strDate)[3:5])

  for intMonthCounter in range (1,intMonth):
    if intMonthCounter == 2:
      if intYear % 4 == 0:
        intDay += 29
      else:
        intDay += 28
    elif intMonthCounter == 4 or intMonthCounter == 6 or intMonthCounter == 9 or intMonthCounter == 11:
      intDay += 30
    else:
      intDay += 31

  if intYear % 4 == 0:
    intDay += intYear * 366
  else:
    intDay += intYear * 365

  fltDateTime = intDay * 24 * 3600
  return fltDateTime

#Finds the time from a given line of the log and returns a flt time in seconds
def GetTime( Line ):
  '''
    Calculates the time from a given line of the logfile
  '''
  strAMorPM = str(Line)[20:22]
  strTime = str(Line)[11:19]
  fltDate = GetDate(Line)
    
  fltTime = sum(x * int(t) for x, t in zip([3600, 60, 1], strTime.split(":")))
  
  if strAMorPM == 'PM' and str(Line)[11:13]!='12':
    fltTime = fltTime + 3600*12
  elif strAMorPM == 'AM' and str(Line)[11:13]=='12':
    fltTime = fltTime - 3600*12

  fltTime+=fltDate
  #print(strTime+' '+strAMorPM+' '+strDate+' '+str(fltTime))
  return fltTime

#Finds information from a useful line and adds it to the csv file
def ReadLine( Line,fltStartTime):
  '''
    Function that converts a single line of code into a date, time and info string
  '''
  absfltTime = GetTime(Line)
  fltTime = absfltTime- fltStartTime #Gets the time since the program started 

  RPS = ' '
  FlowRate = ' '
  TRes = ' '
  T1 = ' '
  T2 = ' '
  T3 = ' '
  T4 = ' '
  TSet = ' '
  Hum = ' '
  TH1 = ' '
  TH2 = ' '

  RUN = '0' # No routine notification
            # 1 Notification that is not determined
            # 2 Waiting for fluid to reach set temp
            # 3 Waiting for slope to flatten
            # 4 Reached set temp

  global Toggle

  if '<DATA>' in Line: #IT is a data line
    Line = Line.split('<DATA>')[-1]
    if 'Arduino' in Line: # It is a flow rate measurement
      string = Line.split('=')[-1]
      string = string.strip(' l/min\n')
      FlowRate = string

      #print(FlowRate)
    elif 'TempReadings' in Line: #Temperature Readings
      if 'TRes' in Line: #Temp from chiller
        string = Line.split('=')[-1]
        string = string.strip(' \n')
        TRes = string
        #print(TRes)
      else: #Temp from temperature logger
        string = Line.strip('TempReadings \n')
        string = string.split(',')
        T1 = string[0].split(':')[-1]
        T2 = string[1].split(':')[-1]
        T3 = string[2].split(':')[-1]
        T4 = string[3].split(':')[-1]
        global intCounter # This changes the time so that it will be correct
        fltTime = fltTime -float(intCounter)
        absfltTime = absfltTime - float(intCounter)
        intCounterMinus() #Subtracts one from the counter
        #print(T1)
        
    elif 'Temps' in Line: #Get set temperature
      string = Line.strip('Temps TSet: ')
      string = string.split(',')
      string = string[0]
      TSet = string
      #print(TSet)

    elif 'Humidity' in Line: #Get humidity and its temperatures
      string = Line.strip(' \n')
      string = string.split(',')
      Hum = string[0].split(':')[-1]
      TH1 = string[1].split(':')[-1]
      TH2 = string[2].split(':')[-1]
      #print(Hum)

  if 'RUNNING' in Line:
    Line = Line.split("< RUNNING >")[-1]
    
    # RUNNING Commands
    if 'Changing Temperature' in Line:
      RUN = '2'
      string = Line.split(':')[-1]
      string = string.split('C')
      string = string.strip(' ')
      TSet = string
    elif 'Waiting 1 min for TRes' in Line:
      RUN = '2'
      string = Line.split(':')[-1]
      if 'Waiting' in string:
        return
      string = string.strip(' \n')
      TSet = string
    elif 'Routine waiting' in Line:
      RUN = '3'
    elif 'Stave reached' in Line:
      RUN = '4'
    else:
      RUN = '1'
      if 'Pump Set' in Line:
        string = Line.split(':')[-1]
        string = string.strip(' \n')
        RPS = string
      elif 'Chiller Set' in Line:
        string = Line.split(':')[-1]
        string = string.strip(' \n')
        TSet = string
        RUN = '2'
      elif 'Arduino Toggled' in Line:
        if Toggle == True:
          Toggle = False
        else:
          Toggle = True

  #Create Averaged Temperature
  if T1 == ' ':
    TStave = ' '
  else:
    TStave = str((float(T1)+float(T2))/2.)
      

  strLine =str(fltStartTime)+','+str(fltTime)+','+TSet+','+TRes+','+T1+','+T2+','+T3+','+T4+','+Hum+','+RPS+','+FlowRate+','+TH1+','+TH2+','+TStave+','+RUN+','+str(int(Toggle))
  return strLine

# -----------------------------------------------------------------------------
# The main loop----------------------------------------------------------------

def main():
  """
  This is the main loop
  """
  if sys.version_info[0] < 3:
    print ("ERROR: Code works for python version 3 only")
    raise Exception(" Wrong python version")

  #Load in the input file
  nargv = len(sys.argv)
  inputfiles = []
  if (nargv <= 1):
    print("ERROR: Please provide log file")
    return
  else:
    for i in range(1,nargv):
      inputfiles.append(sys.argv[i])  

  strLogName = inputfiles[0]
  #strLogName = str(input('Type the name of the file you wish to use: \n'))
  #strLogName = "../2018-09-04_10-12AM_ChillerRun(TestStave1).log"
  
  #Load in the file  
  try:
    inputFile = open(strLogName,'r')
  except:
    print("Data file "+ strLogName + " not found! Plotting last output in memory!")
    return 
 
  Line = inputFile.readline()
  fltStartTime = GetTime(Line)
  #Creates a new output csv file with initial conditions  
  outputFile = open('output.csv','w')  
  Startline = 'absTime[s],relTime[min],Tset[C],TRes[C],T1[C],T2[C],T3[C],T4[C],THum[%],RPS[rps],FlowRate[l/min],TH1[C],TH2[C],TStave[C],RUN,Toggle[bol]\n' 
  outputFile.write(Startline)
  outputFile.close()
  #Opens the csv file to append our data to it
  outputFile = open('output.csv','a')
  
  intCounterReset()
  DataList=[]
  i=0
  
  # Reads the input file and makes a data list
  for line in inputFile:
    try:
      strLine = ReadLine(line,fltStartTime)
    except:
      continue
    if strLine != None:
      DataLine = strLine.split(',') #Takes the string line and reads it as a list
      DataLine[1] = float(DataLine[1])#Converts the second data point(relative time) to a float
      DataList.append(tuple(DataLine)) # converts each line to a tuple 
      i+=1
    if intCounter == 0:
      intCounterReset()

  #Sorts the data by the time value
  DataListSorted = sorted(DataList,key =lambda data: data[1]) 

  #Combines lines with multiple sets of information
  DataListCondensed = []
  linesToSkip = 0
  for line in range(len(DataListSorted)-1):
    if linesToSkip > 0:
      linesToSkip += -1
      continue
    lineTime = DataListSorted[line][1]
    linesToSkip = 0
    NextLineTime = DataListSorted[line+1][1] 
    NewLine = list(DataListSorted[line])
    while lineTime == NextLineTime:
      for i in range(len(DataListSorted[line])):
        Data1 = NewLine[i]
        Data2 = DataListSorted[line+1+linesToSkip][i]
        if Data1 == Data2:
          NewLine[i] = Data1
        elif Data1 == ' ':
          NewLine[i] = Data2
        elif Data1 == '0':
          NewLine[i] = Data2            
      linesToSkip+=1
      try:
        NextLineTime = DataListSorted[line+1+linesToSkip][1]
      except:
        NextLineTime = 999999999
    if linesToSkip> 0:
      DataListCondensed.append(tuple(NewLine))
    else:
      DataListCondensed.append(DataListSorted[line])

  #Writes the data list to the output file as a simple set of numbers separated by commas
  nvars = 16
  oldLine = [0. for i in range(nvars)]
  #Remove blank spots with old lines
  for line in DataListCondensed:
    line = list(line)
    for i in range(nvars):
      if line[i] ==' ':
        line[i] = oldLine[i]
      else:
        oldLine[i] = line[i]
      if i == 1: #Convert time from seconds to min
        strTimeSec = line[i]
        strTimeMin = str(float(strTimeSec)/60.)
        line[i] = strTimeMin 
    strline = str(line)
    strline = strline.strip("[] ")
    strline = strline.replace("'","")
    outputFile.write(strline+'\n')

if __name__  == '__main__' :
  main()
