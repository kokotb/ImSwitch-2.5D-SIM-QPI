from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger
class TimingController(ImConWidgetController):


    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self._widget.sigTimingInfoChanged.connect(self.valueChanged)
        # self._widget.sigTimingCheckChanged.connect(self.valueChanged)
        self.sharedAttrs = self._commChannel.sharedAttrs._data

        #Setup initial values after widget so all values sent to sharedAttrs
        self._widget.populateUnitsList()
        self._widget.timingPeriod_textedit.setText("0")
        self._widget.timingDuration_textedit.setText("0")
        self._widget.totalReps_textedit.setText("1")
        self._widget.sigTimingInfoChanged.emit('Timing Settings','Period Checkbox', str(0))
        self._widget.sigTimingInfoChanged.emit('Timing Settings','Rep Checkbox', str(0))
        self._widget.sigTimingInfoChanged.emit('Timing Settings','Duration Checkbox', str(0))
        self._commChannel.sigSIMAcqToggled.connect(self._widget.toggleCheckboxes) #Still on sigSIMAcqToggled
        self._commChannel.sigModuleSettings.connect(self.loadSettings)
        #
        self._commChannel.sigSetForPSF.connect(self.editForPSF)

    def editForPSF(self, start):
        if start:
            self.initReps = self._widget.totalReps_textedit.text()
            self.initEnabled = self._widget.checkbox_tilingReps.isChecked()
            self._widget.checkbox_tilingReps.setChecked(True)
            self._widget.totalReps_textedit.setText('1')
        if not start:
            self._widget.checkbox_tilingReps.setChecked(self.initEnabled)
            self._widget.totalReps_textedit.setText(self.initReps)


    def loadSettings(self, moduleDict):
        try:
            loadBool = moduleDict['timing']
        except KeyError:
            loadBool = 0
        if loadBool:
            params = self._commChannel.loadedSettings['Timing Settings']

            for i in range(len(self._widget.elementList)):
                if self._widget.elementList[i]._type == 'str':
                    self._widget.elementList[i].setText(params[self._widget.elementList[i]._name])

                elif self._widget.elementList[i]._type == 'int':
                    self._widget.elementList[i].setChecked(int(params[self._widget.elementList[i]._name]))

                if self._widget.elementList[i]._type == 'combostr':
                    self._widget.elementList[i].setCurrentText(params[self._widget.elementList[i]._name])


    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        # print(value)
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, parameterName)] = value
        finally:
            self.settingAttr = False

    


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
