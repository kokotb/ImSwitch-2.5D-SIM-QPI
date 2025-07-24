from ..basecontrollers import ImConWidgetController
import numpy as np
from imswitch.imcommon.model import initLogger
import os
import cv2
import tifffile as tif
import threading
import matplotlib.pyplot as plt
import time
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

try:
    from scipy.optimize import curve_fit
except ImportError:
    print("Unable to import curve_fit from scipy.optimize.")

class AutofocusController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        # self._widget.sigAutofocusInfoChanged.connect(self.valueChanged)
        # self._widget.checkbox_Autofocus.stateChanged.connect(self.testFunc)
        self._widget.initValues()
        # self._commChannel.sigToggleAutofocus.connect(self.toggleAutofocusCheckbox)
        # self._commChannel.sigGetAndScoreAF.connect(self.getAndScoreOneLive)
        # self._widget.openPreview.clicked.connect(self.openSetAFWindowThread)
        self._widget.openPreview.clicked.connect(self.openSetAFWindow)
        self._widget.registerPlane.clicked.connect(self.registerCurrentPlane)
        self._widget.clearRegPlane.clicked.connect(self.clearRegisteredPlane)
        self._widget.autofocusModule.clicked.connect(self.autofocusModuleToggle)
        self._widget.AFWindow.calCurve.clicked.connect(self.runCalCurveThread)
        self._widget.AFWindow.acqImgButton.clicked.connect(self.getOneFrameToSet)
        self._widget.AFWindow.resetEstimates.clicked.connect(self.resetEstimates)
        # self._widget.registerPlane.clicked.connect(self.onLED)
        # self._widget.clearRegPlane.clicked.connect(self.offLED)
        self._manager = self._master.autofocusManager
        self.zPositioner = self._master.positionersManager._subManagers['Z']
        self.AFCam = self._master.detectorsManager._subManagers['AF Cam']
        self.calCurveImgs = []
        # self._commChannel.calCurveFit = False
        # self.initRegScore = None
        self.storeInitEstimate()
        

        self.threshold = self._manager.threshold #pixel value threshold for AF image

    def storeInitEstimate(self):
        self.guess_x = self._manager.guess_x    # Guesses for fits Background, Centre, Width, Amplitude
        self.guess_y = self._manager.guess_y


    def resetEstimates(self):
        self.guess_x = self._manager.init_guess_x[:]
        self.guess_y = self._manager.init_guess_y[:]
        self._logger.info('Initial fit guesses reset.')

    def clearRegisteredPlane(self):
        self._commChannel.initRegScore = None
        self.offLED()

    def autofocusModuleToggle(self, state):
        self._commChannel.autofocusEnabled = state
        self._widget.toggleEnabled(state)
        if state == False:
            self.offLED()
        if (state == True) and (self._commChannel.initRegScore != None):
            self.onLED()


    def onLED(self):
        self._widget.led.turn_on()

    def offLED(self):
        self._widget.led.turn_off()

    def registerCurrentPlane(self):
        score = self.getAndScoreOne()
        self._commChannel.initRegScore = score
        print(f"Plane registered with score of {self._commChannel.initRegScore:.2f}")
        self.onLED()

    # def openSetAFWindowThread(self):
    #     threading.Thread(target=self.openSetAFWindow(), args=(), daemon=True).start()

    def openSetAFWindow(self):
        self._widget.AFWindow.show()
        self._widget.AFWindow.raise_()
        self.getOneFrameToSet()


    def getOneFrameToSet(self):
        img = self.AFCam.grabFrameOnly()
        pixmapImg = self._widget.AFWindow.convert_ndarray_to_qpixmap(img)
        self._widget.AFWindow.embeddedImage.setPixmap(pixmapImg)
        return img

    def getOneFrame(self): 
        img = self.AFCam.grabFrameOnly()
        return img
    
    def runCalCurveThread(self):
        threading.Thread(target=self.runCalCurve, args=(), daemon=True).start()

    def runCalCurve(self):
        zList, currentZ = self.calcZRange()
        # zList = zList.reverse()
        if len(self.calCurveImgs) != 0:
            self.calCurveImgs = []
        for count, _ in enumerate(zList):
            # filename = f"{count:03}.tif"
            self.zPositioner.setPosition(zList[count], 'Z')
            time.sleep(0.01)
            img = self.getOneFrame()
            # self.saveImageInBackground(img, path, filename)
            self.calCurveImgs.append(img)
        self.zPositioner.setPosition(currentZ, 'Z')
        self.scoreCalCurveImgs(zList)

    def getAndScoreOne(self):
        assert self._commChannel.calCurveFit, "Calibration curve not set."
        img = self.getOneFrame()
        score = self.scoreOneImg(img)
        return score

    def scoreOneLive(self, img):
        assert self._commChannel.calCurveFit, "Calibration curve not set."
        score = self.scoreOneImg(img)
        zPred = self.getYfromX(score)
        self._commChannel.currentRegScore = score
        self._commChannel.currentPredZ = zPred
        return score, zPred
    
    def setZPosition(self, z):
        self.zPositioner.setPosition(z, 'Z')

    def getXfromY(self, y):
        x = self._manager.getXromY(y)
        return x

    def getYfromX(self, x):
        y = self._manager.getYfromX(x)
        return y
    
    def scoreOneImg(self, im):
        score = self._manager.scoreOneImg(im)
        return score
    
            


    def scoreCalCurveImgs(self, zList):

        Range = len(zList)  	# Number of files
        # zval = 0.8    	# Step size in microns
        # lowZ = 204

        # Define the model function. In our case, a 1D Gaussian.
        def Gaussian1D(xdata, i0, x0, sX, amp):
            x = xdata
            x0 = float(x0)
            eq = i0+amp*np.exp(-((x-x0)**2/2/sX**2))
            return eq





        x_c = []
        x_sigma = []
        y_sigma = []
        i_values = []

        # To read the acquired images and apply the Gaussian fitting
        for i in range(len(self.calCurveImgs)):
            i_values.append(i)
            #Reading the frames
            im = self.calCurveImgs[i]
            # img = cv2.imread(stacks,-1)
            # im = np.asarray(img).astype(float)
            im = im-np.mean(im)/2	# Remove background
            im[im<self.threshold] = 0			# Threshold

            # plt.imshow(im)

        
            # 1D Gaussian
            h1, w1 = im.shape
            x = np.arange(w1)
            y = np.arange(h1)
            
            # Do x fit
            popt, pcov = curve_fit(Gaussian1D, x, np.mean(im,axis=0), p0=self.guess_x, maxfev = 50000)
            x0 = popt[1]
            sx = popt[2]  
            self.guess_x.clear()
            self.guess_x.append(popt)
            # Do y fit
            popt, pcov = curve_fit(Gaussian1D, y, np.mean(im,axis=1), p0=self.guess_y, maxfev = 50000)
            y0 = popt[1]
            sy = popt[2]
            
            # Replaces initial guess with final guess
            self.guess_y.clear()
            self.guess_y.append(popt)
        
            x_sigma.append(abs(sx))
            # print(x_sigma)
            y_sigma.append(abs(sy))
            x_c.append(popt[1])
            # plt.plot((x0,x0+sx),(y0,y0))
            # plt.plot((x0,x0),(y0,y0+sy))
            # plt.imshow(im)
            # plt.show()
            
        # This is just to set the x-axis of the graph to the axial values
        # StepSize = zval
        i_values = np.array(i_values)
        z_values = zList
        comboData = np.subtract(x_sigma,y_sigma)
        comboDataReshape = comboData.reshape(-1, 1)
        comboDataReshape1D = [j[0] for j in comboDataReshape]

        model = LinearRegression()
        model.fit(comboDataReshape, zList)
        y_pred = model.predict(comboDataReshape)
        self.x_slp = model.coef_[0]
        self._manager.x_slp = self.x_slp
        self.y_int = model.intercept_
        self._manager.y_int = self.y_int
        self.r2 = r2_score(zList, y_pred)
        self._widget.AFWindow.sigUpdateCalibChart.emit(z_values, x_sigma, y_sigma, comboDataReshape1D)
        if self.r2 >= 0.99:
            self._logger.info(f'Calibration curve successfully set.\nSlope = {self.x_slp}\nIntercept = {self.y_int}\nr^2 = {self.r2}')
            self._commChannel.calCurveFit = True
            self._widget.AFWindow.ccSlopeVal.setText(str(round(self.x_slp,3)))
            self._widget.AFWindow.ccIntVal.setText(str(round(self.y_int,2)))
            self._widget.AFWindow.ccR2Val.setText(str(round(self.r2,4)))
            sensitivity = -1 / self.x_slp
            self._widget.AFWindow.ccSensVal.setText(f'{round(sensitivity,2)} pixels/um')
        else:
            self._logger.warning(f"Failed to fit calibration curve to data.\nSlope = {self.x_slp:.3f}\nIntercept = {self.y_int:.2f}\nr^2 = {self.r2:.4f}")
            self._commChannel.calCurveFit = False


        # Save calibration data


        # plt.plot(x_sigma, z_values,  'b8', markersize=2, label="σx")
        # plt.plot(y_sigma, z_values, 'r8', markersize=2, label="σy")
        # plt.plot(np.subtract(x_sigma,y_sigma), z_values, '--k', markersize=2, label="σx - σy")
        # plt.grid(True)
        # plt.ylabel("z-Position (µm)")
        # plt.xlabel("Pixels")
        # plt.legend()
        # plt.show()
        # self.y_int, self.slp = self.estimate_coef(comboData, z_values)



    # def estimate_coef(self, x, y):
    #     # number of observations/points
    #     n = np.size(x)

    #     # mean of x and y vector
    #     m_x = np.mean(x)
    #     m_y = np.mean(y)

    #     # calculating cross-deviation and deviation about x
    #     SS_xy = np.sum(y*x) - n*m_y*m_x
    #     SS_xx = np.sum(x*x) - n*m_x*m_x
    #     # calculating regression coefficients
    #     b_1 = SS_xy / SS_xx
    #     b_0 = m_y - b_1*m_x

    #     return (b_0, b_1)
        

    def calcZRange(self):
        currentZ = self.zPositioner._position['Z']
        rangeVal = self._widget.calCurveRange.value()
        bottom = currentZ - rangeVal/2
        top = currentZ + rangeVal/2
        steps = 21
        zList = np.linspace(top, bottom, steps)
        return zList, currentZ


    
    def saveImageInBackground(self, image, path, filename):
        try:
            # self.folder = self._widget.getRecFolder()
            filename = os.path.join(path,filename) 
            image = np.array(image)
            tif.imwrite(filename, image, imagej=True)
            self._logger.debug("Saving AF image: " + filename)

        except  Exception as e:
            self._logger.error(e)
    

















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
