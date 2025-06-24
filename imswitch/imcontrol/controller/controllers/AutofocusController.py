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

class AutofocusController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        self.sharedAttrs = self._commChannel.sharedAttrs._data
        # self._widget.sigAutofocusInfoChanged.connect(self.valueChanged)
        # self._widget.checkbox_Autofocus.stateChanged.connect(self.testFunc)
        self._widget.initValues()
        # self._commChannel.sigToggleAutofocus.connect(self.toggleAutofocusCheckbox)
        self._widget.openPreview.clicked.connect(self.openSetAFWindowThread)
        self._widget.registerPlane.clicked.connect(self.registerCurrentPlane)
        self._widget.clearRegPlane.clicked.connect(self.clearRegisteredPlane)
        self._widget.AFWindow.roiReset.clicked.connect(self.resetROIOnCam)
        self._widget.AFWindow.roiSet.clicked.connect(self.setROIOnCam)
        self._widget.AFWindow.calCurve.clicked.connect(self.runCalCurve)
        self._widget.AFWindow.acqImgButton.clicked.connect(self.getOneFrameToSet)

        self.zPositioner = self._master.positionersManager._subManagers['Z']
        self.AFCam = self._master.detectorsManager._subManagers['AF Cam']
        self.calCurveImgs = []
        self.calCurveFit = False
        self.currentReg = None

    def clearRegisteredPlane(self):
        self.currentReg = None

    def registerCurrentPlane(self):
        score = self.getAndScoreOne()
        self.currentReg = score

    def resetROIOnCam(self):
        self.AFCam.setROI([0,0,1280,1024])
        self.getOneFrameToSet()

    def setROIOnCam(self):
        try:
            wantedROI = self._widget.AFWindow.embeddedImage.lastClick
            self.AFCam.setROI(wantedROI)
            self.getOneFrameToSet()
        except AttributeError:
            self._logger.warning("ROI has not yet been selected. Please click the center of desired ROI.")

    def openSetAFWindowThread(self):
        threading.Thread(target=self._widget.openSetAFWindow(), args=(), daemon=True).start()

    def getOneFrameToSet(self):
        img = self.AFCam.grabFrameOnly()
        pixmapImg = self._widget.AFWindow.convert_ndarray_to_qpixmap(img)
        self._widget.AFWindow.embeddedImage.setPixmap(pixmapImg)
        return img

    def getOneFrame(self): 
        img = self.AFCam.grabFrameOnly()
        return img
    
    def runCalCurve(self):
        zList, currentZ = self.calcZRange()
        # zList = zList.reverse()
        if len(self.calCurveImgs) != 0:
            self.calCurveImgs = []
        for count, z in enumerate(zList):
            # filename = f"{count:03}.tif"
            self.zPositioner.setPosition(zList[count], 'Z')
            time.sleep(0.01)
            img = self.getOneFrame()
            # self.saveImageInBackground(img, path, filename)
            self.calCurveImgs.append(img)
        self.zPositioner.setPosition(currentZ, 'Z')
        print('AF stack saved.')
        self.scoreCalCurveImgs(zList)

    def getAndScoreOne(self):
        assert self.calCurveFit, "Calibration curve not set."
        img = self.getOneFrame()
        # currentZ = self.zPositioner._position['Z']
        score = self.scoreOneImg(img)
        zPred = self.getYfromX(score)
        return score
    
    def setZPosition(self, z):
        self.zPositioner.setPosition(z, 'Z')

    # def regPlaneAF(self):
    #     pass

    def getXfromY(self, y):
        if self.calCurveFit:
            x = (y-self.y_int)/self.x_slp
        else:
            self._logger.warning('Calibration not yet set successfully.')
        return x

    def getYfromX(self, x):
        if self.calCurveFit:
            y = (self.x_slp*x) + self.y_int
        else:
            self._logger.warning('Calibration not yet set successfully.')
        return y
    
    def scoreOneImg(self, im):
        # Define the model function. In our case, a 1D Gaussian.
        def Gaussian1D(xdata, i0, x0, sX, amp):
            x = xdata
            x0 = float(x0)
            eq = i0+amp*np.exp(-((x-x0)**2/2/sX**2))
            return eq

        try:
            from scipy.optimize import curve_fit
        except ImportError:
            print("Unable to import curve_fit from scipy.optimize.")


        init_guess_x = [0,80,10,62]	# Guesses for fits Background, Centre, Width, Amplitude
        init_guess_y = [0,80,10,31]	# Guesses for fits
        x_sigma = []
        y_sigma = []


        # To read the acquired images and apply the Gaussian fitting

        #Reading the frames
        # img = cv2.imread(stacks,-1)
        # im = np.asarray(img).astype(float)
        im = im-np.mean(im)/2	# Remove background
        im[im<10] = 0			# Threshold
    
        # 1D Gaussian
        h1, w1 = im.shape
        x = np.arange(w1)
        y = np.arange(h1)
        
        # Do x fit
        popt, pcov = curve_fit(Gaussian1D, x, np.mean(im,axis=0), p0=init_guess_x, maxfev = 50000)
        x0 = popt[1]
        sx = popt[2]
        init_guess_x.clear()
        init_guess_x.append(popt)
        # Do y fit
        popt, pcov = curve_fit(Gaussian1D, y, np.mean(im,axis=1), p0=init_guess_y, maxfev = 50000)
        y0 = popt[1]
        sy = popt[2]
        
        # Replaces initial guess with final guess
        init_guess_y.clear()
        init_guess_y.append(popt)
    
        x_sigma = sx
        y_sigma = sy
        score = x_sigma - y_sigma

        # x_c.append(popt[1])
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

        try:
            from scipy.optimize import curve_fit
        except ImportError:
            print("Unable to import curve_fit from scipy.optimize.")


        init_guess_x = [0,80,10,62]	# Guesses for fits Background, Centre, Width, Amplitude
        init_guess_y = [0,80,10,31]	# Guesses for fits
        x_c = []
        x_sigma = []
        y_sigma = []
        i_values = []

        # To read the acquired images and apply the Gaussian fitting
        for i in range(len(self.calCurveImgs)):
            i_values.append(i)
            print("Step " + str(i+1) + " of " + str(Range))
            #Reading the frames
            im = self.calCurveImgs[i]
            # img = cv2.imread(stacks,-1)
            # im = np.asarray(img).astype(float)
            im = im-np.mean(im)/2	# Remove background
            im[im<10] = 0			# Threshold
        
            # 1D Gaussian
            h1, w1 = im.shape
            x = np.arange(w1)
            y = np.arange(h1)
            
            # Do x fit
            popt, pcov = curve_fit(Gaussian1D, x, np.mean(im,axis=0), p0=init_guess_x, maxfev = 50000)
            x0 = popt[1]
            sx = popt[2]
            init_guess_x.clear()
            init_guess_x.append(popt)
            # Do y fit
            popt, pcov = curve_fit(Gaussian1D, y, np.mean(im,axis=1), p0=init_guess_y, maxfev = 50000)
            y0 = popt[1]
            sy = popt[2]
            
            # Replaces initial guess with final guess
            init_guess_y.clear()
            init_guess_y.append(popt)
        
            x_sigma.append(sx)
            y_sigma.append(sy)
            x_c.append(popt[1])
            
        # This is just to set the x-axis of the graph to the axial values
        # StepSize = zval
        i_values = np.array(i_values)
        z_values = zList
        comboData = np.subtract(x_sigma,y_sigma)
        comboDataReshape = comboData.reshape(-1, 1)

        model = LinearRegression()
        model.fit(comboDataReshape, zList)
        y_pred = model.predict(comboDataReshape)
        self.x_slp = model.coef_[0]
        self.y_int = model.intercept_
        self.r2 = r2_score(zList, y_pred)
        if self.r2 >= 0.999:
            self._logger.info(f'Calibration curve successfully set.\nSlope = {self.x_slp}\nIntercept = {self.y_int}\nr^2 = {self.r2}')
            self.calCurveFit = True
        else:
            self._logger.warning("Failed to fit calibration curve to data.")
            self.calCurveFit = False


        # Save calibration data
        # plt.plot(z_values, x_sigma, 'b8', markersize=2, label="σx")
        # plt.plot(z_values, y_sigma, 'r8', markersize=2, label="σy")
        # plt.plot(np.subtract(x_sigma,y_sigma),z_values,  '--k', markersize=2, label="σx - σy")
        # plt.grid(True)
        # plt.ylabel("z-Position (µm)")
        # plt.xlabel("Width (px)")
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
        bottom = currentZ - 10
        top = currentZ + 10
        steps = 101
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
