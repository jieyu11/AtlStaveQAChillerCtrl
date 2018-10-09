'''
FindInfo. py --------------------------------------------------------------

Author: William Heidorn, Iowa State University, USA

A program that reads *.log files from the ISU chiller control system and
converts them into a readable csv file.

usage: ./FindInfo.py [output.csv] [time] [duration]

     time: this is the time that you are looking at it can either be absolute time or the real time
           mm-dd-yyyy_hh-mm-ss

           or this could be the relative time in minutes
           min

     duration: This is the amount of data to look at 

'''
import sys
import os
import csv

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

  strTime = str(Line)[11:19]
  fltDate = GetDate(Line)
    
  fltTime = sum(x * int(t) for x, t in zip([3600, 60, 1], strTime.split("-")))

  fltTime+=fltDate
  #print(strTime+' '+strAMorPM+' '+strDate+' '+str(fltTime))
  return fltTime

def main():
  """
  This is the main loop
  """
  if sys.version_info[0] < 3:
    print ("ERROR: Code works for python version 3 only")
    raise Exception(" Wrong python version")

  #Load in the input conditions
  nargv = len(sys.argv)
  inputfiles = []
  if (nargv <= 2):
    print("ERROR: Please provide  ./FindInfo.py [time] [duration] [file to read=output.csv]")
    return
  elif nargv == 3:
    strTime = sys.argv[1]
    strDuration = sys.argv[2]
    filename = "output.csv"
  else:
    strTime = sys.argv[1]
    strDuration = sys.argv[2]
    filename = sys.argv[3]

  print("\n\tLOADED: "+filename)
  print("\tTime  : "+strTime)
  print("\tDur.  : "+strDuration+"\n")

  #Load in the input csv
  try:
    ffile = open(filename,'r')
    csv_reader = csv.reader(ffile)
  except:
    print("ERROR: Failed to read csv file")

  #Generate Data Outline
  nlines = 0
  for row in csv_reader:
    if nlines == 0:
      datainfo = row
      nVar = len(datainfo)
    nlines += 1

  #Generate and fill data array
  ffile2 = open(filename,'r')
  csv_reader2 = csv.reader(ffile2)
  dataArray = [[0. for y in range(nlines-1)] for x in range(nVar)]
  timeList = [0. for y in range(nlines-1)]
  nrow = 0

  for row in csv_reader2:
    dataline = row
    if nrow == 0:
      nrow = 1 
      continue
    nitem = 0
    for item in dataline:
      dataArray[nitem][nrow-1] = float(item)
      if nitem ==1:
        dataArray[nitem-1][nrow-1] += float(item)*60 #Fixes the absolute start time output
      nitem+=1
    timeList[nrow-1] = dataArray[0][nrow-1] - dataArray[0][0]
    nrow+=1

  #Get the time
  if '-' in strTime:
    try: 
      fltTimeAbs = GetTime(strTime)
      fltTime = fltTimeAbs - dataArray[0][0]
    except:
      print("ERROR: Incorrect time. Input style is mm-dd-yyyy_hh-mm-ss")
      return
  else:
    try:
      fltTime = float(strTime)*60
    except:
      print("ERROR: Incorrect time. Input style is a float in min")
      return
  #Check the interval
  try:
    fltDuration = float(strDuration)*60
  except:
    print("ERROR: Incorrect duration format. It should be a number in min")
    return


  Tmin = fltTime - fltDuration/2.
  Tmax = fltTime + fltDuration/2.

  #Print out the averages for each row with std deviation
  for var in range(nVar):
    avgVal = 0
    stdDev = 0
    nPoints = 0

    #Get Average
    for line in range(nlines-1):
      #print(timeList[line])
      if Tmin < timeList[line] and timeList[line] < Tmax:
        #print(timeList[line])
        avgVal += dataArray[var][line]
        nPoints+=1
    if nPoints <= 0:
      print("ERROR: No points found in range specified")
      return  
    avgVal = avgVal/(nPoints)
    
    #Get StdDev
    for line in range(nlines-1):
      if Tmin < timeList[line] and timeList[line] <Tmax:
        stdDev += (dataArray[var][line]-avgVal)**2
    stdDev = (stdDev/nPoints)**0.5

    try:
      varName = datainfo[var].split("[")[0]
      varUnit = datainfo[var].split("[")[-1]
      varUnit = varUnit.strip("]")

    except:
      varName = datainfo[var]
      varUnit = ""

    #Print it out for each variable
    print("{0:>10}: {1:>8} +/- {2:<6} {3}".format(varName,str(round(avgVal,2)),str(round(stdDev,2)),varUnit))

if __name__  == '__main__' :
  main()
