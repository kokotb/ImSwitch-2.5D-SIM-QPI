import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import ParameterTree
from qtpy import QtCore, QtWidgets
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QLocale
from PyQt5.QtGui import QWheelEvent , QDoubleValidator, QIntValidator



class SLM25DWidget(Widget):
    """ Widget containing 2.5D SLM interface. """
    sig25DParamChanged = QtCore.Signal(str, str, str)
    sigZernParamChanged = QtCore.Signal(str, str, str, float)
    # sigAutoZernParamChanged = QtCore.Signal(str, str, str, str)


    #Signals for updating and eventually projecting images
    sigZernikeMaskChanged = QtCore.Signal()
    sig25DMaskChanged = QtCore.Signal()
    sigMaskCenterChanged = QtCore.Signal()



#Reset button signals
    sigResetZern = QtCore.Signal()
    sigReset25D = QtCore.Signal()

#Signals to control enabling buttons/SLM/displaying preview window
    sigLockZernike = QtCore.Signal(bool)


    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        #For development only:
        self.maskScaleAvailable = False

        ### Placeholders for entire image display box (2 labels, 2 images).
        self.slmFrame = pg.GraphicsLayoutWidget()
        self.slmFrame.setEnabled(False)
        self.slmFrame.addLabel('Zernike', angle=-90, row=0, col=0)
        self.vbZernike = self.slmFrame.addViewBox(row=0, col=1, enableMouse=False, border='w', lockAspect=True)
        self.slmFrame.addLabel('2.5D Mask', angle=-90, row=0, col=2)
        self.vb25D = self.slmFrame.addViewBox(row=0, col=3, enableMouse=False, border='w', lockAspect=True)
        self.imgZernike = pg.ImageItem()
        self.img25d = pg.ImageItem()
        #Inititally displayed images. Just black.
        self.matrixZernike = np.zeros((1920, 1080))
        self.matrix25d = np.zeros((1920, 1080))
        self.overlayMatrix25D =  np.zeros((1920, 1080))
        self.overlayImg25D = pg.ImageItem(self.overlayMatrix25D)
        self.imgZernike.setImage(self.matrixZernike, levels=(0, 255)) 
        self.img25d.setImage(self.matrix25d)
        #Add initially created images to the widget
        self.vbZernike.addItem(self.imgZernike)
        self.vb25D.addItem(self.img25d) #This line must before addItem(self.overlayImg25D) so transparent overlay is on top of this layer.
        self.vb25D.addItem(self.overlayImg25D)
        ###

        #Initialize buttons on top row of the widget
        self.start25D = QPushButton("Start 2.5D")
        self.stop25D = QPushButton("Stop 2.5D")
        self.stop25D.setEnabled(False)
        self.activate25DSLM = QCheckBox('Activate 2.5D SLM')
        
        self.projectZernike = QCheckBox('Project Zernike')
        self.projectZernike.setChecked(True)
        self.projectZernike.setEnabled(False)
        self.project25D = QCheckBox('Project 2.5D Mask')
        self.project25D.setChecked(False)
        self.project25D.setEnabled(False)
        # self.projectCenter = QCheckBox('Project Center')
        # self.projectCenter.setChecked(False)
        # self.projectCenter.setEnabled(False)

        #Other buttons at the bottom
        self.beginAZbutton = QPushButton("AutoZernike New")
        self.beginAZbutton.setEnabled(False)
        self.beginAZbutton.setFixedWidth(250)
        self.centerMaskbutton = QPushButton("Center Mask")
        self.centerMaskbutton.setEnabled(False)
        self.centerMaskbutton.setFixedWidth(250)


        # self.autoZernCheckbox = QCheckBox("Auto Zernike")
        # self.autoZernCheckbox.stateChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Both','AZEnabled',str(value))) #!!! ask Cody???
        # self.autoZernCheckbox.setEnabled(False)
        # self.autoZernCheckbox.setChecked(True)

        # self.autoZernCheckboxNew = QCheckBox("Auto Zernike New")
        # # self.autoZernCheckboxNew.stateChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Both','AZEnabled',str(value))) #!!! ask Cody???
        # self.autoZernCheckboxNew.setEnabled(False)
        # self.autoZernCheckboxNew.setChecked(True)

        self.sideSelectComboLabel = QtWidgets.QLabel('Auto Side:')
        self.sideSelectCombo = QComboBox()
        self.sideSelectCombo.addItems(["Left", "Right"])
        self.sideSelectCombo.setCurrentIndex(1)

        # self.autocorectLeftRadioButton = QRadioButton('Left-Autocorrect')
        # self.autocorectRightRadioButton = QRadioButton('Right-Autocorrect')
        # self.autocorectRightRadioButton.setChecked(True)

        self.channelSelectComboLabel = QtWidgets.QLabel('Auto Channel:')
        self.channelSelectCombo = QComboBox()
        self.channelSelectCombo.addItems(["Red", "Green", "Blue"])
        self.channelSelectCombo.setCurrentIndex(0)
        # self.channelSelectCombo.currenteditingFinished.connect()

        # self.autocorectRedRadioButton = QRadioButton('Red-Autocorrect')
        # self.autocorectGreenRadioButton = QRadioButton('Green-Autocorrect')
        # self.autocorectBlueRadioButton = QRadioButton('Blue-Autocorrect')
        # self.autocorectRedRadioButton.setChecked(True)

        self.loadImgToSLMbutton = QPushButton("Load Image")
        self.loadImgToSLMbutton.setEnabled(False)
        self.loadImgToSLMbutton.setFixedWidth(250)



        #Setup layouts
        self.mainLayout = QtWidgets.QVBoxLayout() #Overall main layout
        self.grid12HorizLayout = QtWidgets.QHBoxLayout() #Zernike/2.5D horizontal layout to contain 2 grid layouts.
        self.topLayout = QtWidgets.QGridLayout() #Layout containing everything above grids 1 and 2.
        self.grid1 = QtWidgets.QGridLayout() #Zernike
        self.grid1Buttons = QtWidgets.QHBoxLayout() #Buttons below zernike parameters
        self.grid1Main = QtWidgets.QVBoxLayout() #Container for grid1 and the botton below grid 1
        self.grid2 = QtWidgets.QGridLayout() #2.5D
        self.grid3 = QtWidgets.QGridLayout() #David's million buttons layout
        self.setLayout(self.mainLayout)

        #Add the buttons/checkboxes on top row
        self.topLayout.addWidget(self.start25D,0,0)
        self.topLayout.addWidget(self.stop25D,0,1)
        self.topLayout.addWidget(self.activate25DSLM,0,2)
        self.topLayout.addWidget(self.projectZernike,0,3)
        self.topLayout.addWidget(self.project25D,0,4)
        # self.topLayout.addWidget(self.projectCenter,0,5)
        self.topLayout.addWidget(self.slmFrame, 1, 0, 1, 6)
        self.topLayout.setRowMinimumHeight(1, 110)

        #Group radio buttons together in logical groups.
        # self.LRbutton_group = QButtonGroup()  
        # self.LRbutton_group.addButton(self.autocorectLeftRadioButton)
        # self.LRbutton_group.addButton(self.autocorectRightRadioButton)
        # self.Colorbutton_group = QButtonGroup()  
        # self.Colorbutton_group.addButton(self.autocorectRedRadioButton)
        # self.Colorbutton_group.addButton(self.autocorectGreenRadioButton)
        # self.Colorbutton_group.addButton(self.autocorectBlueRadioButton)

        ###Add David's buttons
        self.grid3.addWidget(self.loadImgToSLMbutton, 0, 0)
        self.grid3.addWidget(self.beginAZbutton, 0, 1)
        self.grid3.addWidget(self.centerMaskbutton, 0, 2)

        # self.grid3.addWidget(self.autoZernCheckbox, 0, 4)
        # self.grid3.addWidget(self.autoZernCheckboxNew, 1, 0)

        self.grid3.addWidget(self.sideSelectComboLabel, 1, 0)
        self.grid3.addWidget(self.sideSelectCombo, 1, 1)
        # self.grid3.addWidget(self.autocorectRedRadioButton, 2, 0)
        # self.grid3.addWidget(self.autocorectGreenRadioButton, 2, 1)
        # self.grid3.addWidget(self.autocorectBlueRadioButton, 2, 2)
        self.grid3.addWidget(self.channelSelectComboLabel, 2, 0)
        self.grid3.addWidget(self.channelSelectCombo, 2, 1)

        ###
        
        # Horizontal lines separating logic sections
        self.dividerHoriz = QFrame()
        self.dividerHoriz.setFrameShape(QFrame.HLine)
        self.dividerHoriz.setFrameShadow(QFrame.Plain)
        self.dividerHoriz.setLineWidth(200)

        self.mainLayout.addLayout(self.topLayout)
        self.mainLayout.addWidget(self.dividerHoriz)


        self.axisValTypes = {"Gamma": float, "Psi": float, "Left Center-X": int, "Left Center-Y": int, "Right Center-X": int, "Right Center-Y": int, "Beam Diameter": float}
        self.pars = {}
        # SETTING PHASE MASK PARAMETERS =========================================================================
        
        self.ZernikeCoefficientNames = ["(0,0)", "(1,-1)", "(1,1)", "(2,-2)", "(2,0)", "(2,2)", "(3,-3)", "(3,-1)", "(3,1)", "(3,3)", "(4,0)"]
        self.ZernikeAberrationNames = ["Piston", "Y-tilt", "X-tilt", "Oblique Astigmatism", "Defocus", "Vertical Astigmatism", "Vertical Trefoil", "Vertical Coma", "Horizontal Coma", "Horizontal Trefoil", "Spherical"]
        self.ZernikeSides = ["Left", "Right"]
        self.elementListZern = []

        self.zernLabel = QtWidgets.QLabel(f'<strong>Zernike Coefficients</strong>')
        self.zernLabel.setEnabled(False)
        self.zernLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid1.addWidget(self.zernLabel, 0, 0)

        self.leftZernLabel = QtWidgets.QLabel(f'<strong>Left</strong>')
        self.leftZernLabel.setEnabled(False)
        self.leftZernLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid1.addWidget(self.leftZernLabel, 0, 1)

        self.rightZernLabel = QtWidgets.QLabel(f'<strong>Right</strong>')
        self.rightZernLabel.setEnabled(False)
        self.rightZernLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid1.addWidget(self.rightZernLabel, 0, 2)

        for side in self.ZernikeSides:
            self.row = 0
            for i in range(len(self.ZernikeCoefficientNames)):
                self.row += 1
                name = self.ZernikeCoefficientNames[i]
                labelNames = f'{self.ZernikeCoefficientNames[i]} - {self.ZernikeAberrationNames[i]}'
                self.axisValTypes[name + side] = float

                label = f'{labelNames}'

                #Define all widget items
                self.pars['Label' + name + side] = QtWidgets.QLabel(f'{label}')
                self.pars['Label' + name + side].setTextFormat(QtCore.Qt.RichText)
                self.pars['AbsPosEdit' + name + side] = QtWidgets.QDoubleSpinBox()
                self.pars['AbsPosEdit' + name + side]._name = self.ZernikeAberrationNames[i]
                self.pars['AbsPosEdit' + name + side]._type = 'flt'
                
                if side == 'Left': self.pars['AbsPosEdit' + name + side]._side = 'Left'
                elif side == 'Right': self.pars['AbsPosEdit' + name + side]._side = 'Right'
        
                self.pars['AbsPosEdit' + name + side].setRange(-5.0,5.0)
                if name == '(4,0)': #Different settings for 'spherical'
                    self.pars['AbsPosEdit' + name + side].setSingleStep(0.01)
                    self.pars['AbsPosEdit' + name + side].setDecimals(2)
                else:
                    self.pars['AbsPosEdit' + name + side].setSingleStep(0.1)
                    self.pars['AbsPosEdit' + name + side].setDecimals(2)
                self.pars['AbsPosEdit' + name + side].setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
                self.pars['AbsPosEdit' + name + side].setValue(0.101)
                self.pars['AbsPosEdit' + name + side].setFixedWidth(75)

                self.pars['Label' + name + side].setEnabled(False)
                # self.pars['UpButton' + name + side].setEnabled(False)
                # self.pars['DownButton' + name + side].setEnabled(False)
                self.pars['AbsPosEdit' + name + side].setEnabled(False)

                self.elementListZern.append(self.pars['AbsPosEdit' + name + side])
                
                # Add to widget object
                if side == "Left":
                    index = 0
                elif side == "Right":
                    index = 1
                else:
                    print("ERROR: Zernike buttons left - right failed")
                if side == "Left":
                    self.grid1.addWidget(self.pars['Label' + name + side], self.row, 0 + index)
                self.grid1.addWidget(self.pars['AbsPosEdit' + name + side], self.row, 1 + index)
                # self.pars['AbsPosEdit' + name].setValue(0.1)       

                self.pars['AbsPosEdit' + name + side].valueChanged.connect(self.sigZernikeMaskChanged.emit) #Anytime a Zernike value is changed, it sends this signal received by controller

        self.resetZern = QPushButton("Reset Zern")
        self.resetZern.setEnabled(False)
        self.resetZern.clicked.connect(self.sigResetZern.emit)
        self.grid1Buttons.addWidget(self.resetZern)

        self.lockZernCheckbox = QCheckBox("Lock Zernike")
        self.lockZernCheckbox.stateChanged.connect(lambda value: self.zernikeLocked(value))
        self.lockZernCheckbox.setEnabled(False)
        self.lockZernCheckbox.setChecked(False)
        self.grid1Buttons.addWidget(self.lockZernCheckbox)

        self.slmPreview = QPushButton("SLM View")
        self.slmPreview.setEnabled(False)
        self.slmPreview.setFixedWidth(250)
        self.grid1Buttons.addWidget(self.slmPreview)

        self.grid1Main.addLayout(self.grid1)
        self.grid1Main.addLayout(self.grid1Buttons)


        # SETTING PHASE MASK PARAMETERS =========================================================================
        self.row = 0

        self.label25D = QtWidgets.QLabel(f'<strong>2.5D Mask</strong>')
        self.label25D.setEnabled(False)
        self.label25D.setTextFormat(QtCore.Qt.RichText)
        self.grid2.addWidget(self.label25D, self.row, 0)

        self.valLabel = QtWidgets.QLabel(f'<strong>Value</strong>')
        self.valLabel.setEnabled(False)
        self.valLabel.setTextFormat(QtCore.Qt.RichText)
        self.grid2.addWidget(self.valLabel, self.row, 1)

        self.reset25D = QPushButton("Reset 2.5D")
        self.reset25D.setEnabled(False)
        self.reset25D.clicked.connect(self.sigReset25D.emit)
        self.grid2.addWidget(self.reset25D, self.row, 2)

        self.paramConstraintDict = {'Gamma':('double',(-20,20),1, 0.1, ''), 'Psi': ('double',(-10,10),1, 0.1, ''), 'Left Center-X': ('integer',(1,960),0, 10, 'px'), 'Left Center-Y': ('integer',(1,1080),0, 10, 'px'), 
                                    'Right Center-X': ('integer',(960,1920),0, 10, 'px'), 'Right Center-Y': ('integer',(1,1080),0, 10, 'px'), 'Beam Diameter': ('double',(1,9),1, 0.1, 'mm')}
        self.paramNames = list(self.paramConstraintDict.keys())

        self.elementList25D = []
        for i in range(len(self.paramConstraintDict)):
            self.row += 1
            name = self.paramNames[i]
            # AbsInitialValue = self.absAxisInitialValues[name]
            self.unit = self.paramConstraintDict[name][4]

            label = f'{name}'

            #Define all widget items
            self.pars['Label' + name] = QtWidgets.QLabel(f'{label}')
            self.pars['Label' + name].setTextFormat(QtCore.Qt.RichText)

            self.pars['AbsPosUnit' + name] = QtWidgets.QLabel(self.unit)
            self.pars['Label' + name].setEnabled(False)
            
            self.pars['AbsPosUnit' + name].setEnabled(False)

            if self.paramConstraintDict[name][0] == 'double':
                self.pars['AbsPosEdit' + name] = QtWidgets.QDoubleSpinBox()
                self.pars['AbsPosEdit' + name]._name = name
                self.pars['AbsPosEdit' + name].setFixedWidth(75)
                self.pars['AbsPosEdit' + name].setRange(self.paramConstraintDict[name][1][0], self.paramConstraintDict[name][1][1])
                self.pars['AbsPosEdit' + name].setSingleStep(self.paramConstraintDict[name][3])
                self.pars['AbsPosEdit' + name].setDecimals(self.paramConstraintDict[name][2])
                self.pars['AbsPosEdit' + name].setValue(0)
                self.pars['AbsPosEdit' + name].setEnabled(False)

            if self.paramConstraintDict[name][0] == 'integer': #All the center/position parameters
                self.pars['AbsPosEdit' + name] = QtWidgets.QSpinBox()
                self.pars['AbsPosEdit' + name]._name = name
                self.pars['AbsPosEdit' + name].setFixedWidth(75)
                self.pars['AbsPosEdit' + name].setRange(self.paramConstraintDict[name][1][0], self.paramConstraintDict[name][1][1])
                self.pars['AbsPosEdit' + name].setSingleStep(self.paramConstraintDict[name][3])
                self.pars['AbsPosEdit' + name].setValue(0)
                self.pars['AbsPosEdit' + name].setEnabled(False)




            self.elementList25D.append(self.pars['AbsPosEdit' + name])

            # Add to widget object
            self.grid2.addWidget(self.pars['Label' + name], self.row, 0)

            self.grid2.addWidget(self.pars['AbsPosEdit' + name], self.row, 1)
            self.grid2.addWidget(self.pars['AbsPosUnit' + name], self.row, 2)



            # Connect spinboxes to signals (Beam Diameter connected in Controller)
            if (name == 'Gamma') or (name == 'Psi'):
                self.pars['AbsPosEdit' + name].valueChanged.connect(self.sig25DMaskChanged.emit)

            elif self.paramConstraintDict[name][0] == 'integer': #All center/position fields.
                self.pars['AbsPosEdit' + name].editingFinished.connect(self.sigMaskCenterChanged.emit)



        self.maskScaleNumberLabel = QtWidgets.QLabel("Mask Scale")
        self.maskScaleNumberLabel.setEnabled(False)
        self.maskScaleNumber = QtWidgets.QSpinBox()
        self.maskScaleNumber.setRange(0,255)
        self.maskScaleNumber.setSingleStep(1)
        self.maskScaleNumber.setValue(255)
        self.maskScaleNumber.setEnabled(False)

        self.maskScaleNumber.setFixedWidth(75)

        self.grid2.addWidget(self.maskScaleNumberLabel, self.row + 1, 0)
        self.grid2.addWidget(self.maskScaleNumber, self.row + 1, 1)

        self.grid2.setRowStretch(self.grid2.rowCount(), 1)
        self.grid2.setColumnStretch(self.grid2.columnCount(), 1)

        self.dividerVert = QFrame() #Vertical divider between Zernike and 2.5D
        self.dividerVert.setFrameShape(QFrame.VLine)
        self.dividerVert.setFrameShadow(QFrame.Plain)
        self.dividerVert.setLineWidth(200)

        self.grid12HorizLayout.addLayout(self.grid1Main)
        self.grid12HorizLayout.addWidget(self.dividerVert)
        self.grid12HorizLayout.addLayout(self.grid2)
        self.mainLayout.addLayout(self.grid12HorizLayout)
        self.mainLayout.addWidget(self.dividerHoriz)
        self.mainLayout.addLayout(self.grid3)

        

        # # Connect received signals to funcions
        self.sigResetZern.connect(self.resetZernToDefault)
        self.sigReset25D.connect(self.reset25DToDefault)

        self.connect25DSharedAttrSigs()

    def zernikeLocked(self, value):
        
        self.beginAZbutton.setEnabled(not value)
        # self.autoZernCheckbox.setEnabled(not value)
        # self.autoZernCheckboxNew.setEnabled(not value)
        self.resetZern.setEnabled(not value)
        self.loadImgToSLMbutton.setEnabled(not value)
        for i in range(len(self.ZernikeCoefficientNames)):
            for side in self.ZernikeSides:
                name = self.ZernikeCoefficientNames[i]
                self.pars['Label' + name + side].setEnabled(not value)
                # self.pars['UpButton' + name + side].setEnabled(not value)
                # self.pars['DownButton' + name + side].setEnabled(not value)
                self.pars['AbsPosEdit' + name + side].setEnabled(not value)

        self.sigLockZernike.emit(bool(value))

    def reset25DToDefault(self):
        
        for name in self.paramNames:
            absInitValue = self.valueDict25D[name]
            self.pars['AbsPosEdit' + name].setValue(absInitValue)
        # self.sigMaskCenterChanged.emit()

    def resetZernToDefault(self):
        for side in self.ZernikeSides:
            for name in self.ZernikeCoefficientNames:
                self.pars['AbsPosEdit' + name + side].setValue(self.valueDictZern25D[name + side])
        # self.sigUpdateZernikeMask.emit()

    def askYesNoQuestion(self):
        """ Asks the user a yes/no question and returns whether "yes" was clicked. """
        result = QtWidgets.QMessageBox.question(None, 'Need to Select single isolated bead', 'Please select a single isolated bead for aberration analysis.'
                                                ' . Go to image display window -> New shapes layer -> Add rectangles. Draw frame aproximately 20x20 pixels, '
                                                 'with isolated bead in the middle and empty dark background. Would you like to countiniue?',
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        return result == QtWidgets.QMessageBox.Yes
         
    def disableAll(self):
        self.slmPreview.setEnabled(False)
        self.beginAZbutton.setEnabled(False)
        self.centerMaskbutton.setEnabled(False)
        self.leftZernLabel.setEnabled(False)
        self.rightZernLabel.setEnabled(False)
        self.valLabel.setEnabled(False)
        self.maskScaleNumberLabel.setEnabled(False)
        self.maskScaleNumber.setEnabled(False)
        # self.autoZernCheckbox.setEnabled(False)
        # self.autoZernCheckboxNew.setEnabled(False)
        self.lockZernCheckbox.setEnabled(False)
        self.slmFrame.setEnabled(False)
        self.zernLabel.setEnabled(False)
        self.label25D.setEnabled(False)
        self.projectZernike.setEnabled(False)
        self.project25D.setEnabled(False)
        # self.projectCenter.setEnabled(False)
        # self.label25DStep.setEnabled(False)
        self.resetZern.setEnabled(False)
        self.reset25D.setEnabled(False)
        self.loadImgToSLMbutton.setEnabled(False)
        # self.slmFrameCenter.setEnabled(False)
        # self.slmFrame25d.setEnabled(False)
        for i in range(len(self.ZernikeCoefficientNames)):
            for side in self.ZernikeSides:
                name = self.ZernikeCoefficientNames[i]
                self.pars['Label' + name + side].setEnabled(False)
                # self.pars['UpButton' + name + side].setEnabled(False)
                # self.pars['DownButton' + name + side].setEnabled(False)
                self.pars['AbsPosEdit' + name + side].setEnabled(False)

        for i in range(len(self.paramNames)):
            name = self.paramNames[i]
            self.pars['Label' + name].setEnabled(False)
            self.pars['AbsPosEdit' + name].setEnabled(False)
            self.pars['AbsPosUnit' + name].setEnabled(False)

    def enableAll(self):
        self.slmPreview.setEnabled(True)
        self.beginAZbutton.setEnabled(True)
        self.centerMaskbutton.setEnabled(True)
        self.leftZernLabel.setEnabled(True)
        self.rightZernLabel.setEnabled(True)
        if self.maskScaleAvailable:
            self.maskScaleNumberLabel.setEnabled(True)
            self.maskScaleNumber.setEnabled(True)
        # self.autoZernCheckbox.setEnabled(True)
        # self.autoZernCheckboxNew.setEnabled(True)

        self.lockZernCheckbox.setEnabled(True)
        self.valLabel.setEnabled(True)
        self.slmFrame.setEnabled(True)
        self.zernLabel.setEnabled(True)
        self.label25D.setEnabled(True)
        self.projectZernike.setEnabled(True)
        self.project25D.setEnabled(True)
        # self.projectCenter.setEnabled(True)
        # self.label25DStep.setEnabled(True)
        self.resetZern.setEnabled(True)
        self.reset25D.setEnabled(True)
        self.loadImgToSLMbutton.setEnabled(True)
        # self.slmFrameCenter.setEnabled(True)
        # self.slmFrame25d.setEnabled(True)
        for i in range(len(self.ZernikeCoefficientNames)):
            for side in self.ZernikeSides:
                name = self.ZernikeCoefficientNames[i]
                self.pars['Label' + name + side].setEnabled(True)
                # self.pars['UpButton' + name + side].setEnabled(True)
                # self.pars['DownButton' + name + side].setEnabled(True)
                self.pars['AbsPosEdit' + name + side].setEnabled(True)

        for i in range(len(self.paramNames)):
            name = self.paramNames[i]
            self.pars['Label' + name].setEnabled(True)
            # self.pars['UpButton' + name].setEnabled(True)
            # self.pars['DownButton' + name].setEnabled(True)
            # self.pars['StepEdit' + name].setEnabled(True)
            # self.pars['StepUnit' + name].setEnabled(True)
            self.pars['AbsPosEdit' + name].setEnabled(True)
            self.pars['AbsPosUnit' + name].setEnabled(True)


    def SIMToggled(self, boolSIM): #Only function is to disable/enable 2.5D Start button as SIM is turned on/off.
        self.start25D.setEnabled(not boolSIM)
        self.stop25D.setEnabled(boolSIM)

    def connect25DSharedAttrSigs(self):
        self.pars['AbsPosEditGamma'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Gamma',str(value)))
        self.pars['AbsPosEditPsi'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Psi',str(value)))
        self.pars['AbsPosEditLeft Center-X'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Left Center-X',str(value)))
        self.pars['AbsPosEditLeft Center-Y'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Left Center-Y',str(value)))
        self.pars['AbsPosEditRight Center-X'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Right Center-X',str(value)))
        self.pars['AbsPosEditRight Center-Y'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Right Center-Y',str(value)))
        self.pars['AbsPosEditBeam Diameter'].valueChanged.connect(lambda value: self.sig25DParamChanged.emit('25D SLM Parameters','Beam Diameter',str(value)))
        #######################
        self.pars['AbsPosEdit(0,0)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Piston',value))
        self.pars['AbsPosEdit(1,-1)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Y-tilt',value))
        self.pars['AbsPosEdit(1,1)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','X-tilt',value))
        self.pars['AbsPosEdit(2,-2)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Oblique Astigmatism',value))
        self.pars['AbsPosEdit(2,0)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Defocus',value))
        self.pars['AbsPosEdit(2,2)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Vertical Astigmatism',value))
        self.pars['AbsPosEdit(3,-3)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Vertical Trefoil',value))
        self.pars['AbsPosEdit(3,-1)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Vertical Coma',value))
        self.pars['AbsPosEdit(3,1)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Horizontal Coma',value))
        self.pars['AbsPosEdit(3,3)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Horizontal Trefoil',value))
        self.pars['AbsPosEdit(4,0)' + 'Left'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Left','Spherical',value))
        ######################
        self.pars['AbsPosEdit(0,0)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Piston',value))
        self.pars['AbsPosEdit(1,-1)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Y-tilt',value))
        self.pars['AbsPosEdit(1,1)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','X-tilt',value))
        self.pars['AbsPosEdit(2,-2)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Oblique Astigmatism',value))
        self.pars['AbsPosEdit(2,0)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Defocus',value))
        self.pars['AbsPosEdit(2,2)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Vertical Astigmatism',value))
        self.pars['AbsPosEdit(3,-3)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Vertical Trefoil',value))
        self.pars['AbsPosEdit(3,-1)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Vertical Coma',value))
        self.pars['AbsPosEdit(3,1)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Horizontal Coma',value))
        self.pars['AbsPosEdit(3,3)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Horizontal Trefoil',value))
        self.pars['AbsPosEdit(4,0)' + 'Right'].valueChanged.connect(lambda value: self.sigZernParamChanged.emit('Zernike SLM Parameters','Right','Spherical',value))



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
