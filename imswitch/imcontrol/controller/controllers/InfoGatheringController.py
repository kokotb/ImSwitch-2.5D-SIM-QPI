import requests
import json
import os
import glob

import numpy as np
import time
import threading
from datetime import datetime
import tifffile as tif
import os
import time
import numpy as np

from decimal import Decimal
import math
import logging
import sys


from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.model import configfiletools
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController


import pandas as pd



class InfoGatheringController(ImConWidgetController):
    """Linked to InfoGatheringWidget. Needs to be connected to widget to get initialized and connected to signals."""
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)

        # Connect signals to communications channel
        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.updateSharedAttributes)
        self._commChannel.sigSIMAcqToggled.connect(self.saveAttributesToFile)
        
        # Load experimental parameters into local object attribute
        self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data

        
    def updateSharedAttributes(self):
        self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        # self._logger.warning("Shared attributes updated.")
        
    def saveAttributesToFile(self):
        # Filter out only the important attributes?
        
        # Save attributes
        dir_harcoded = "C:\\Users\\Bostjan Kokot\\Documents\\ImSwitchConfig"
        file_name_hardcoded = "exp_metadata"
        # with open(os.path.join(dir_harcoded, file_name_hardcoded), 'w') as setupFile:
        #     setupFile.write(self.shared_attributes.to_json(indent=4))
        
        self._logger.warning("Attributes saved.")
    
