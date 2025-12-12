import imswitch.startTimer as startTimer
import time
startTimer.startTime = time.perf_counter()

from imswitch.__main__ import main
import shutil



# Deletes whole config folder

 #Registers start of program to announce start up time later.

#David
# shutil.rmtree('C:/Users/SIM/Documents/ImSwitchConfig')

#Jakob  
# shutil.rmtree(R'C:\Users\JakobC\Documents\ImSwitchConfig')

# #Microscope Computer
shutil.rmtree(R'C:/Users/SIM_admin/Documents/ImSwitchConfig')  


main()

