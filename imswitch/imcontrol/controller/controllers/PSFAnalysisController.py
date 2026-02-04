import numpy as np
from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.controller.basecontrollers import ImConWidgetController
import time
from imswitch.imcommon.framework import Signal, SignalInterface


class PSFAnalysisController(ImConWidgetController):
    """Linked to InfoGatheringWidget. Needs to be connected to widget to get initialized and connected to signals."""
    
    sigPSFstackInDatasetDone = Signal()

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._widget.loadingPopupRecord.recordImages.clicked.connect(self.startRecImagesFunc)
        self._widget.loadingPopupRecord.recordPSFdataset.clicked.connect(self.startRecordDatasetFunc)
        self.recordingPSF = False
        self.recordingPSFDataset = False
        self.sigPSFstackInDatasetDone.connect(self.savePSFandStartNext)
        self._commChannel.sigSIMStopped.connect(self.stopRecImagesFunc)

    def startRecordDatasetFunc(self):
        self.recordingPSFDataset = True
        self.gammas = [0., 1., 2., 3., 4., 4.5, 5., 5.5, 6.5, 7., 7.5, 8., 9., 10., 11., 12.]
        self.psis = [0., 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 1.]
        self.gammaIndex = 0
        self.psiIndex = 0
        self.RecordPSFforDataset()
                    

    def RecordPSFforDataset(self):
        self._commChannel.sigSet25dParVals.emit(self.gammas[self.gammaIndex], self.psis[self.psiIndex])
        time.sleep(0.3)
        self.startRecImagesFunc()


    def savePSFandStartNext(self):
        gamma = self.gammas[self.gammaIndex]
        psi = self.psis[self.psiIndex]
        gammastr = f"{int(np.round(gamma * 10, decimals=0)):02d}"
        psistr = f"{int(np.round(psi * 10, decimals=0)):02d}"
        foldername = "experiment" + "g" + gammastr + "p" + psistr
        self._widget.loadingPopupRecord.savePSFfuncDataset(foldername)
        print(foldername + " saved")

        if self.psiIndex >= (len(self.psis) - 1):
            self.psiIndex = 0
            self.gammaIndex += 1

            if self.gammaIndex >= len(self.gammas):
                self.gammaIndex = 0
                print("Dataset recording finished")

            else:
                self.RecordPSFforDataset()

        else:
            self.psiIndex += 1
            self.RecordPSFforDataset()



    def startRecImagesFunc(self):
        self.originZ = self._master.positionersManager._subManagers['Z']._position['Z']

        # self.originZ = self._master.positionersManager._subManagers['Z']._position['Z']

        if not self._commChannel.simActive:
            self._widget.loadingPopupRecord.recordImages.setEnabled(False)
            self._commChannel.sigSetForPSF.emit(True)
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
            #self._master.positionersManager._subManagers['Z'].setPosition(self.originZ, 'Z')
            # zValueChecked = self._master.positionersManager._subManagers['Z'].get_abs()
            # while zValueChecked != self.originZ:
            #     zValueChecked = self._master.positionersManager._subManagers['Z'].get_abs()
            # self._commChannel.sigUpdateZPosition.emit('Z','Z')
            self.recordingPSF = False
            
            

            try:
                image_stack = self._commChannel.getPSFStack()


                # 2 = red,  1 = green,  0 = blue
                if self._widget.loadingPopupRecord.checkboxRecordRed.isChecked():
                    self.channelStack = np.array(image_stack["Red"])
                elif self._widget.loadingPopupRecord.checkboxRecordGreen.isChecked():
                    self.channelStack = np.array(image_stack["Green"])
                elif self._widget.loadingPopupRecord.checkboxRecordBlue.isChecked():
                    self.channelStack = np.array(image_stack["Blue"])

                self._widget.loadingPopupRecord.image_stack = np.rot90(self.channelStack, k=3, axes=(1, 2))
                self._widget.loadingPopupRecord.imgZStack.setImage(self.channelStack[0], levels=(0,4095))
                # self._widget.loadingPopupRecord.updatePSFXYimage()
                # self._widget.loadingPopupRecord.updatePSFXZimage()
                # self._widget.loadingPopupRecord.updatePSFYZimage()
                self._widget.loadingPopupRecord.showSelectedPSF()

                if self.recordingPSFDataset:
                    self.sigPSFstackInDatasetDone.emit()


            except AttributeError:
                print('Stop recording fuction for PSF failed to complete.')


            

            




    # def updateSharedAttributes(self):
    #     # print('test')
    #     self.shared_attributes = self._master._MasterController__commChannel._CommunicationChannel__sharedAttrs._data
    #     # self._logger.warning("Shared attributes updated.")