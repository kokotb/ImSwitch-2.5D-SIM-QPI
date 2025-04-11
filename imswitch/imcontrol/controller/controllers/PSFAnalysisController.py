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



class PSFAnalysisController(ImConWidgetController):
    """Linked to InfoGatheringWidget. Needs to be connected to widget to get initialized and connected to signals."""
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        # self._commChannel.sigStart25D.emit()
        self._widget.loadingPopupRecord.recordImages.clicked.connect(self.startRecImagesFunc)
        self._commChannel.sigSIMStopped.connect(self.stopRecImagesFunc)

    def startRecImagesFunc(self):
        self._widget.loadingPopupRecord.recordImages.setEnabled(False)
        self._commChannel.sigStart25D.emit()
        
    def stopRecImagesFunc(self):
        self._widget.loadingPopupRecord.recordImages.setEnabled(True)
        self.image_stack = self._commChannel.getPSFStack()

        self._widget.loadingPopupRecord.imgZStack.setImage(self.image_stack[0][0], levels=(0,4095))



    # def updateSharedAttributes(self):
    #     # print('test')
    #     self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
    #     # self._logger.warning("Shared attributes updated.")
        
    # # def saveAttributesToFile(self):
    # #     # Filter out only the important attributes?
        
    # #     # Save attributes
    # #     dir_harcoded = 'C:/Users/SIM_admin/Documents/ImSwitchConfig'
    # #     file_name_hardcoded = "exp_metadata"
    # #     # with open(os.path.join(dir_harcoded, file_name_hardcoded), 'w') as setupFile:
    # #     #     setupFile.write(self.shared_attributes.to_json(indent=4))
        
    # #     self._logger.warning("Attributes saved.")


    # def loadJSONFromFile(self):
    #     jsonObject = self._widget.loadingPopup.loadJSON()
    #     self._commChannel.sigLoadSettings.emit(jsonObject)
    #     self.moduleList = self.modulesToLoad()
    #     self._commChannel.sigModuleSettings.emit(self.moduleList)
        

    # def modulesToLoad(self):
    #     elementList = self._widget.loadingPopup.elementList
    #     moduleList = dict()

    #     for i in range(len(elementList)):
    #         moduleList[elementList[i]._name] = elementList[i].checkState()

    #     return moduleList


            


    # def getWantedAttrs(self):
    #     """ Returns a JSON representation of this instance. """
    #     attrs = {}
    #     for key, value in self.shared_attributes.items():
    #         if key in self.wantedAttributes:
    #             parent = attrs
    #             for i in range(len(key) - 1):
    #                 if key[i] not in parent:
    #                     parent[key[i]] = {}
    #                 parent = parent[key[i]]

    #             parent[key[-1]] = value
    #         # jsonOutput = json.dumps(attrs)
    #         jsonOutputPretty = json.dumps(attrs, indent=4)

    #     return jsonOutputPretty

    # def getAllAttrs(self):
    #     """ Returns a JSON representation of this instance. """
    #     attrs = {}
    #     for key, value in self.shared_attributes.items():
    #         parent = attrs
    #         for i in range(len(key) - 1):
    #             if key[i] not in parent:
    #                 parent[key[i]] = {}
    #             parent = parent[key[i]]

    #         parent[key[-1]] = value
    #     # jsonOutput = json.dumps(attrs)
    #     jsonOutputPretty = json.dumps(attrs, indent=4)

    #     return jsonOutputPretty
    
    # def getAndSaveJSON(self):
    #     jsonOutput = self.getWantedAttrs()

        
    #     # savePath = os.path.join(self.exptFolderPath,'Snapshot')
    #     with open("JSONTest.json", "w", encoding='utf-8') as outfile:
    #         outfile.write(jsonOutput)


    # def getHDF5Attributes(self):
    #     """ Returns a dictionary of HDF5 attributes representing this object.
    #     """
    #     attrs = {}
    #     for key, value in self.shared_attributes.items():
    #         attrs[':'.join(key)] = value

    #     return attrs
    
    # # def saveHDF5Attributes(self):
    # #     """ Saves a dictionary of HDF5 attributes representing this object.
    # #     """
    # #     attrs = {}
    # #     for key, value in self.shared_attributes.items():
    # #         attrs[':'.join(key)] = value

    # #     return attrs