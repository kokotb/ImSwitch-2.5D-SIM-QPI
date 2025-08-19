from imswitch.__main__ import main
import shutil
import os



# Deletes only file needed to be able to choose config file at startup
# os.remove('C:/Users/SIM_admin/Documents/ImSwitchConfig/config/imcontrol_options.json')
# os.remove('C:/Users/Bostjan Kokot/Documents/ImSwitchConfig/config/imcontrol_options.json')
# os.remove('C:/Users/Administrator/Documents/ImSwitchConfig/config/imcontrol_options.json')

# FIXME: Remove if .json is confirmed to work well
# Deletes whole config folder
#David
# shutil.rmtree('C:/Users/SIM/Documents/ImSwitchConfig')
#Microscope Computer
# shutil.rmtree(R'C:/Users/SIM_admin/Documents/ImSwitchConfig')  
main()  



   