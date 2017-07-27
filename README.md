#							                  ATLAS Stave Thermo Quality Assurance Testing

Introduction

	The program ChillerCtrl.py purpose is to control the coolant fluid temperature and flow through the ATLAS stave.  

Requirements
	
	*Software
	Any OS that supports Python.  Python 3.6.2 or greater interpreter.  200MB for Python and ?KB for ChillerCtrl.py. 
	
	*Hardware
	A computer with at least one RS-232 serial port and 4 USB ports.  One USB port is expected to have a USB to RS-485 adapter.
	The cooling system is composed of: FTS System RC211B0 recirculating cooler; Lenze ESV751N02YXC EMA 4x inverter drive;
	pump motor PVN56T17V5338B; and Liquiflo H5FSPP4B002606US-8(-60) booster pump.  The coolant used is 3M Novec 7100. 
	One of each: Omega HH147U temperature logger, Omega HH314A humidity logger, and Flir A655sc IR camera.

Installation

	Follow Python installer instructions for installing Python.  Place the ChillerCtrl.py in any desired directory.
	
Usage

	?
	
History

	?-Aug-2017 version 1.0 released.

Notice
 
  Following are the abbreviations used for variable/object identifications:
    int – integer
    str – string
    chr - char
    dict – dictionary
    bol – Boolean
    lng – long
    flt – float
    lst – list
    cls - class
    ist - class instance


Authors

	William Heidorn, Iowa State University,  USA  wheidorn@iastate.edu
	Jie Yu, Iowa State University,  USA  jieyu@iastate.edu
	Roy Mckay, Iowa State University, USA  mckay@iastate.edu
