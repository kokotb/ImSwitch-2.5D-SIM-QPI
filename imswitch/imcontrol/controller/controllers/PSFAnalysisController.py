import numpy as np
from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController

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
        try:
            image_stack = self._commChannel.getPSFStack()
            # self.image_stack = self._widget.loadingPopupRecord.image_stack DUMB THINGS HERE TOO !!!
            self.channelStack = np.array(image_stack[2])
            self._widget.loadingPopupRecord.image_stack = self.channelStack
            self._widget.loadingPopupRecord.imgZStack.setImage(self.channelStack[0], levels=(0,4095))
            # self._widget.loadingPopupRecord.updatePSFXYimage()
            # self._widget.loadingPopupRecord.updatePSFXZimage()
            # self._widget.loadingPopupRecord.updatePSFYZimage()
            self._widget.loadingPopupRecord.showSelectedPSF()
        except AttributeError:
            pass




    # def updateSharedAttributes(self):
    #     # print('test')
    #     self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
    #     # self._logger.warning("Shared attributes updated.")