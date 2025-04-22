'''
@file	python_demo.py

Contains a short example of interfacing with the controller interface DLL in Python.

Note that since Python is not compiled, it does not know which DLL to pick up.  The user
must copy the relevant DLL into the same directory as the Python script, or modify the script.

@authors Graham Bartlett
@copyright Prior Scientific Instruments Ltd., 2017
'''

import ctypes
import sys
sys.path.insert(0, R"C:\Users\SIM_admin\Downloads\OneDrive_2025-04-17\Release 2.7.15\NPC-D_Digital_Controller_Interface_DLL_2.7.15\NPC-D Digital Controller Interface DLL Production Release\controller_interface\adapter\python")
import dll_adapter

# Start of main code
dll = dll_adapter.DllAdapter()
intSize = ctypes.sizeof(ctypes.c_voidp)

dllFile = R"C:\Users\SIM_admin\Downloads\OneDrive_2025-04-17\Release 2.7.15\NPC-D_Digital_Controller_Interface_DLL_2.7.15\NPC-D Digital Controller Interface DLL Production Release\controller_interface\bin\Windows\controller_interface64.dll"

isOk = dll.Init(dllFile)


if not isOk:
	print ("ERROR: Could not load DLL " + dllFile + " from current directory")
	sys.exit(-1)	
	

status = dll.OpenSession("COM18")
dll.DoCommand('controller.security.user.set 233573869')

if status == True:
	print("\nOpened OK")
	
	print("\nidentity.software.version.get")
	results = dll.DoCommand("identity.software.version.get")
	for result in results:
		print(result[0] + " : " + result[1])
		if result[0] == "version":
			version = int(result[1])
			majorVersion = (version >> 24) & 0xFF
			minorVersion = (version >> 16) & 0xFF
			buildVersion = version & 0xFFFF
			print("Controller firmware version is " + str(majorVersion) + "." + str(minorVersion) + "." + str(buildVersion))

	print("\nstage.position.measured.get 1")
	results = dll.DoCommand("stage.position.measured.get 1")
	for result in results:
		print(result[0] + " : " + result[1])
		if result[0] == "value":
			# Convert pm to microns
			resultMicrons = float(result[1]) * 1.0e-6
			print("This is " + str(resultMicrons) + " microns")

	dll.CloseSession()
	
else:
	print("\nCould not open")
	sys.exit(-2)
	
dll.Uninit()
