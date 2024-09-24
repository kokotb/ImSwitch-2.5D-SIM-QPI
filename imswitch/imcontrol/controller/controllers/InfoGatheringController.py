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
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController


import pandas as pd



class InfoGatheringController(ImConWidgetController):
    """Linked to SIMWidget."""
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)

        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.updateExperimentParameters)

        
    def updateExperimentParameters(self):
        print(f"testing\nInfoGatheringController")
