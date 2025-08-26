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

        self._widget.initValues()
        self._widget.openPreview.clicked.connect(self.openSetAFWindow)
        self._widget.registerPlane.clicked.connect(self.registerCurrentPlane)
        self._widget.clearRegPlane.clicked.connect(self.clearRegisteredPlane)
        self._widget.AFWindow.calCurve.clicked.connect(self.runCalCurveThread)
        self._widget.AFWindow.acqImgButton.clicked.connect(self.getOneFrameToSet)
        self._widget.AFWindow.resetEstimates.clicked.connect(self.resetEstimates)
        self._widget.AFWindow.resetMask.clicked.connect(self.resetMask)
        self._manager = self._master.autofocusManager
        self.zPositioner = self._master.positionersManager._subManagers['Z']
        self.AFCam = self._master.detectorsManager._subManagers['AF Cam']
        self.calCurveImgs = []
        self.calCurveScores = []
        
        self.storeInitEstimate()
        self.initWidget()
        
        self.threshold = self._manager.threshold #pixel value threshold for AF image

        self._widget.AFWindow.embeddedImage.sigUpdateWithMask.connect(self.updateImageWithMask)


    def initWidget(self):
        if self.AFCam.initAFCam:
            self._widget.openPreview.setEnabled(True)
            self._widget.registerPlane.setEnabled(True)
            self._widget.clearRegPlane.setEnabled(True)

    def storeInitEstimate(self):
        self.guess_x = self._manager.guess_x    # Guesses for fits Background, Centre, Width, Amplitude
        self.guess_y = self._manager.guess_y


    def resetEstimates(self):
        self.guess_x = self._manager.init_guess_x[:]
        self.guess_y = self._manager.init_guess_y[:]

        self._logger.info('Gaussian fit parameters reset to initial.')

    def resetMask(self):
        if self._widget.AFWindow.coordsRegistered:
            self._widget.AFWindow.embeddedImage.left = None
            self._widget.AFWindow.embeddedImage.right = None
            self._widget.AFWindow.coordsRegistered = False
            self.getOneFrameToSet()
            self._logger.info('Reflection mask deleted.')
            for name in self._widget.AFWindow.instructionList:
                if name.order == 0:
                    name.setStyleSheet("color: white;")
                else:
                    name.setStyleSheet("color: gray;")

        else:
            self._logger.info('Reflection mask is not currently registered.')


    def clearRegisteredPlane(self):
        self._commChannel.initRegScore = None
        self.offLED()

    # def autofocusModuleToggle(self, state):
    #     if not self.AFCam.initAFCam:
    #         self._logger.info('Autofocus camera was not initialized.')
    #         time.sleep(0.1)
    #         self._widget.autofocusModule.setCheckState(False)
    #     else:
    #         self._commChannel.autofocusEnabled = state
    #         self._widget.toggleEnabled(state)
    #         if state == False:
    #             self.offLED()
    #         if (state == True) and (self._commChannel.initRegScore != None):
    #             self.onLED()


    def onLED(self):
        self._widget.led.turn_on()

    def offLED(self):
        self._widget.led.turn_off()

    def registerCurrentPlane(self):
        score = self.getAndScoreOne()
        self._commChannel.initRegScore = score
        print(f"Plane registered with score of {self._commChannel.initRegScore:.2f}")
        self.onLED()

    def openSetAFWindow(self):
        self._widget.AFWindow.show()
        self._widget.AFWindow.raise_()
        self.getOneFrameToSet()

    def getOneFrameToSet(self):
        if self._widget.AFWindow.coordsRegistered:
            img = self.getOneFrame()
            imgMaskZero = self.colToZero(img)
            self.setOneFrame(imgMaskZero)
            return imgMaskZero
        else:
            img = self.getOneFrame()
            self.setOneFrame(img)
            return img

    def getOneFrame(self): 
        img = self.AFCam.grabFrameOnly()
        return img

    def setOneFrame(self, img): 
        pixmapImg = self._widget.AFWindow.convert_ndarray_to_qpixmap(img)
        self._widget.AFWindow.embeddedImage.setPixmap(pixmapImg)

    def runCalCurveThread(self):
        threading.Thread(target=self.runCalCurve, args=(), daemon=True).start()


    
    def colToZero(self, img):

        imgMaskZero = img[:]
        imgMaskZero[:,range(self._widget.AFWindow.embeddedImage.left,self._widget.AFWindow.embeddedImage.right)] = 0

        return imgMaskZero

    def updateImageWithMask(self):
        img = self.getOneFrame()
        imgMaskZero = self.colToZero(img)
        self.setOneFrame(imgMaskZero)


    def runCalCurve(self):
        # if self._widget.AFWindow.embeddedImage.left == None:
        #     self._widget.AFWindow.msg_box.exec_()
        if not self._widget.AFWindow.coordsRegistered:
            self._logger.warning("Reflection mask must be set before running calibration curve.")
        
        else:
            
            zList, currentZ = self.calcZRange()
            # zList = zList.reverse()
            if len(self.calCurveImgs) != 0:
                self.calCurveImgs = []
            for count, _ in enumerate(zList):
                # filename = f"{count:03}.tif"
                self.zPositioner.setPosition(zList[count], 'Z')
                time.sleep(0.01)
                img = self.getOneFrame()
                imgMaskZero = self.colToZero(img)
                self.setOneFrame(imgMaskZero)
                # self.saveImageInBackground(img, path, filename)
                self.calCurveImgs.append(img)
            
            self.zPositioner.setPosition(currentZ, 'Z')
            time.sleep(0.01)
            img = self.getOneFrame()
            imgMaskZero = self.colToZero(img)
            self._widget.AFWindow.instruction_label3.setStyleSheet("color: gray;")
            self._widget.AFWindow.instruction_label1.setStyleSheet("color: white;")
            self.setOneFrame(imgMaskZero)
            
            self.scoreCalCurveImgs(zList)


    def getAndScoreOne(self):
        assert self._commChannel.calCurveFit, "Calibration curve not set."
        img = self.getOneFrame()
        score = self.scoreOneImg(img)
        return score

    # def scoreOneLive(self, img):
    #     assert self._commChannel.calCurveFit, "Calibration curve not set."
    #     score = self.scoreOneImg(img)
    #     zPred = self.getYfromX(score)
    #     self._commChannel.currentRegScore = score
    #     self._commChannel.currentPredZ = zPred
    #     return score, zPred
    
    def setZPosition(self, z):
        self.zPositioner.setPosition(z, 'Z')

    # def getXfromY(self, y):
    #     x = self._manager.getXromY(y)
    #     return x

    def getYfromX(self, x):
        y = self._manager.getYfromX(x)
        return y
    
    def scoreOneImg(self, im):
        score = self._manager.scoreOneImg(im, self._commChannel.AFMaskLeft, self._commChannel.AFMaskRight)
        return score
    
    def scoreCalCurveImgs(self, zList):
        # Define the model function. In our case, a 1D Gaussian.
        def Gaussian1D(xdata, i0, x0, sX, amp):
            x = xdata
            x0 = float(x0)
            eq = i0+amp*np.exp(-((x-x0)**2/2/sX**2))
            return eq

        # x_c = []
        x_sigma = []
        y_sigma = []
        # i_values = []

        # To read the acquired images and apply the Gaussian fitting
        for i in range(len(self.calCurveImgs)):
            # i_values.append(i)
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
            xMasked = np.delete(x, range(self._widget.AFWindow.embeddedImage.left,self._widget.AFWindow.embeddedImage.right))
            imgMaskDel = self._manager.removeColumns(im, self._widget.AFWindow.embeddedImage.left, self._widget.AFWindow.embeddedImage.right)
            
            # Do x fit
            popt, pcov = curve_fit(Gaussian1D, xMasked, np.mean(imgMaskDel,axis=0), p0=self.guess_x, maxfev = 50000)
            x0 = popt[1]
            sx = popt[2]  
            self.guess_x.clear()
            self.guess_x.append(popt)
            # Do y fit
            popt, pcov = curve_fit(Gaussian1D, y, np.mean(imgMaskDel,axis=1), p0=self.guess_y, maxfev = 50000)
            y0 = popt[1]
            sy = popt[2]
            
            # Replaces initial guess with final guess
            self.guess_y.clear()
            self.guess_y.append(popt)
        
            x_sigma.append(abs(sx))
            # print(x_sigma)
            y_sigma.append(abs(sy))
            # x_c.append(popt[1])
            # plt.plot((x0,x0+sx),(y0,y0))
            # plt.plot((x0,x0),(y0,y0+sy))
            # plt.imshow(im)
            # plt.show()
            
        # This is just to set the x-axis of the graph to the axial values
        # StepSize = zval
        # i_values = np.array(i_values)
        z_values = zList
        comboData = np.subtract(x_sigma,y_sigma)
        comboDataReshape = comboData.reshape(-1, 1)
        comboDataReshape1D = [j[0] for j in comboDataReshape]
        self._commChannel.AFMaskLeft = self._widget.AFWindow.embeddedImage.left
        self._commChannel.AFMaskRight = self._widget.AFWindow.embeddedImage.right

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
            self._logger.info(f'Calibration curve successfully set.\nSlope = {self.x_slp}\nIntercept = {self.y_int}\nR^2 = {self.r2}')
            self._commChannel.calCurveFit = True
            self._widget.AFWindow.ccSlopeVal.setText(str(round(self.x_slp,3)))
            self._widget.AFWindow.ccIntVal.setText(str(round(self.y_int,2)))
            self._widget.AFWindow.ccR2Val.setText(str(round(self.r2,5)))
            sensitivity = -1 / self.x_slp
            self._widget.AFWindow.ccSensVal.setText(f'{round(sensitivity,2)} pixels/um')
        else:
            self._logger.warning(f"Failed to fit calibration curve to data.\nSlope = {self.x_slp:.3f}\nIntercept = {self.y_int:.2f}\nR^2 = {self.r2:.4f}")
            self._commChannel.calCurveFit = False
        

    def calcZRange(self):
        currentZ = self.zPositioner._position['Z']
        rangeVal = self._widget.AFWindow.calCurveRange.value()
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
