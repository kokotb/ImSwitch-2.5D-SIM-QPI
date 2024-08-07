from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class PositionerWidget(Widget):
    """ Widget in control of the piezo movement. """

    sigStepUpClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigStepDownClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigsetAbsPosClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigsetPositionerSpeedClicked = QtCore.Signal(str, str)  # (positionerName, axis)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numPositioners = 0
        self.pars = {}
        self.grid = QtWidgets.QGridLayout()
        self.setLayout(self.grid)

    def addPositioner(self, positionerName, axes, speed):
        axisInitialValues = {  "X": "1",  "Y": "1",  "Z": "0.2"}
        for i in range(len(axes)):
            axis = axes[i]
            initialValue = axisInitialValues[axis]

            parNameSuffix = self._getParNameSuffix(positionerName, axis)
            label = f'{positionerName} -- {axis}' if positionerName != axis else positionerName

            self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
            self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
            self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('+')
            self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('-')

            self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialValue)
            # self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLineEdit()
            self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')

            self.grid.addWidget(self.pars['Label' + parNameSuffix], self.numPositioners, 0)
            self.grid.addWidget(self.pars['Position' + parNameSuffix], self.numPositioners, 1)
            self.grid.addWidget(self.pars['UpButton' + parNameSuffix], self.numPositioners, 3)
            self.grid.addWidget(self.pars['DownButton' + parNameSuffix], self.numPositioners, 4)
            self.grid.addWidget(QtWidgets.QLabel('Step'), self.numPositioners, 5)
            self.grid.addWidget(self.pars['StepEdit' + parNameSuffix], self.numPositioners, 6)
            self.grid.addWidget(self.pars['StepUnit' + parNameSuffix], self.numPositioners, 7)

            # Connect signals
            self.pars['UpButton' + parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigStepUpClicked.emit(positionerName, axis)
            )
            self.pars['DownButton' + parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigStepDownClicked.emit(positionerName, axis)
            )
            
   
            self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
            self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
            self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
            self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')
            self.grid.addWidget(self.pars['AbsPosEdit' + parNameSuffix], self.numPositioners, 9)
            self.grid.addWidget(self.pars['AbsPosUnit' + parNameSuffix], self.numPositioners, 10)
            self.grid.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix], self.numPositioners, 11)
            self.grid.addWidget(self.pars['AbsPos' + parNameSuffix], self.numPositioners, 8)


            self.pars['ButtonAbsPosEnter'+ parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigsetAbsPosClicked.emit(positionerName, axis)
            )

            self.pars['Speed' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Speed</strong>')
            self.pars['Speed' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
            self.pars['ButtonSpeedEnter' + parNameSuffix] = guitools.BetterPushButton('SetSpeed')
            self.pars['SpeedEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
            self.pars['SpeedUnit' + parNameSuffix] = QtWidgets.QLabel(' µm/s?')
            self.grid.addWidget(self.pars['SpeedEdit' + parNameSuffix], self.numPositioners, 13)
            self.grid.addWidget(self.pars['SpeedUnit' + parNameSuffix], self.numPositioners, 14)
            self.grid.addWidget(self.pars['ButtonSpeedEnter' + parNameSuffix], self.numPositioners, 15)
            self.grid.addWidget(self.pars['Speed' + parNameSuffix], self.numPositioners, 12)

            self.pars['ButtonSpeedEnter'+ parNameSuffix].clicked.connect(
                lambda *args, axis=axis: self.sigsetPositionerSpeedClicked.emit(positionerName, axis)
            )

            self.numPositioners += 1

    def getStepSize(self, positionerName, axis):
        """ Returns the step size of the specified positioner axis in
        micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        return float(self.pars['StepEdit' + parNameSuffix].text())

    def setStepSize(self, positionerName, axis, stepSize):
        """ Sets the step size of the specified positioner axis to the
        specified number of micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        self.pars['StepEdit' + parNameSuffix].setText(stepSize)

    def getAbsPos(self, positionerName, axis):
        """ Sets the absolute position of the specified positioner axis in
        micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        return float(self.pars['AbsPosEdit'+parNameSuffix].text())
    
    def updateAbsPos(self, positionerName, axis, position):
        """ Updates the absolute position widget of the specified positioner 
        axis in micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        self.pars['AbsPosEdit'+parNameSuffix].setText(str(position))

    def updateSpeedSize(self, positionerName, axis, speedSize):
        """ Sets the step size of the specified positioner axis to the
        specified speed. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        self.pars['SpeedEdit' + parNameSuffix].setText(str(speedSize))

    def getSpeedSize(self, positionerName, axis):
        """ Sets the step size of the specified positioner axis to the
        specified speed. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        return float(self.pars['SpeedEdit'+parNameSuffix].text())

    def updatePosition(self, positionerName, axis, position):

        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        self.pars['Position' + parNameSuffix].setText(f'<strong>{position:.2f} µm</strong>')
        # Updates entry window for absolute position
        self.updateAbsPos(positionerName, axis, position)


    def _getParNameSuffix(self, positionerName, axis):
        return f'{positionerName}--{axis}'


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
