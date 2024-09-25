import json
import numpy as np
from datetime import datetime
import tifffile as tif
import numpy as np
from decimal import Decimal
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.model import configfiletools
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.model.dirtools import DataFileDirs
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
        # print('test')
        self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        # self._logger.warning("Shared attributes updated.")
        
    # def saveAttributesToFile(self):
    #     # Filter out only the important attributes?
        
    #     # Save attributes
    #     dir_harcoded = 'C:/Users/SIM_admin/Documents/ImSwitchConfig'
    #     file_name_hardcoded = "exp_metadata"
    #     # with open(os.path.join(dir_harcoded, file_name_hardcoded), 'w') as setupFile:
    #     #     setupFile.write(self.shared_attributes.to_json(indent=4))
        
    #     self._logger.warning("Attributes saved.")


    def getAttrs(self):
        """ Returns a JSON representation of this instance. """
        attrs = {}
        for key, value in self.shared_attributes.items():
            parent = attrs
            for i in range(len(key) - 1):
                if key[i] not in parent:
                    parent[key[i]] = {}
                parent = parent[key[i]]

            parent[key[-1]] = value
        # jsonOutput = json.dumps(attrs)
        jsonOutputPretty = json.dumps(attrs, indent=4)

        return jsonOutputPretty
    
    def getAndSaveJSON(self):
        jsonOutput = self.getAttrs()
        with open("JSONTest.json", "w", encoding='utf-8') as outfile:
            outfile.write(jsonOutput)

    def saveJSON(self, jsonOutput):
        with open("JSONTest.json", "w", encoding='utf-8') as outfile:
            outfile.write(jsonOutput)
        self._logger.warning("Attributes saved.")

    def getHDF5Attributes(self):
        """ Returns a dictionary of HDF5 attributes representing this object.
        """
        attrs = {}
        for key, value in self.shared_attributes.items():
            attrs[':'.join(key)] = value

        return attrs
    
    # def saveHDF5Attributes(self):
    #     """ Saves a dictionary of HDF5 attributes representing this object.
    #     """
    #     attrs = {}
    #     for key, value in self.shared_attributes.items():
    #         attrs[':'.join(key)] = value

    #     return attrs