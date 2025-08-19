import json
import numpy as np
from datetime import datetime
import tifffile as tif
import numpy as np
from decimal import Decimal
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcontrol.model import configfiletools
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.InfoGatheringWidget import MyInputDialog
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
from imswitch.imcommon.model.dirtools import DataFileDirs
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
import json
import os
# from PyQt5.QtWidgets import QDialog



class InfoGatheringController(ImConWidgetController):
    """Linked to InfoGatheringWidget. Needs to be connected to widget to get initialized and connected to signals."""
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        # inputDialog = MyInputDialog(QDialog)

        # Connect signals to communications channel
        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.updateSharedAttributes)
        self._commChannel.sigSaveSettingsFirst.connect(self.saveFileDialog)
        self._commChannel.sigSIMAcqToggled.connect(self._widget.toggleLoadButton)
        # self._commChannel.sigSIMAcqToggled.connect(self.saveAttributesToFile)
        
        
        # Load experimental parameters into local object attribute
        self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
        self.wantedAttributes = [('Laser', '488AOTF', 'Value'),
                                ('Laser', '488AOTF', 'Enabled'),
                                ('Laser', '561AOTF', 'Value'),
                                ('Laser', '561AOTF', 'Enabled'),
                                ('Laser', '640AOTF', 'Value'),
                                ('Laser', '640AOTF', 'Enabled'),
                                ('Positioner', 'Z', 'Z', 'Position'),
                                ('Positioner', 'XY', 'X', 'Position'),
                                ('Positioner', 'XY', 'Y', 'Position'),
                                ('Tiling Settings', 'Steps - X'),
                                ('Tiling Settings', 'Steps - Y'),
                                ('Tiling Settings', 'Overlap'),
                                ('Tiling Settings', 'Tiling Preview'),
                                ('Tiling Settings', 'Tiling Checkbox'),
                                ('Timing Settings', 'Period Checkbox'),
                                ('Timing Settings', 'Timing Unit'),
                                ('Timing Settings', 'Timing Period'),
                                ('Timing Settings', 'Duration'),
                                ('Timing Settings', 'Duration Unit'),
                                ('Timing Settings', 'Repetitions'),
                                ('Timing Settings', 'Rep Checkbox'),
                                ('Timing Settings', 'Duration Checkbox'),
                                ('Detector', '488 Fluor', 'Model'), 
                                ('Detector', '488 Fluor', 'ROI'),
                                ('Detector', '488 Fluor', 'Param', 'ExposureTime'),
                                ('Detector', '488 Fluor', 'Param', 'Gain'),
                                ('Detector', '488 Fluor', 'Param', 'Gamma'),
                                ('Detector', '488 Fluor', 'Param', 'TriggerMode'),
                                ('Detector', '561 Fluor', 'Model'),
                                ('Detector', '561 Fluor', 'ROI'),
                                ('Detector', '561 Fluor', 'Param', 'ExposureTime'),
                                ('Detector', '561 Fluor', 'Param', 'Gain'),
                                ('Detector', '561 Fluor', 'Param', 'Gamma'),
                                ('Detector', '561 Fluor', 'Param', 'TriggerMode'),
                                ('Detector', '640 Fluor', 'Model'),
                                ('Detector', '640 Fluor', 'ROI'),
                                ('Detector', '640 Fluor', 'Param', 'ExposureTime'),
                                ('Detector', '640 Fluor', 'Param', 'Gain'),
                                ('Detector', '640 Fluor', 'Param', 'Gamma'),
                                ('Detector', '640 Fluor', 'Param', 'TriggerMode'),
                                ('SIM Parameters', 'ReconWL1'),
                                ('SIM Parameters', 'ReconWL2'),
                                ('SIM Parameters', 'ReconWL3'),
                                ('SIM Parameters', 'NA'),
                                ('SIM Parameters', 'Pixelsize'),
                                ('SIM Parameters', 'Alpha'),
                                ('SIM Parameters', 'Beta'),
                                ('SIM Parameters', 'w'),
                                ('SIM Parameters', 'eta'),
                                ('SIM Parameters', 'n'),
                                ('SIM Parameters', 'Magnification'),
                                ('SIM Parameters',"SLM Running Order"),
                                ('User Dir Info', 'Working Directory'),
                                ('User Dir Info', 'Current Path'),
                                ('User Dir Info', 'User Name'),
                                ('User Dir Info', 'Experiment Name'),
                                ('Z-Stack Settings', 'Step Size'),
                                ('Z-Stack Settings', 'Total Z /um'),
                                ('Z-Stack Settings', 'Z-Stack Checkbox'),
                                ('Z-Stack Settings','Scan Direction'),
                                ('Z-Stack Settings','Z-Stack Center?'),
                                ('Z-Stack Settings','Scan Start Offset'),
                                ('ROI List', 'List'),
                                ('ROI List', 'Checkbox'),
                                ('25D SLM Parameters', 'Gamma'),
                                ('25D SLM Parameters', 'Psi'),
                                ('25D SLM Parameters', 'Left Center-X'),
                                ('25D SLM Parameters', 'Left Center-Y'),
                                ('25D SLM Parameters', 'Right Center-X'),
                                ('25D SLM Parameters', 'Right Center-Y'),
                                ('25D SLM Parameters', 'Beam Diameter'),
                                ('Zernike SLM Parameters','Left', 'Piston'),
                                ('Zernike SLM Parameters','Left', 'Y-tilt'),
                                ('Zernike SLM Parameters','Left', 'X-tilt'),
                                ('Zernike SLM Parameters','Left', 'Oblique Astigmatism'),
                                ('Zernike SLM Parameters','Left', 'Defocus'),
                                ('Zernike SLM Parameters','Left', 'Vertical Astigmatism'),
                                ('Zernike SLM Parameters','Left', 'Vertical Trefoil'),
                                ('Zernike SLM Parameters','Left', 'Vertical Coma'),
                                ('Zernike SLM Parameters','Left', 'Horizontal Coma'),
                                ('Zernike SLM Parameters','Left', 'Horizontal Trefoil'),
                                ('Zernike SLM Parameters','Left', 'Spherical'),
                                ('Zernike SLM Parameters','Right', 'Piston'),
                                ('Zernike SLM Parameters','Right', 'Y-tilt'),
                                ('Zernike SLM Parameters','Right', 'X-tilt'),
                                ('Zernike SLM Parameters','Right', 'Oblique Astigmatism'),
                                ('Zernike SLM Parameters','Right', 'Defocus'),
                                ('Zernike SLM Parameters','Right', 'Vertical Astigmatism'),
                                ('Zernike SLM Parameters','Right', 'Vertical Trefoil'),
                                ('Zernike SLM Parameters','Right', 'Vertical Coma'),
                                ('Zernike SLM Parameters','Right', 'Horizontal Coma'),
                                ('Zernike SLM Parameters','Right', 'Horizontal Trefoil'),
                                ('Zernike SLM Parameters','Right', 'Spherical'),
                                ('Zernike SLM Parameters','Both', 'Enabled'),
                                ('Autofocus Settings','Autofocus Checkbox'),
                                ('Autofocus Settings','Autofocus Channel')]
        
        
        self._widget.loadingPopup.okButton.clicked.connect(self.loadJSONFromFile)
        self._widget.saveSettings.clicked.connect(self.saveFileDialog)
        self._widget.loadSettings.clicked.connect(self.openLoadWindow)
        ####################################
        # self._widget.loadingPopup.lasersCheckbox.loadSignal = self._commChannel.sigLoadLasersSettings

    def openLoadWindow(self):
        self._widget.loadingPopup.filePath.setText(self._commChannel.sharedAttrs._data[('User Dir Info', 'Working Directory')])
        self._widget.loadingPopup.exec_()

         


    def saveFileDialog(self):
        currentRoot = self._commChannel.sharedAttrs._data[('User Dir Info', 'Working Directory')]
        fileIndex = 1
        if not self._commChannel.simActive:
            # name = self._commChannel.currentTimeString
            filePath = self._widget.saveFileDialog(currentRoot)
            if filePath == None:
                return
            filePathRoot = os.path.split(filePath)[0]
        else:
            filePathRoot = self._commChannel.activeDir
            name = self._commChannel.currentTimeString
            filePath = os.path.join(filePathRoot, name + '.json')
            if not os.path.exists(filePathRoot):
                os.makedirs(filePathRoot)
            if os.path.exists(filePath):
                fileIndex += 1
                filePath = os.path.join(filePathRoot, name + '_' + str(fileIndex) + '.json')
        
        jsonOutput = self.getWantedAttrs()
        


        with open(filePath, "w", encoding='utf-8') as outfile:
            outfile.write(jsonOutput)
        self.lastSavePath = filePath
        self.lastSaveName = os.path.split(filePath)[-1]
        print('Settings JSON saved at: ' + self.lastSavePath)


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


    def loadJSONFromFile(self):
        jsonObject = self._widget.loadingPopup.loadJSON()
        self._commChannel.sigLoadSettings.emit(jsonObject)
        self.moduleList = self.modulesToLoad()
        self._commChannel.sigModuleSettings.emit(self.moduleList)
        

    def modulesToLoad(self):
        elementList = self._widget.loadingPopup.elementList
        moduleList = dict()

        for i in range(len(elementList)):
            moduleList[elementList[i]._name] = elementList[i].checkState()

        return moduleList


            


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