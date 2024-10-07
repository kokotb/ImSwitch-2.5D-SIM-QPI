import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtWidgets
from pyqtgraph.parametertree import ParameterTree
from imswitch.imcontrol.view import guitools
from imswitch.imcontrol.view.widgets.basewidgets import NapariHybridWidget

import napari
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QCheckBox, QLabel, QLineEdit, QFrame)


class SIMWidget(NapariHybridWidget):
    """ Widget containing sim interface. """


    sigSIMMonitorChanged = QtCore.Signal(int)  # (monitor)
    sigPatternID = QtCore.Signal(int)  # (display pattern id)
    # sigCalibrateToggled = QtCore.Signal(bool)
    sigSIMAcqToggled = QtCore.Signal(bool)
    sigSIMParamChanged = QtCore.Signal(str, str, str) # (value)
    sigUserDirInfoChanged = QtCore.Signal(str, str, str)
    # sigTilingInfoChanged = QtCore.Signal(str, str, str)
    sigROInfoChanged = QtCore.Signal(str, str, str)
    def __post_init__(self):
        #super().__init__(*args, **kwargs)

        # Main GUI 
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        # Side TabView
        self.tabView = QTabWidget()
        self.layout.addWidget(self.tabView, 0)

        # Add tabs
        # self.manual_control_tab = self.create_manual_control_tab()
        # self.tabView.addTab(self.manual_control_tab, "Manual Control")
        
        self.experiment_tab = self.create_experiment_tab()
        self.layer_control_tab = self.create_layer_control_tab()
        self.tabView.addTab(self.experiment_tab, "Experiment")
        self.tabView.addTab(self.layer_control_tab, "Layer Control")

        
        # self.timelapse_settings_tab = self.create_timelapse_settings_tab()
        # self.tabView.addTab(self.timelapse_settings_tab, "TimeLapse Settings")
        
        # self.zstack_settings_tab = self.create_zstack_settings_tab()
        # self.tabView.addTab(self.zstack_settings_tab, "Z-stack Settings")
        
        #BKEDIT econstruction_parameters_tab ported to create_experiment_tab()
        # self.reconstruction_parameters_tab = self.create_reconstruction_parameters_tab() 
        # self.tabView.addTab(self.reconstruction_parameters_tab, "Reconstruction Parameters")
        
        # self.calibrateButton.toggled.connect(self.sigCalibrateToggled)
        self.params = [
            "ReconWL1", "ReconWL2", "ReconWL3","NA", "Pixelsize", "Alpha", "Beta", "w","eta","n","Magnification"
        ]
        # Set layer properties
        self.layer = None
        self.laserColormaps = {'488':'blue','561':'green','640':'red'}
        self.micronsPerPixel = [.1233,.1233]
        self.connectSIMSharedAttrSigs(self.params)
        self.connectUserDirSharedAttrSigs()

        
    def getImage(self):
        if self.layer is not None:
            return self.img.image
        
    def setSIMImage(self, im, name):
        if self.layer is None or name not in self.viewer.layers:
            colormap = self.laserColormaps[name[:3]]
            self.layer = self.viewer.add_image(im, rgb=False, name=name, colormap=colormap, blending='additive')
            self.viewer.layers[name].scale = [x/2 for x in self.micronsPerPixel] #SIM image recon result is 2x size of WF and raw images. So scale needs to be reduced by half.
            self.viewer.layers[name].contrast_limits_range = [0,4095]
        else:
            self.viewer.layers[name].data = im
    
    def setRawImage(self, im, name):
        if self.layer is None or name not in self.viewer.layers:
            colormap = 'grayclip'
            self.layer = self.viewer.add_image(im, rgb=False, name=name, colormap=colormap, blending='additive')
            self.viewer.layers[name].scale = self.micronsPerPixel
            self.viewer.layers[name].contrast_limits_range = [0,4095]
            self.viewer.layers[name].contrast_limits = (0,4095)
            self.viewer.scale_bar.unit = 'um'
            self.viewer.scale_bar.visible = True
            
            

        else:
            self.viewer.layers[name].data = im
            

    def setWFImage(self, im, name):
        if self.layer is None or name not in self.viewer.layers:
            colormap = self.laserColormaps[name[:3]]
            self.layer = self.viewer.add_image(im, rgb=False, name=name, colormap=colormap, blending='additive')
            self.viewer.layers[name].scale = self.micronsPerPixel
            self.viewer.layers[name].contrast_limits_range = [0,4095]
            self.viewer.layers[name]._keep_auto_contrast = True

        else:
            self.viewer.layers[name].data = im

    def contrastReconFunc(self):
            
        layerList = self.getAllLayerNames()
        reconLayerList = [x for x in layerList if 'Recon' in x]
        # if reconLayerList == []:
        #     return
        for name in reconLayerList:
            initMaxLimit = np.max(self.viewer.layers[name].data_raw)
            self.viewer.layers[name].contrast_limits = [0,initMaxLimit]

    def colormapToggleReconFunc(self, channel):
        self.laserColormaps
        layerList = self.getAllLayerNames()
        reconLayerList = [x for x in layerList if 'Recon' in x]
        if channel not in reconLayerList:
            return
        currentColor = self.viewer.layers[channel].colormap.name
        if currentColor == 'grayclip':
            self.viewer.layers[channel].colormap = self.laserColormaps[channel[:3]]
        else:
            self.viewer.layers[channel].colormap = 'grayclip'




    def contrastRawsFSFunc(self):
        layerList = self.getAllLayerNames()
        rawLayerList = [x for x in layerList if 'Raw' in x]
        for name in rawLayerList:
            self.viewer.layers[name].contrast_limits = [0,4095]

    def contrastRawsFunc(self):
        layerList = self.getAllLayerNames()
        rawLayerList = [x for x in layerList if 'Raw' in x]
        for name in rawLayerList:
            initMaxLimit = np.max(self.viewer.layers[name].data_raw)
            self.viewer.layers[name].contrast_limits = [0,initMaxLimit]

    def hideShowAllLayersFunc(self):
        layerList = self.getAllLayerNames()
        if True in [self.viewer.layers[name].visible for name in layerList]:
            for name in layerList:
                self.viewer.layers[name].visible = False
        else:
            for name in layerList:
                self.viewer.layers[name].visible = True
        
    def hideShowLayerByType(self, layerType):
        layerList = self.getAllLayerNames()
        layerListByType = [x for x in layerList if layerType in x]

        if True in [self.viewer.layers[name].visible for name in layerListByType]:
            for name in layerListByType:
                self.viewer.layers[name].visible = False
        else:
            for name in layerListByType:
                self.viewer.layers[name].visible = True

    def hideShowLayerByChannel(self,channel):
        layerList = self.getAllLayerNames()
        layerListByChannel = [x for x in layerList if channel in x]

        if True in [self.viewer.layers[name].visible for name in layerListByChannel]:
            for name in layerListByChannel:
                self.viewer.layers[name].visible = False
        else:
            for name in layerListByChannel:
                self.viewer.layers[name].visible = True


    def getAllLayerNames(self):
        layerList = []
        for i in range(len(self.viewer.layers)):
            layerList.append(self.viewer.layers[i].name)
        return layerList

    def create_layer_control_tab(self):

        
        
        tab = QWidget()
        parentLayout = QVBoxLayout()
        self.hideShowAllLayers = QPushButton("Hide/Show All Layers")

        #Layer contrast buttons grouped together
        self.contrastLabel = QtWidgets.QLabel('Layer Contrasts')
        self.contrastLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.contrastRecon = QPushButton("Recons Once")
        self.contrastFSRaw = QPushButton("Raws Full Scale")
        self.contrastRaw = QPushButton("Raws Once")
        self.myframe = QFrame()
        self.myframe.setFrameShape(QFrame.StyledPanel)
        self.myframe.setFrameShadow(QFrame.Plain)
        self.myframe.setLineWidth(5)

        layersContrast = QVBoxLayout(self.myframe)
        layersContrast.addWidget(self.contrastRecon)
        layersContrast.addWidget(self.contrastFSRaw)
        layersContrast.addWidget(self.contrastRaw)
        layersContrastBoxed = QVBoxLayout()
        layersContrastBoxed.addWidget(self.myframe)

        # Recon colormap toggle buttons boxed by channel.
        self.colormapToggleLabel = QtWidgets.QLabel('Toggle Recon Colormaps')
        self.colormapToggleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.colormapToggle488 = QPushButton("488")
        self.colormapToggle561 = QPushButton("561")
        self.colormapToggle640 = QPushButton("640")
        self.myframe = QFrame()
        self.myframe.setFrameShape(QFrame.StyledPanel)
        self.myframe.setFrameShadow(QFrame.Plain)
        self.myframe.setLineWidth(5)
        layersColormapToggle = QVBoxLayout(self.myframe)
        layersColormapToggle.addWidget(self.colormapToggle488)
        layersColormapToggle.addWidget(self.colormapToggle561)
        layersColormapToggle.addWidget(self.colormapToggle640)
        layersColormapToggleBoxed = QVBoxLayout()
        layersColormapToggleBoxed.addWidget(self.myframe)

        # Hide/show buttons boxed by channel.
        self.hideShowChanLabel = QtWidgets.QLabel('Hide/Show by Channel')
        self.hideShowChanLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.hideShow488Layers = QPushButton("488")
        self.hideShow561Layers = QPushButton("561")
        self.hideShow640Layers = QPushButton("640")
        self.myframe = QFrame()
        self.myframe.setFrameShape(QFrame.StyledPanel)
        self.myframe.setFrameShadow(QFrame.Plain)
        self.myframe.setLineWidth(5)
        layersHideShowChannel = QVBoxLayout(self.myframe)
        layersHideShowChannel.addWidget(self.hideShow488Layers)
        layersHideShowChannel.addWidget(self.hideShow561Layers)
        layersHideShowChannel.addWidget(self.hideShow640Layers)
        layersHideShowChannelBoxed = QVBoxLayout()
        layersHideShowChannelBoxed.addWidget(self.myframe)

        
        # Hide/show buttons boxed by type.
        self.hideShowTypeLabel = QtWidgets.QLabel('Hide/Show by Type')
        self.hideShowTypeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.hideShowReconLayers = QPushButton("Recons")
        self.hideShowWFLayers = QPushButton("Widefields")
        self.hideShowRawLayers = QPushButton("Raws")
        self.myframe = QFrame()
        self.myframe.setFrameShape(QFrame.StyledPanel)
        self.myframe.setFrameShadow(QFrame.Plain)
        self.myframe.setLineWidth(5)
        layersHideShowType = QVBoxLayout(self.myframe)
        layersHideShowType.addWidget(self.hideShowReconLayers)
        layersHideShowType.addWidget(self.hideShowWFLayers)
        layersHideShowType.addWidget(self.hideShowRawLayers)
        layersHideShowTypeBoxed = QVBoxLayout()
        layersHideShowTypeBoxed.addWidget(self.myframe)


        #Add elements in order you want them to appear
        parentLayout.addWidget(self.contrastLabel)
        parentLayout.addLayout(layersContrastBoxed)
        parentLayout.addWidget(self.colormapToggleLabel)
        parentLayout.addLayout(layersColormapToggleBoxed)
        parentLayout.addWidget(self.hideShowChanLabel)
        parentLayout.addLayout(layersHideShowChannelBoxed)
        parentLayout.addWidget(self.hideShowTypeLabel)
        parentLayout.addLayout(layersHideShowTypeBoxed)
        parentLayout.addWidget(self.hideShowAllLayers)

        #Connect all buttons to functions. Lambda syntax used when a argument is needed to be passed with the function.
        self.contrastRecon.clicked.connect(self.contrastReconFunc)
        self.contrastFSRaw.clicked.connect(self.contrastRawsFSFunc)
        self.contrastRaw.clicked.connect(self.contrastRawsFunc)
        self.colormapToggle488.clicked.connect(lambda: self.colormapToggleReconFunc('488 Recon'))
        self.colormapToggle561.clicked.connect(lambda: self.colormapToggleReconFunc('561 Recon'))
        self.colormapToggle640.clicked.connect(lambda: self.colormapToggleReconFunc('640 Recon'))
        self.hideShowReconLayers.clicked.connect(lambda: self.hideShowLayerByType('Recon'))
        self.hideShowWFLayers.clicked.connect(lambda: self.hideShowLayerByType('WF'))
        self.hideShowRawLayers.clicked.connect(lambda: self.hideShowLayerByType('Raw'))
        self.hideShow488Layers.clicked.connect(lambda: self.hideShowLayerByChannel('488'))
        self.hideShow561Layers.clicked.connect(lambda: self.hideShowLayerByChannel('561'))
        self.hideShow640Layers.clicked.connect(lambda: self.hideShowLayerByChannel('640'))
        self.hideShowAllLayers.clicked.connect(self.hideShowAllLayersFunc)

        tab.setLayout(parentLayout)
        return tab




    def create_experiment_tab(self):
        tab = QWidget()
        wholeTabVertLayout = QVBoxLayout()
        tabBottomVertLayout1 = QVBoxLayout()
        tabBottomVertLayout2 = QVBoxLayout()
        tabBottomHorLayout = QHBoxLayout()
    
        # Start/Stop/Calibrate buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setCheckable(True)
        self.calibrateButton = QPushButton("Calibrate")
        self.saveOneSetButton = QPushButton("Snapshot")
        button_layout = QtWidgets.QGridLayout()
        button_layout.addWidget(self.start_button,0,0)
        button_layout.addWidget(self.stop_button,0,1)
        button_layout.addWidget(self.calibrateButton,1,0)
        button_layout.addWidget(self.saveOneSetButton,1,1)
        wholeTabVertLayout.addLayout(button_layout)
    
        # Checkbox options
        self.checkbox_reconstruction = QCheckBox('Live Reconstruction')
        self.checkbox_reconstruction.setChecked(True)
        self.checkbox_record_reconstruction = QCheckBox('Save Reconstruction')
        self.checkbox_record_raw = QCheckBox('Save Raw Data')
        self.checkbox_record_WF = QCheckBox('Save Widefield')
        self.checkbox_logging = QCheckBox("Logging")
        # self.checkbox_tilepreview =  QCheckBox("Tile Preview")
        checkbox_layout = QtWidgets.QVBoxLayout()
        checkbox_layout.addWidget(self.checkbox_reconstruction)
        checkbox_layout.addWidget(self.checkbox_record_reconstruction)
        checkbox_layout.addWidget(self.checkbox_record_raw)
        checkbox_layout.addWidget(self.checkbox_record_WF)
        checkbox_layout.addWidget(self.checkbox_logging)
        # checkbox_layout.addWidget(self.checkbox_tilepreview)
        tabBottomVertLayout1.addLayout(checkbox_layout)
        
        #RO selection on 4DD sLM
        self.roSelectLayout = QtWidgets.QHBoxLayout()
        self.roSelectLabel = QtWidgets.QLabel('Running Orders:')
        self.roSelectList = QtWidgets.QComboBox()
        self.roSelectList.currentTextChanged.connect(lambda value: self.sigROInfoChanged.emit('SIM SLM',"SLM Running Order", value))
        self.roSelectLayout.addWidget(self.roSelectLabel)
        self.roSelectLayout.addWidget(self.roSelectList)
        tabBottomVertLayout1.addLayout(self.roSelectLayout)
    
    


        # Save folder
        parameters2_layout = QtWidgets.QGridLayout()
        self.path_label = QLabel("Root Path")
        self.path_edit = QLineEdit("")
        self.user_label = QLabel("User Name")
        self.user_edit = QLineEdit("")
        self.expt_label = QLabel("Experiment Name")
        self.expt_edit = QLineEdit("")
        self.openFolderButton = guitools.BetterPushButton('Open')
        row = 0
        parameters2_layout.addWidget(self.user_label, row, 0)
        parameters2_layout.addWidget(self.user_edit, row, 1)
        parameters2_layout.addWidget(self.expt_label, row+1, 0)
        parameters2_layout.addWidget(self.expt_edit, row+1, 1)
        parameters2_layout.addWidget(self.path_label, row+2, 0)
        parameters2_layout.addWidget(self.path_edit, row+2, 1)        
        parameters2_layout.addWidget(self.openFolderButton, row + 3, 0, 1, 2)
        tabBottomVertLayout1.addLayout(parameters2_layout)
        
        # FIXME: delete after development
        # self.start_button_test = QPushButton("Test_long-text-test")
        # button_layout_test = QtWidgets.QGridLayout()
        # button_layout_test.addWidget(self.start_button_test,0,0)
        # tabBottomVertLayout2.addLayout(button_layout_test)
        reconstruction_parameters_tab = self.create_reconstruction_parameters()
        tabBottomVertLayout2.addLayout(reconstruction_parameters_tab)
        
        tabBottomHorLayout.addLayout(tabBottomVertLayout2)
        tabBottomHorLayout.addLayout(tabBottomVertLayout1)
        wholeTabVertLayout.addLayout(tabBottomHorLayout)

        self.start_button.toggled.connect(self.sigSIMAcqToggled)
        # self.stop_button.toggled.connect(self._commChannel.sigStopSim.emit())
        


        tab.setLayout(wholeTabVertLayout)
        return tab
    


    
    def addROName(self, roIndex, roName):
        self.roSelectList.addItem(f'{roName}', roIndex)

    def getSelectedRO(self):
        selectedRO = str(self.roSelectList.currentIndex())
        roIndex = selectedRO.split(":")
        roIndex = int(roIndex[0])
        return roIndex
    
    def getUserName(self):
        return self.user_edit.text()
    
    def getExptName(self):
        return self.expt_edit.text()

    def setSelectedRO(self, currentROIndex):
        self.roSelectList.setCurrentIndex(currentROIndex)

    def getReconCheckState(self):
        reconState = self.checkbox_reconstruction.checkState()
        if reconState == 0:
            reconStateBool = False
        elif reconState == 2:
            reconStateBool = True
        return reconStateBool

    def setUserDirInfo(self, saveDir):
        self.path_edit.setText(saveDir)
        self.user_edit.setPlaceholderText('Username')
        self.expt_edit.setPlaceholderText('Experiment Name')
        self.sigUserDirInfoChanged.emit('User Dir Info','User Name',"username")
        self.sigUserDirInfoChanged.emit('User Dir Info','Experiment Name',"exptname")



    def create_reconstruction_parameters(self):
        # tab = QWidget() #BKEDIT
        layout = QVBoxLayout()
        # print(self.setupInfoDict)

        # create widget per label
        self.ReconWL1_label = QLabel("")
        self.ReconWL1_textedit = QLineEdit("")
        self.ReconWL2_label = QLabel("")
        self.ReconWL2_textedit = QLineEdit("")
        self.ReconWL3_label = QLabel("")
        self.ReconWL3_textedit = QLineEdit("")
        self.NA_label = QLabel("")
        self.NA_textedit = QLineEdit("")
        self.pixelsize_label = QLabel("")
        self.pixelsize_textedit = QLineEdit("")
        self.alpha_label = QLabel("")
        self.alpha_textedit = QLineEdit("")
        self.beta_label = QLabel("")
        self.beta_textedit = QLineEdit("")
        self.w_label = QLabel("")
        self.w_textedit = QLineEdit("")
        self.eta_label = QLabel("")
        self.eta_textedit = QLineEdit("")
        self.n_label = QLabel("")
        self.n_textedit = QLineEdit("")
        self.magnification_label = QLabel("")
        self.magnification_textedit = QLineEdit("")
        row_layout_1 = QHBoxLayout()
        row_layout_1.addWidget(self.ReconWL1_label)
        row_layout_1.addWidget(self.ReconWL1_textedit)
        row_layout_2 = QHBoxLayout()
        row_layout_2.addWidget(self.ReconWL2_label)
        row_layout_2.addWidget(self.ReconWL2_textedit)
        row_layout_3 = QHBoxLayout()
        row_layout_3.addWidget(self.ReconWL3_label)
        row_layout_3.addWidget(self.ReconWL3_textedit)
        row_layout_4 = QHBoxLayout()
        row_layout_4.addWidget(self.NA_label)
        row_layout_4.addWidget(self.NA_textedit)
        row_layout_5 = QHBoxLayout()
        row_layout_5.addWidget(self.pixelsize_label)
        row_layout_5.addWidget(self.pixelsize_textedit)
        row_layout_6 = QHBoxLayout()
        row_layout_6.addWidget(self.alpha_label)
        row_layout_6.addWidget(self.alpha_textedit)
        row_layout_7 = QHBoxLayout()
        row_layout_7.addWidget(self.beta_label)
        row_layout_7.addWidget(self.beta_textedit)
        row_layout_8 = QHBoxLayout()
        row_layout_8.addWidget(self.w_label)
        row_layout_8.addWidget(self.w_textedit)
        row_layout_9 = QHBoxLayout()
        row_layout_9.addWidget(self.eta_label)
        row_layout_9.addWidget(self.eta_textedit)
        row_layout_10 = QHBoxLayout()
        row_layout_10.addWidget(self.n_label)
        row_layout_10.addWidget(self.n_textedit)
        row_layout_11 = QHBoxLayout()
        row_layout_11.addWidget(self.magnification_label)
        row_layout_11.addWidget(self.magnification_textedit)
        
        layout.addLayout(row_layout_1)
        layout.addLayout(row_layout_2)
        layout.addLayout(row_layout_3)
        layout.addLayout(row_layout_4)
        layout.addLayout(row_layout_5)
        layout.addLayout(row_layout_6)
        layout.addLayout(row_layout_7)
        layout.addLayout(row_layout_8)
        layout.addLayout(row_layout_9)
        layout.addLayout(row_layout_10)
        layout.addLayout(row_layout_11)
        
        

        # tab.setLayout(layout) #BKedit
        # return tab
        return layout

        
    def setSIMWidgetFromConfig(self,setupInfoDict):


        self.ReconWL1_label.setText(self.params[0])
        self.ReconWL1_textedit.setText(str(setupInfoDict[self.params[0]]))
        self.ReconWL2_label.setText(self.params[1])
        self.ReconWL2_textedit.setText(str(setupInfoDict[self.params[1]]))
        self.ReconWL3_label.setText(self.params[2])
        self.ReconWL3_textedit.setText(str(setupInfoDict[self.params[2]]))
        self.NA_label.setText(self.params[3])
        self.NA_textedit.setText(str(setupInfoDict[self.params[3]]))
        self.pixelsize_label.setText(self.params[4])
        self.pixelsize_textedit.setText(str(setupInfoDict[self.params[4]]))
        self.alpha_label.setText(self.params[5])
        self.alpha_textedit.setText(str(setupInfoDict[self.params[5]]))
        self.beta_label.setText(self.params[6])
        self.beta_textedit.setText(str(setupInfoDict[self.params[6]]))
        self.w_label.setText(self.params[7])
        self.w_textedit.setText(str(setupInfoDict[self.params[7]]))
        self.eta_label.setText(self.params[8])
        self.eta_textedit.setText(str(setupInfoDict[self.params[8]]))
        self.n_label.setText(self.params[9])
        self.n_textedit.setText(str(setupInfoDict[self.params[9]]))
        self.magnification_label.setText(self.params[10])
        self.magnification_textedit.setText(str(setupInfoDict[self.params[10]]))    

    def connectSIMSharedAttrSigs(self, params):
        self.ReconWL1_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[0],value))
        self.ReconWL2_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[1],value))
        self.ReconWL3_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[2],value))
        self.NA_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[3],value))
        self.pixelsize_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[4],value))
        self.alpha_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[5],value))
        self.beta_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[6],value))
        self.w_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[7],value))
        self.eta_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[8],value))
        self.n_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[9],value))
        self.magnification_textedit.textChanged.connect(lambda value: self.sigSIMParamChanged.emit('SIM Parameters',params[10],value))

        #editingFinished seems to be a better method, but cannot get to work correctly.
        # self.ReconWL1_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[0],self.ReconWL1_textedit.text()))
        # self.ReconWL2_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[1],self.ReconWL2_textedit.text()))
        # self.ReconWL3_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[2],self.ReconWL3_textedit.text()))
        # self.NA_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[3],self.NA_textedit.text()))
        # self.pixelsize_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[4],self.pixelsize_textedit.text()))
        # self.alpha_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[5],self.alpha_textedit.text()))
        # self.beta_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[6],self.beta_textedit.text()))
        # self.w_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[7],self.w_textedit.text()))
        # self.eta_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[8],self.eta_textedit.text()))
        # self.n_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[9],self.n_textedit.text()))
        # self.magnification_textedit.editingFinished.connect(self.sigSIMParamChanged.emit('SIM Parameters',params[10],self.magnification_textedit.text()))

    def connectUserDirSharedAttrSigs(self):
        self.path_edit.textChanged.connect(lambda value: self.sigUserDirInfoChanged.emit('User Dir Info','Working Directory',value))
        self.user_edit.textChanged.connect(lambda value: self.sigUserDirInfoChanged.emit('User Dir Info','Experiment Name',value))
        self.expt_edit.textChanged.connect(lambda value: self.sigUserDirInfoChanged.emit('User Dir Info','User Name',value))


    def getZStackParameters(self):
        return (np.float32(self.zmin_textedit.text()), np.float32(self.zmax_textedit.text()), np.float32(self.nsteps_textedit.text()))
    
    def getTimelapseParameters(self):
        return (np.float32(self.period_textedit.text()), np.float32(self.frames_textedit.text()))
    
    def getRecFolder(self):
        return self.path_edit.text()
    


# Copyright (C) 2020-2023 ImSwitch developers
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
