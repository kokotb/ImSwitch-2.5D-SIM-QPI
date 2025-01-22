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
        # self._commChannel.sigSIMAcqToggled.connect(self.saveAttributesToFile)
        self._widget.saveSettings.clicked.connect(self.getAndSaveJSON)
        
        # Load experimental parameters into local object attribute
        self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        self.wantedAttributes = [('Laser', '488AOTF', 'Value'),('Laser', '488AOTF', 'Enabled'),('Laser', '561AOTF', 'Value'),('Laser', '561AOTF', 'Enabled'),
                            ('Laser', '640AOTF', 'Value'),('Laser', '640AOTF', 'Enabled'),('Positioner', 'Z', 'Z', 'Position'),
                            ('Positioner', 'XY', 'X', 'Position'),('Positioner', 'XY', 'Y', 'Position'),('Tiling Settings', 'Steps - X'),
                            ('Tiling Settings', 'Steps - Y'),('Tiling Settings', 'Overlap'),
                            ('Tiling Settings', 'Tiling Checkbox'),('Timing Settings', 'Timing Unit'),('Timing Settings', 'Timing Period'),('Timing Settings', 'Duration'),
                            ('Timing Settings', 'Duration Unit'),('Timing Settings', 'Repetitions'),('Timing Settings', 'Rep Checkbox'),('Timing Settings', 'Duration Checkbox'), ('Detector', '488 Cam', 'Model'), 
                            ('Detector', '488 Cam', 'ROI'),('Detector', '488 Cam', 'Param', 'ExposureTime'),('Detector', '488 Cam', 'Param', 'Gain'),
                            ('Detector', '488 Cam', 'Param', 'Gamma'),('Detector', '488 Cam', 'Param', 'TriggerMode'),('Detector', '561 Cam', 'Model'),
                            ('Detector', '561 Cam', 'ROI'),('Detector', '561 Cam', 'Param', 'ExposureTime'),('Detector', '561 Cam', 'Param', 'Gain'),
                            ('Detector', '561 Cam', 'Param', 'Gamma'),('Detector', '561 Cam', 'Param', 'TriggerMode'),('Detector', '640 Cam', 'Model'),
                            ('Detector', '640 Cam', 'ROI'),('Detector', '640 Cam', 'Param', 'ExposureTime'),('Detector', '640 Cam', 'Param', 'Gain'),
                            ('Detector', '640 Cam', 'Param', 'Gamma'),('Detector', '640 Cam', 'Param', 'TriggerMode'),('SIM Parameters', 'ReconWL1'),
                            ('SIM Parameters', 'ReconWL2'),('SIM Parameters', 'ReconWL3'),('SIM Parameters', 'NA'),('SIM Parameters', 'Pixelsize'),
                            ('SIM Parameters', 'Alpha'),('SIM Parameters', 'Beta'),('SIM Parameters', 'w'),('SIM Parameters', 'eta'),
                            ('SIM Parameters', 'n'),('SIM Parameters', 'Magnification'),('SIM SLM', 'SLM Running Order'),('User Dir Info', 'Working Directory'), ('User Dir Info', 'Current Path'),
                            ('User Dir Info', 'User Name'),('User Dir Info', 'Experiment Name'),('Z-Stack Settings', 'Step Size'),('Z-Stack Settings', 'Total Z (/um)'),('Z-Stack Settings', 'Z-Stack Checkbox'),
                            ('Z-Stack Settings','Scan Direction'),('Z-Stack Settings','Z-Stack Center?'),('Z-Stack Settings','Scan Start Offset'), ('ROI List', 'List'),
                            ('25D SLM Parameters', 'Gamma'),('25D SLM Parameters', 'Psi'),('25D SLM Parameters', 'Left Center-X'),('25D SLM Parameters', 'Left Center-Y'),('25D SLM Parameters', 'Right Center-X'),
                            ('25D SLM Parameters', 'Right Center-Y'),('25D SLM Parameters', 'Beam Diameter'),('Zernike SLM Parameters','Piston'),('Zernike SLM Parameters','Y-tilt'),
                            ('Zernike SLM Parameters','X-tilt'),('Zernike SLM Parameters','Oblique Astigmatism'),('Zernike SLM Parameters','Defocus'),('Zernike SLM Parameters','Vertical Astigmatism'),
                            ('Zernike SLM Parameters','Vertical Trefoil'),('Zernike SLM Parameters','Vertical Coma'),('Zernike SLM Parameters','Horizontal Coma'),('Zernike SLM Parameters','Horizontal Trefoil')]
        

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


    def getWantedAttrs(self):
        """ Returns a JSON representation of this instance. """
        attrs = {}
        for key, value in self.shared_attributes.items():
            if key in self.wantedAttributes:
                parent = attrs
                for i in range(len(key) - 1):
                    if key[i] not in parent:
                        parent[key[i]] = {}
                    parent = parent[key[i]]

                parent[key[-1]] = value
            # jsonOutput = json.dumps(attrs)
            jsonOutputPretty = json.dumps(attrs, indent=4)

        return jsonOutputPretty

    def getAllAttrs(self):
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
        jsonOutput = self.getWantedAttrs()

        
        # savePath = os.path.join(self.exptFolderPath,'Snapshot')
        with open("JSONTest.json", "w", encoding='utf-8') as outfile:
            outfile.write(jsonOutput)

    # def saveJSON(self, jsonOutput):
    #     with open("JSONTest.json", "w", encoding='utf-8') as outfile:
    #         outfile.write(jsonOutput)
    #     self._logger.warning("Attributes saved.")


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