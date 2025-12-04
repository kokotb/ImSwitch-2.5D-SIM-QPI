from qtpy import QtCore, QtWidgets
from PyQt5.QtGui import QWheelEvent , QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QCheckBox, QMainWindow, QWidget, QLineEdit, QPushButton
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget
from PyQt5.QtCore import Qt, QLocale

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

        # initializing 'Open Settings' button and window
        self.settingsWindow = PositionerSettings(self)
        self.settingsButton = QtWidgets.QPushButton('Open Settings')
        self.settingsButton.clicked.connect(self.openSettingsProtected)
        self.posLayout.addWidget(self.settingsButton)
        
    def openSettingsProtected(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Settings Locked", "Enter password:", QtWidgets.QLineEdit.Password)
        if ok and text == "SIM":
            self.settingsWindow.show()
        elif not ok and text == "":
            pass
        else:
            QtWidgets.QMessageBox.warning(self, "Incorrect Password", "The password you entered is incorrect.")
        
        
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
    sigCheckValidity = QtCore.Signal(str)
    def __init__(self, parent: None):
        super().__init__(parent)
        self.setWindowTitle("Tiling Settings")
        self.setMinimumSize(500, 600)
        self.overallLayout = QtWidgets.QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(self.overallLayout)
        self.setCentralWidget(central_widget)

        # 2 point skew title
        self.skew2ptTitleLayout = QtWidgets.QHBoxLayout()
        self.skew2ptTitleLayout = QtWidgets.QHBoxLayout()
        self.skew2ptTitleLabel = QtWidgets.QLabel('<strong>Two-Point Skew (°)</strong>')
        self.skew2ptTitleLayout.addWidget(self.skew2ptTitleLabel)
        self.skew2ptTitleLayout.addStretch()
        self.overallLayout.addLayout(self.skew2ptTitleLayout)
        self.overallLayout.addLayout(self.skew2ptTitleLayout)
        
        # 2 point skew layout
        self.skew2ptLayout = QtWidgets.QHBoxLayout()
        self.skew2ptLayout.addSpacing(6)
        self.skew2ptButton = QtWidgets.QPushButton('Set Point A')
        self.skew2ptInfo = QtWidgets.QLabel("🛈")
        self.skew2ptInfo.setStyleSheet("QLabel {font-size: 16px}")
        self.skew2ptInfo.setToolTip(
            "Two-Point Skew:\n"
            "1. Move to the first point on the tilted sample edge and press the button.\n"
            "2. Move to the second point along the same horizontal edge of your sample and press again.\n"
            "The skew will be calculated automatically and displayed on the right."
        )
        self.skewLabel = QtWidgets.QLabel(f'<strong>0.0</strong>')
        self.skew2ptLayout.addWidget(self.skew2ptButton)
        self.skew2ptLayout.addWidget(self.skew2ptInfo)
        self.skew2ptLayout.addWidget(self.skewLabel)
        self.skew2ptLayout.addStretch()
        self.overallLayout.addLayout(self.skew2ptLayout)
        
        # skew title
        self.skewTitleLayout = QtWidgets.QHBoxLayout()
        self.skewTitleLabel = QtWidgets.QLabel(f'<strong>Manual Skew (°)</strong>')       
        self.skewTitleLayout.addWidget(self.skewTitleLabel)
        self.overallLayout.addLayout(self.skewTitleLayout)
        
        # skew layout
        self.skewLayout = QtWidgets.QHBoxLayout()
        self.skewLayout.addSpacing(6)
        self.skewEntry = QtWidgets.QLineEdit('0.0')
        self.skewEntry.setFixedWidth(60)
        self.skewEntry.setToolTip("Enter a skew angle between -89.9 and 89.9.")
        self.validator = QDoubleValidator(-89.9, 89.9, 2)
        self.validator.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.skewEntry.setValidator(self.validator)
        self.skewButton = QtWidgets.QPushButton('Set')
        self.skewLayout.addWidget(self.skewEntry)
        self.skewLayout.addWidget(self.skewButton)
        self.skewLayout.addStretch()
        self.overallLayout.addLayout(self.skewLayout)    
        
        # stage max speed title
        self.maxSpeedTitleLayout = QtWidgets.QHBoxLayout()
        self.maxSpeedTitleLabel = QtWidgets.QLabel(f'<strong>Max Speed (µm/s)</strong>')       
        self.maxSpeedTitleLayout.addWidget(self.maxSpeedTitleLabel)
        self.overallLayout.addLayout(self.maxSpeedTitleLayout)      
        
        # stage max speed layout
        self.maxSpeedLayout = QtWidgets.QHBoxLayout()
        self.maxSpeedLabel = QtWidgets.QLabel(f'<strong>0</strong>')
        self.maxSpeedEntry = QtWidgets.QLineEdit('0')
        self.maxSpeedEntry.setFixedWidth(60)
        self.maxSpeedEntry.setToolTip("Enter the maximum speed during a point to point move (1000-10000).")
        self.validator = QIntValidator(1000,10000)
        self.maxSpeedEntry.setValidator(self.validator)
        self.maxSpeedButton = QtWidgets.QPushButton('Set')
        self.maxSpeedLayout.addWidget(self.maxSpeedLabel)
        self.maxSpeedLayout.addWidget(self.maxSpeedEntry)
        self.maxSpeedLayout.addWidget(self.maxSpeedButton)
        self.maxSpeedLayout.addStretch()
        self.overallLayout.addLayout(self.maxSpeedLayout)       
         
        # stage max acceleration title
        self.maxAccTitleLayout = QtWidgets.QHBoxLayout()
        self.maxAccTitleLabel = QtWidgets.QLabel(f'<strong>Max Acc (µm/s²)</strong>') 
        self.maxAccTitleLayout.addWidget(self.maxAccTitleLabel)
        self.overallLayout.addLayout(self.maxAccTitleLayout)  
        
        # stage max acceleration layout 
        self.maxAccLayout = QtWidgets.QHBoxLayout()
        self.maxAccLabel = QtWidgets.QLabel(f'<strong>0</strong>')
        self.maxAccEntry = QtWidgets.QLineEdit('0')
        self.maxAccEntry.setFixedWidth(60)
        self.maxAccEntry.setToolTip("Enter the maximum acceleration during a point to point move (1000-100000).")
        self.validator = QIntValidator(1000,100000)
        self.maxAccEntry.setValidator(self.validator)
        self.maxAccButton = QtWidgets.QPushButton('Set')
        self.maxAccLayout.addWidget(self.maxAccLabel)
        self.maxAccLayout.addWidget(self.maxAccEntry)
        self.maxAccLayout.addWidget(self.maxAccButton)
        self.maxAccLayout.addStretch()
        self.overallLayout.addLayout(self.maxAccLayout)
            
        # stage jerk title
        self.jerkTitleLayout = QtWidgets.QHBoxLayout()
        self.jerkTitleLabel = QtWidgets.QLabel(f'<strong>Jerk (ms)</strong>')       
        self.jerkTitleLayout.addWidget(self.jerkTitleLabel)
        self.overallLayout.addLayout(self.jerkTitleLayout)  
        
        # stage jerk layout 
        self.jerkLayout = QtWidgets.QHBoxLayout()
        self.jerkLabel = QtWidgets.QLabel(f'<strong>0</strong>')
        self.jerkEntry = QtWidgets.QLineEdit('0')
        self.jerkEntry.setFixedWidth(60)
        self.jerkEntry.setToolTip("Enter the jerk time (0-1000).")
        self.validator = QIntValidator(0,1000) # find the correct values
        self.jerkEntry.setValidator(self.validator)
        self.jerkButton = QtWidgets.QPushButton('Set')
        self.jerkLayout.addWidget(self.jerkLabel)
        self.jerkLayout.addWidget(self.jerkEntry)
        self.jerkLayout.addWidget(self.jerkButton)
        self.jerkLayout.addStretch()
        self.overallLayout.addLayout(self.jerkLayout)     
        
        # stage backlash title
        self.backlashTitleLayout = QtWidgets.QHBoxLayout()
        self.backlashCheck = QtWidgets.QCheckBox()
        self.backlashCheck.setChecked(False)
        self.backlashCheck.setToolTip('Check here to enable backlash.')
        self.backlashTitleLayout.addWidget(self.backlashCheck)
        self.backlashTitleLabel = QtWidgets.QLabel(f'<strong>Backlash (µm)</strong>')
        self.backlashTitleLayout.addWidget(self.backlashTitleLabel)
        self.backlashTitleLayout.addStretch()
        self.overallLayout.addLayout(self.backlashTitleLayout)

        # stage backlash layout 
        self.backlashLayout = QtWidgets.QHBoxLayout()
        self.backlashLabel = QtWidgets.QLabel(f'<strong>0</strong>')
        self.backlashEntry = QtWidgets.QLineEdit('0')
        self.backlashEntry.setFixedWidth(60)
        self.backlashEntry.setToolTip("Enter the backlash (0-100).")
        self.validator = QIntValidator(0,100) # find the correct values
        self.backlashEntry.setValidator(self.validator)
        self.backlashButton = QtWidgets.QPushButton('Set')
        self.backlashLayout.addWidget(self.backlashLabel)
        self.backlashLayout.addWidget(self.backlashEntry)
        self.backlashLayout.addWidget(self.backlashButton)
        self.backlashLayout.addStretch()
        self.overallLayout.addLayout(self.backlashLayout)
        self.backlashWidgets = [self.backlashLabel, self.backlashEntry, self.backlashButton]
        for widget in self.backlashWidgets:
            widget.setEnabled(False)

        # keep the overall layout together
        self.overallLayout.addStretch()
        
        
        
        self.skewEntry.textChanged.connect(lambda *args, name='skewEntry': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        self.maxSpeedEntry.textChanged.connect(lambda *args, name='maxSpeedEntry': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        self.maxAccEntry.textChanged.connect(lambda *args, name='maxAccEntry': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        self.jerkEntry.textChanged.connect(lambda *args, name='jerkEntry': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        self.backlashEntry.textChanged.connect(lambda *args, name='backlashEntry': self.sigCheckValidity.emit(name))
        self.sigCheckValidity.connect(self.checkValidity)
        
    def checkValidity(self, name):
        if name == 'skewEntry':
            signalOrigin = self.skewEntry
        if name == 'maxSpeedEntry':
            signalOrigin = self.maxSpeedEntry
        if name == 'maxAccEntry':
            signalOrigin = self.maxAccEntry
        if name == 'jerkEntry':
            signalOrigin = self.jerkEntry
        if name == 'backlashEntry':
            signalOrigin = self.backlashEntry
        valid = signalOrigin.hasAcceptableInput()
        if valid:
            signalOrigin.setStyleSheet('')
        else:
            signalOrigin.setStyleSheet("border: 1px solid red;")
    
    

        
        



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
