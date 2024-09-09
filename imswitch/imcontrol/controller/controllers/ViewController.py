from imswitch.imcommon.model import APIExport
from ..basecontrollers import ImConWidgetController


class ViewController(ImConWidgetController):
    """ Linked to ViewWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._acqHandle = None

        self._widget.setViewToolsEnabled(False)

        # Connect ViewWidget signals
        self._widget.sigGridToggled.connect(self.gridToggle)
        self._widget.sigCrosshairToggled.connect(self.crosshairToggle)
        self._widget.sigLiveviewToggled.connect(self.liveview)
        # self._widget.sigAcquireSetToggled.connect(self.acquireSet)
        # self._widget.sigTriggerModeToggled.connect(self.setLiveTriggerModeState)
        self._commChannel.sigSIMAcqToggled.connect(self.simStarted)

    def simStarted(self, enabled):
        if enabled:
            # self.liveview(False)
            self._widget.setLiveViewActive(not enabled)
            self._widget.setLiveViewEnabled(not enabled)
        if not enabled:
            self._widget.setLiveViewEnabled(not enabled)

    def liveview(self, enabled):
        """ Start liveview and activate detector acquisition. """
        self._commChannel.sigLiveviewToggled.emit(enabled)

        if enabled and self._acqHandle is None:
            #CTNOTE TRIGGER ACTIVATION HERE MAYBE
            self._acqHandle = self._master.detectorsManager.startAcquisition(liveView=True)
            # for heading in self._master.detectorsManager._subManagers:
            #     trigValue = self._master.detectorsManager._subManagers[{heading}]._DetectorManager__parameters['TriggerMode'].value
            #     if trigValue == 'On':
            # self._master.arduinoManager.startContSequence(0)
            self._widget.setViewToolsEnabled(True)
        elif not enabled and self._acqHandle is not None:
            self._master.detectorsManager.stopAcquisition(self._acqHandle, liveView=True)
            self._master.arduinoManager.stopSequence()
            self._acqHandle = None
        # print("liveview")
            

    def gridToggle(self, enabled):
        """ Connect with grid toggle from Image Widget through communication channel. """
        self._commChannel.sigGridToggled.emit(enabled)

    def crosshairToggle(self, enabled):
        """ Connect with crosshair toggle from Image Widget through communication channel. """
        self._commChannel.sigCrosshairToggled.emit(enabled)

    def closeEvent(self):
        if self._acqHandle is not None:
            self._master.detectorsManager.stopAcquisition(self._acqHandle, liveView=True)

    def get_image(self, detectorName):
        if detectorName is None:
            print("if detector name is none")
            return self._master.detectorsManager.execOnCurrent(lambda c: c.getLatestFrame())
            
        else:
            print("else if detector name")
            return self._master.detectorsManager[detectorName].getLatestFrame()
    
    # def setLiveTriggerModeState(self):
    #     """ Sets trigger mode down to a detector level"""
    #     # Check checkbox
    #     trigger_mode = self._widget.checkbox_trigerred.isChecked()
    #     detector = self._master.detectorsManager.getCurrentDetector()

    #     # Setting trigger mode to a detector
    #     detector.live_trigger_mode = trigger_mode


    @APIExport(runOnUIThread=True)
    def setLiveViewActive(self, active: bool) -> None:
        """ Sets whether the LiveView is active and updating. """
        self._widget.setLiveViewActive(active)

    @APIExport(runOnUIThread=True)
    def setLiveViewGridVisible(self, visible: bool) -> None:
        """ Sets whether the LiveView grid is visible. """
        self._widget.setLiveViewGridVisible(visible)

    @APIExport(runOnUIThread=True)
    def setLiveViewCrosshairVisible(self, visible: bool) -> None:
        """ Sets whether the LiveView crosshair is visible. """
        self._widget.setLiveViewCrosshairVisible(visible)

    # @APIExport(runOnUIThread=True)
    # def setLiveViewAcquireSet(self, visible: bool) -> None:
    #     """ Sets whether the LiveView crosshair is visible. """
    #     self._widget.setLiveViewAcquireSet(visible)


# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
