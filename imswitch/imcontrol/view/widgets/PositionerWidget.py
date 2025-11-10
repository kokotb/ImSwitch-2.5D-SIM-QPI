from qtpy import QtCore, QtWidgets
from PyQt5.QtGui import QWheelEvent , QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QCheckBox, QMainWindow, QWidget, QLineEdit, QPushButton
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget


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
        self.elementList = []


    def addPositionerZ(self, positionerName, axes, speed):

        axis = axes[0]
        initialValueFine = 0.1
        initialValueCoarse = 5
        parNameSuffix = self._getParNameSuffix(positionerName, axis)
        label = f'{positionerName} -- {axis}' if positionerName != axis else positionerName
        zDriftLayout = QtWidgets.QVBoxLayout()
        self.wholeZLayout = QtWidgets.QHBoxLayout()

        self.pars['Label' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{label}</strong>')
        self.pars['Label' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.wholeZLayout.addWidget(self.pars['Label' + parNameSuffix])


        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0:.2f} µm</strong>')
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['Position' + parNameSuffix].setFixedWidth(100)
        zDriftLayout.addWidget(self.pars['Position' + parNameSuffix], alignment=QtCore.Qt.AlignHCenter)

        self.pars['Drift' + parNameSuffix] = QtWidgets.QLabel(f'({0:.2f} µm)')

        self.pars['Drift' + parNameSuffix].setFixedWidth(100)
        zDriftLayout.addWidget(self.pars['Drift' + parNameSuffix], alignment=QtCore.Qt.AlignHCenter)


        self.gridZCoarseFine = QtWidgets.QGridLayout()
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('+')

        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('-')
        self.pars['UpButtonCoarse' + parNameSuffix] = guitools.BetterPushButton('+')
        self.pars['DownButtonCoarse' + parNameSuffix] = guitools.BetterPushButton('-')
        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(str(initialValueFine))
        self.pars['StepEdit' + parNameSuffix].setFixedWidth(50)
        self.pars['StepEdit' + parNameSuffix].setToolTip('Hold Ctrl while using scroll wheel to focus in fine steps. Mouse must be anywhere in Positioner box')  
        self.validator = QDoubleValidator()
        self.pars['StepEdit' + parNameSuffix].setValidator(self.validator)
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.pars['StepEditCoarse' + parNameSuffix] = QtWidgets.QLineEdit(str(initialValueCoarse))
        self.pars['StepEditCoarse' + parNameSuffix].setFixedWidth(50)
        self.pars['StepEditCoarse' + parNameSuffix].setToolTip('Hold Shift while using scroll wheel to focus in coarse steps. Mouse must be anywhere in Positioner box')  
        self.validator = QIntValidator()
        self.pars['StepEditCoarse' + parNameSuffix].setValidator(self.validator)
        self.pars['StepUnitCoarse' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.gridZCoarseFine.addWidget(self.pars['DownButton' + parNameSuffix], 0, 0)
        self.gridZCoarseFine.addWidget(self.pars['UpButton' + parNameSuffix], 0, 1)
        self.gridZCoarseFine.addWidget(self.pars['DownButtonCoarse' + parNameSuffix],1, 0)
        self.gridZCoarseFine.addWidget(self.pars['UpButtonCoarse' + parNameSuffix], 1, 1)
        self.gridZCoarseFine.addWidget(QtWidgets.QLabel('Fine'), 0, 2)
        self.gridZCoarseFine.addWidget(QtWidgets.QLabel('Coarse'), 1, 2)
        self.gridZCoarseFine.addWidget(self.pars['StepEdit' + parNameSuffix], 0, 3)
        self.gridZCoarseFine.addWidget(self.pars['StepUnit' + parNameSuffix], 0, 4)
        self.gridZCoarseFine.addWidget(self.pars['StepEditCoarse' + parNameSuffix], 1, 3)
        self.gridZCoarseFine.addWidget(self.pars['StepUnitCoarse' + parNameSuffix], 1, 4)

        self.wholeZLayout.addLayout(zDriftLayout)
        self.wholeZLayout.addLayout(self.gridZCoarseFine)


        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Pos:</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0.0')
        self.pars['AbsPosEdit' + parNameSuffix]._name = 'Z--Z'
        self.pars['AbsPosEdit' + parNameSuffix]._type = 'str'
        self.pars['AbsPosEdit' + parNameSuffix].setMinimumWidth(100)
        self.validator = QDoubleValidator()
        self.validator.setDecimals(1)
        self.pars['AbsPosEdit' + parNameSuffix].setValidator(self.validator)
        self.pars['AbsPosEdit' + parNameSuffix].returnPressed.connect(self.pars['ButtonAbsPosEnter' + parNameSuffix].click)
        self.pars['AbsPosUnit' + parNameSuffix] = QtWidgets.QLabel(' µm')
        self.wholeZLayout.addWidget(self.pars['AbsPos' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['AbsPosEdit' + parNameSuffix])
        self.wholeZLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix])
        self.posLayout.addLayout(self.wholeZLayout)

        self.elementList.append(self.pars['AbsPosEdit' + parNameSuffix])


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
        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0.0:.1f} µm</strong>')
        self.pars['Position' + parNameSuffix].setFixedWidth(120)
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('→')
        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('←')

        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialStepValue)
        self.pars['StepEdit' + parNameSuffix].setMaximumWidth(50)
        self.validator = QIntValidator()
        self.pars['StepEdit' + parNameSuffix].setValidator(self.validator)
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Pos:</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')
        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0.0')
        self.pars['AbsPosEdit' + parNameSuffix]._name = 'XY--X'
        self.pars['AbsPosEdit' + parNameSuffix]._type = 'str'
        self.pars['AbsPosEdit' + parNameSuffix].setMinimumWidth(100)
        self.validator = QDoubleValidator()
        self.pars['AbsPosEdit' + parNameSuffix].setValidator(self.validator)
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
        # self.wholeXLayout.addWidget(self.pars['ButtonAbsPosEnter' + parNameSuffix])

        self.posLayout.addLayout(self.wholeXLayout)
        self.elementList.append(self.pars['AbsPosEdit' + parNameSuffix])



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
        self.pars['Position' + parNameSuffix] = QtWidgets.QLabel(f'<strong>{0.0:.1f} µm</strong>')
        self.pars['Position' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['Position' + parNameSuffix].setFixedWidth(120)
        self.pars['UpButton' + parNameSuffix] = guitools.BetterPushButton('↑')
        self.pars['DownButton' + parNameSuffix] = guitools.BetterPushButton('↓')

        self.pars['StepEdit' + parNameSuffix] = QtWidgets.QLineEdit(initialStepValue)
        self.validator = QIntValidator()
        self.pars['StepEdit' + parNameSuffix].setMaximumWidth(50)
        self.pars['StepEdit' + parNameSuffix].setValidator(self.validator)
        self.pars['StepUnit' + parNameSuffix] = QtWidgets.QLabel('µm')
        self.pars['AbsPos' + parNameSuffix] = QtWidgets.QLabel(f'<strong>Pos:</strong>')
        self.pars['AbsPos' + parNameSuffix].setTextFormat(QtCore.Qt.RichText)
        self.pars['ButtonAbsPosEnter' + parNameSuffix] = guitools.BetterPushButton('Enter')

        self.pars['AbsPosEdit' + parNameSuffix] = QtWidgets.QLineEdit('0.0')
        self.pars['AbsPosEdit' + parNameSuffix]._name = 'XY--Y'
        self.pars['AbsPosEdit' + parNameSuffix]._type = 'str'
        self.pars['AbsPosEdit' + parNameSuffix].setMinimumWidth(100)
        self.validator = QDoubleValidator()
        self.pars['AbsPosEdit' + parNameSuffix].setValidator(self.validator)
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


        self.elementList.append(self.pars['AbsPosEdit' + parNameSuffix])

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

        self.settingsWindow = PositionerSettings(self)

        # self.settingsButtonLayout = QtWidgets.QHBoxLayout()
        self.settingsButton = QtWidgets.QPushButton('Open Settings')
        self.settingsButton.clicked.connect(self.settingsWindow.show)
        # self.settingsButtonLayout.addWidget(self.pars['AbsPosUnit' + parNameSuffix])
        self.posLayout.addWidget(self.settingsButton)
        
        
    def wheelEvent(self, event: QWheelEvent):
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                self.focusDelta = event.angleDelta().y() / 120 * float(self.pars['StepEditCoarse'+'Z--Z'].text())
                self.sigWheelEvent.emit(self.focusDelta)
            elif modifiers == QtCore.Qt.ControlModifier:
                self.focusDelta = event.angleDelta().y() / 120 * float(self.pars['StepEdit'+'Z--Z'].text())
                self.sigWheelEvent.emit(self.focusDelta)
            event.accept()

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
        self.pars['AbsPosEdit'+parNameSuffix].setText(str(round(position,1)))

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
        
        self.updateAbsPos(positionerName, axis, position) # Updates entry window for absolute position


    def _getParNameSuffix(self, positionerName, axis):
        return f'{positionerName}--{axis}'


class PositionerSettings(QMainWindow):
    def __init__(self, parent: None):

        super().__init__(parent)
        self.setWindowTitle("Load Settings")
        self.setMinimumSize(600, 600)
        self.overallLayout = QtWidgets.QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(self.overallLayout)
        self.setCentralWidget(central_widget)
        
        self.skewLayout = QtWidgets.QHBoxLayout()


        self.skewLabel = QtWidgets.QLabel(f'<strong>10.2</strong>')
        
        self.skewEntry = QtWidgets.QLineEdit('0.0')
        self.skewEntry.setFixedWidth(50)
        
        self.skewButton = QtWidgets.QPushButton('Set')
        self.skewButton.clicked.connect(self.setSkewOnStage)
        
        
        self.skewLayout.addWidget(self.skewLabel)
        self.skewLayout.addWidget(self.skewEntry)
        self.skewLayout.addWidget(self.skewButton)
        self.skewLayout.addStretch() # Pushes widgets to the left
        
        self.overallLayout.addLayout(self.skewLayout)
        
    def setSkewOnStage(self):
        pass

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
