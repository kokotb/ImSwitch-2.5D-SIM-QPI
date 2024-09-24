from qtpy import QtCore, QtWidgets
from PyQt5.QtGui import QWheelEvent , QDoubleValidator


from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class PositionerWidget(Widget):
    """ Widget in control of the piezo movement. """

    sigStepUpClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigStepDownClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigStepUpCoarseClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigStepDownCoarseClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigsetAbsPosClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigsetPositionerSpeedClicked = QtCore.Signal(str, str)  # (positionerName, axis)
    sigWheelEvent = QtCore.Signal(float)  # (positionerName, axis)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pars = {}
        self.posLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.posLayout)

    def addPositionerZ(self, positionerName, axes, speed):

        axis = axes[0]
        initialValueFine = 0.2
        initialValueCoarse = 5
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        label = f'{positionerName} -- {axis}' if positionerName != axis else positionerName


        self.wholeZLayout = QtWidgets.QHBoxLayout()
        self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
        self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.wholeZLayout.addWidget(self.pars['Label' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['Position' + parNameSuffix])


        self.gridZCoarseFine = QtWidgets.QGridLayout()
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('+')
        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('-')
        self.pars['UpButtonCoarse' + parNameSuffix] = guitools.BetterPushButton('+')
        self.pars['DownButtonCoarse' + parNameSuffix] = guitools.BetterPushButton('-')
        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(str(initialValueFine))
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')
        self.pars['StepEditCoarse' + parNameSuffix] = QtWidgets.QLineEdit(str(initialValueCoarse))
        self.pars['StepUnitCoarse' + parNameSuffix] = QtWidgets.QLabel(' µm')
        self.gridZCoarseFine.addWidget(self.pars['UpButton' + parNameSuffix], 0, 0)
        self.gridZCoarseFine.addWidget(self.pars['DownButton' + parNameSuffix], 0, 1)
        self.gridZCoarseFine.addWidget(self.pars['UpButtonCoarse' + parNameSuffix], 1, 0)
        self.gridZCoarseFine.addWidget(self.pars['DownButtonCoarse' + parNameSuffix],1, 1)
        self.gridZCoarseFine.addWidget(QtWidgets.QLabel('Fine'), 0, 2)
        self.gridZCoarseFine.addWidget(QtWidgets.QLabel('Coarse'), 1, 2)
        self.gridZCoarseFine.addWidget(self.pars['StepEdit' + parNameSuffix], 0, 3)
        self.gridZCoarseFine.addWidget(self.pars['StepUnit' + parNameSuffix], 0, 4)
        self.gridZCoarseFine.addWidget(self.pars['StepEditCoarse' + parNameSuffix], 1, 3)
        self.gridZCoarseFine.addWidget(self.pars['StepUnitCoarse' + parNameSuffix], 1, 4)
        self.wholeZLayout.addLayout(self.gridZCoarseFine)


        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
        self.pars['AbsPosEdit' + parNameSuffix].returnPressed.connect(self.pars['ButtonAbsPosEnter' + parNameSuffix].click)
        self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')
        self.wholeZLayout.addWidget(self.pars['AbsPos' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['AbsPosEdit' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix])

        self.posLayout.addLayout(self.wholeZLayout)


        # Connect signals
        self.pars['UpButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepUpClicked.emit(positionerName, axis)
        )
        self.pars['DownButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepDownClicked.emit(positionerName, axis)
        )
        self.pars['ButtonAbsPosEnter'+ parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigsetAbsPosClicked.emit(positionerName, axis)
        )
        self.pars['UpButtonCoarse' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepUpCoarseClicked.emit(positionerName, axis)
        )
        self.pars['DownButtonCoarse' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepDownCoarseClicked.emit(positionerName, axis)
        )



    def addPositionerXY(self, positionerName, axes, speed):
        for axis in axes:
            if axis == 'X':
                self.addPositionerX(positionerName, axis, speed)
            if axis == 'Y':
                self.addPositionerY(positionerName, axis, speed)


    def addPositionerX(self, positionerName, axis, speed):
        axisInitialValues = {"X": "10"}
        self.wholeXLayout = QtWidgets.QHBoxLayout()
        initialStepValue = axisInitialValues[axis]

        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        label = f'{axis}' if positionerName != axis else positionerName

        self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
        self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('→')
        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('←')
        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialStepValue)
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
        self.pars['AbsPosEdit' + parNameSuffix].returnPressed.connect(self.pars['ButtonAbsPosEnter' + parNameSuffix].click)
        self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel('µm')


        self.wholeXLayout.addWidget(self.pars['Label' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['Position' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['DownButton' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['UpButton' + parNameSuffix])
        self.wholeXLayout.addWidget(QtWidgets.QLabel('Step'))
        self.wholeXLayout.addWidget(self.pars['StepEdit' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['StepUnit' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['AbsPos' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['AbsPosEdit' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix])
        self.wholeXLayout.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix])

        self.posLayout.addLayout(self.wholeXLayout)



        # Connect signals
        self.pars['UpButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepUpClicked.emit(positionerName, axis)
        )
        self.pars['DownButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepDownClicked.emit(positionerName, axis)
        )
        self.pars['ButtonAbsPosEnter'+ parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigsetAbsPosClicked.emit(positionerName, axis)
        )


    def addPositionerY(self, positionerName, axis, speed):
        axisInitialValues = {"Y": "10"}

        self.wholeYLayout = QtWidgets.QHBoxLayout()

        initialStepValue = axisInitialValues[axis]

        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        label = f'{axis}' if positionerName != axis else positionerName

        self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
        self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('↑')
        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('↓')
        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialStepValue)
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')

        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
        # validator = QDoubleValidator()
        # validator.setRange(-10000.0, 9999.0, 1)
        # self.pars['AbsPosEdit' + parNameSuffix].setMaxLength(8)
        # self.pars['AbsPosEdit' + parNameSuffix].setValidator(validator)
        self.pars['AbsPosEdit' + parNameSuffix].returnPressed.connect(self.pars['ButtonAbsPosEnter' + parNameSuffix].click)

        self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel('µm')


        self.wholeYLayout.addWidget(self.pars['Label' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['Position' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['DownButton' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['UpButton' + parNameSuffix])
        self.wholeYLayout.addWidget(QtWidgets.QLabel('Step'))
        self.wholeYLayout.addWidget(self.pars['StepEdit' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['StepUnit' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['AbsPos' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['AbsPosEdit' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix])
        self.wholeYLayout.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix])



        self.posLayout.addLayout(self.wholeYLayout)

        # Connect signals
        self.pars['UpButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepUpClicked.emit(positionerName, axis)
        )
        self.pars['DownButton' + parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigStepDownClicked.emit(positionerName, axis)
        )
        self.pars['ButtonAbsPosEnter'+ parNameSuffix].clicked.connect(
            lambda *args, axis=axis: self.sigsetAbsPosClicked.emit(positionerName, axis)
        )


    # def addPositioner(self, positionerName, axes, speed):
    #     axisInitialValues = {  "X": "10",  "Y": "10",  "Z": "0.2"}
    #     for i in range(len(axes)):
    #         axis = axes[i]
    #         initialValue = axisInitialValues[axis]

    #         parNameSuffix = self._getParNameSuffix(positionerName, axis)
    #         label = f'{positionerName} -- {axis}' if positionerName != axis else positionerName

    #         self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
    #         self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
    #         self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
    #         self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
    #         self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('+')
    #         self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('-')

    #         self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialValue)
    #         # self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLineEdit()
    #         self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')

    #         self.posLayout.addWidget(self.pars['Label' + parNameSuffix], self.numPositioners, 0)
    #         self.posLayout.addWidget(self.pars['Position' + parNameSuffix], self.numPositioners, 1)
    #         self.posLayout.addWidget(self.pars['UpButton' + parNameSuffix], self.numPositioners, 3)
    #         self.posLayout.addWidget(self.pars['DownButton' + parNameSuffix], self.numPositioners, 4)
    #         self.posLayout.addWidget(QtWidgets.QLabel('Step'), self.numPositioners, 5)
    #         self.posLayout.addWidget(self.pars['StepEdit' + parNameSuffix], self.numPositioners, 6)
    #         self.posLayout.addWidget(self.pars['StepUnit' + parNameSuffix], self.numPositioners, 7)

    #         # Connect signals
    #         self.pars['UpButton' + parNameSuffix].clicked.connect(
    #             lambda *args, axis=axis: self.sigStepUpClicked.emit(positionerName, axis)
    #         )
    #         self.pars['DownButton' + parNameSuffix].clicked.connect(
    #             lambda *args, axis=axis: self.sigStepDownClicked.emit(positionerName, axis)
    #         )
            
    #         self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Abs. Pos</strong>')
    #         self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
    #         self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
    #         self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0')
    #         self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')
    #         self.posLayout.addWidget(self.pars['AbsPosEdit' + parNameSuffix], self.numPositioners, 9)
    #         self.posLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix], self.numPositioners, 10)
    #         self.posLayout.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix], self.numPositioners, 11)
    #         self.posLayout.addWidget(self.pars['AbsPos' + parNameSuffix], self.numPositioners, 8)


    #         self.pars['ButtonAbsPosEnter'+ parNameSuffix].clicked.connect(
    #             lambda *args, axis=axis: self.sigsetAbsPosClicked.emit(positionerName, axis)
    #         )

    #         self.numPositioners += 1

    def wheelEvent(self, event: QWheelEvent):
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                self.focusDelta = event.angleDelta().y() / 12
                self.sigWheelEvent.emit(self.focusDelta)
            elif modifiers == QtCore.Qt.ControlModifier:
                self.focusDelta = event.angleDelta().y() / 600
                self.sigWheelEvent.emit(self.focusDelta)

    def getStepSize(self, positionerName, axis):
        """ Returns the step size of the specified positioner axis in
        micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        return float(self.pars['StepEdit' + parNameSuffix].text())

    def getStepSizeCoarse(self, positionerName, axis):
        """ Returns the step size of the specified positioner axis in
        micrometers. """
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        return float(self.pars['StepEditCoarse' + parNameSuffix].text())

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
        self.pars['Position' + parNameSuffix].setText(f'<strong>{position:.2f} µm</strong>') #Sets value on left side of positioner widget
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
