from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger

class InfoGatheringControllerTest1(ImConWidgetController):
    """ Not linked to widgets. Meant to pool experiment data
    and save it in a .xml file in a folder where data is saved. """
    
    
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        
        self._commChannel.sharedAttrs.sigAttributeSet.connect(self.updateExperimentParameters)
    
    def updateExperimentParameters(self):
        print("testing in InfoGatheringController")
        # self._logger.debug(f"InfoGatheringController: {self._master}")

