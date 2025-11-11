import numpy as np
from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
import time


class PSFAnalysisController(ImConWidgetController):
    """Linked to InfoGatheringWidget. Needs to be connected to widget to get initialized and connected to signals."""
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._widget.loadingPopupRecord.recordImages.clicked.connect(self.startRecImagesFunc)
        self.recordingPSF = False
        self._commChannel.sigSIMStopped.connect(self.stopRecImagesFunc)

    def startRecImagesFunc(self):
        self.originZ = self._master.positionersManager._subManagers['Z']._position['Z']

        # self.originZ = self._master.positionersManager._subManagers['Z']._position['Z']

        if not self._commChannel.simActive:
            self._widget.loadingPopupRecord.recordImages.setEnabled(False)
            self._commChannel.sigSetForPSF.emit(True)
            # self._commChannel.sigCalcZStepArray.emit()
            self._commChannel.sigStart25D.emit()
            self.recordingPSF = True
        else:
            reply = self._widget.loadingPopupRecord.askYesNoQuestion()
            if reply == True:
                self._commChannel.stop25DNow = True
             
            else:
                self._logger.warning('Please stop acquisition before recording a PSF.')
            
        
    def stopRecImagesFunc(self):
        if (self.recordingPSF):
            
            self._commChannel.sigSetForPSF.emit(False)
            self._widget.loadingPopupRecord.recordImages.setEnabled(True)
            # self._master.positionersManager._subManagers['Z'].setPosition(self.originZ, 'Z')
            # zValueChecked = self._master.positionersManager._subManagers['Z'].get_abs()
            # while zValueChecked != self.originZ:
            #     zValueChecked = self._master.positionersManager._subManagers['Z'].get_abs()
            # self._commChannel.sigUpdateZPosition.emit('Z','Z')
            self.recordingPSF = False
            

            try:
                image_stack = self._commChannel.getPSFStack()


                # 2 = red,  1 = green,  0 = blue
                if self._widget.loadingPopupRecord.checkboxRecordRed.isChecked():
                    self.channelStack = np.array(image_stack[2])   
                elif self._widget.loadingPopupRecord.checkboxRecordGreen.isChecked():
                    self.channelStack = np.array(image_stack[1])
                elif self._widget.loadingPopupRecord.checkboxRecordBlue.isChecked():
                    self.channelStack = np.array(image_stack[0])

                self._widget.loadingPopupRecord.image_stack = self.channelStack
                self._widget.loadingPopupRecord.imgZStack.setImage(self.channelStack[0], levels=(0,4095))
                # self._widget.loadingPopupRecord.updatePSFXYimage()
                # self._widget.loadingPopupRecord.updatePSFXZimage()
                # self._widget.loadingPopupRecord.updatePSFYZimage()
                self._widget.loadingPopupRecord.showSelectedPSF()
            except AttributeError:
                print('Stop recording fuction for PSF failed to complete.')


            

            




    # def updateSharedAttributes(self):
    #     # print('test')
    #     self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
    #     # self._logger.warning("Shared attributes updated.")