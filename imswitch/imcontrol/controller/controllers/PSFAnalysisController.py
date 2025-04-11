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
        image_stack = self._commChannel.getPSFStack()

        # self.image_stack = self._widget.loadingPopupRecord.image_stack DUMB THINGS HERE TOO !!!
        self.channelStack = np.array(image_stack[0])
        self._widget.loadingPopupRecord.image_stack = self.channelStack
        self._widget.loadingPopupRecord.imgZStack.setImage(self.channelStack[0], levels=(0,4095))



    # def updateSharedAttributes(self):
    #     # print('test')
    #     self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
    #     # self._logger.warning("Shared attributes updated.")

