from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import APIExport
import numpy as np
from imswitch.imcommon.model import dirtools, initLogger, APIExport, ostools
from imswitch.imcommon.framework import Signal


class TilingController(ImConWidgetController):
    """ Linked to WatcherWidget. """

    # sigTilingPositions = Signal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = initLogger(self)
        # self._widget.sigSaveFocus.connect(self.saveFocus)
        self._widget.sigTilingInfoChanged.connect(self.valueChanged)
        # self._image = []
        # self._skipOrNot = None
        self._widget.initTilingInfo()

        self.num_grid_x = self._widget.numGridX_textedit.text()

        self.num_grid_y = self._widget.numGridY_textedit.text()
        
        self.overlap = self._widget.overlap_textedit.text()

        for key in self._master.positionersManager._subManagers:
            if self._master.positionersManager._subManagers[key].axes[0] == ['X'] or ['Y']:
                self.positionerXY = self._master.positionersManager._subManagers[key]





    def valueChanged(self, attrCategory, parameterName, value):
        self.setSharedAttr(attrCategory, parameterName, value)

    def setSharedAttr(self, attrCategory, parameterName, value):
        """Sending attribute to shared attributes

        Args:
            parameterName (str): name of a parameter passed from wdiget
            attr (_type_): type of a attribute (value, enabled, ...)
            value (_type_): value of the parameter read from wdiget
        """
        self.settingAttr = True
        try:
            self._commChannel.sharedAttrs[(attrCategory, parameterName)] = value
        finally:
            self.settingAttr = False

    def createXYGridPositionArray(self):
        imageLeastCommonSize = [512,512]
        pixelsize = self._commChannel.sharedAttrs._data[('SIM Parameters','Pixel size')]
        mag = self._commChannel.sharedAttrs._data[('SIM Parameters','Magnification')]
        projCamPixelSize = pixelsize/mag
        imageSizePixelsX, imageSizePixelsY = imageLeastCommonSize
        #Pulled from SIM GUI
        grid_x_num = self.num_grid_x
        grid_y_num = self.num_grid_y
        overlap_xy = self.overlap
        xy_scan_type = 'snake' # or 'quad', not sure what that does yet...
        count_limit = 101

        # Grab starting position that we can return to
        start_position_x, start_position_y = self.positionerXY.get_abs()
        x_start, y_start = [float(start_position_x), float(start_position_y)]
        
        # Determine stage travel range, stage accepts values in microns
        frame_size_x = imageSizePixelsX*projCamPixelSize
        frame_size_y = imageSizePixelsY*projCamPixelSize
        
        # Step-size based on overlap info
        x_step = (1 - overlap_xy) * frame_size_x
        y_step = (1 - overlap_xy) * frame_size_y
        assert x_step != 0 and y_step != 0, 'xy_step == 0 - check that xy_overlap is < 1, and that frame_size is > 0'
        positions = []
        y_list = list(np.arange(0, grid_y_num, 1)*y_step+y_start)
        # ------------Grid scan------------
        # Generate positions for each row
        for y in y_list:
            # Where to start this row

            if xy_scan_type == 'snake':
                # Generate x coordinates
                x_list = list(np.arange(0, -grid_x_num, -1)*x_step+x_start)

                
            # Run every other row backwards to minimize stage movement
            if y_list.index(y) % 2 == 1:
                x_list.reverse()
            
            # Populate the final list
            for x in x_list:
                positions.append([x,y])
                
            # Truncate the list if the length/the number of created
            # positions exceeds the specified limit
            if len(positions) > count_limit:
                positions = positions[:count_limit]
                self.logger.warning(f"Number fo positions was reduced to {count_limit}!")
        self._commChannel.sigTilingPositions.emit(positions)
        print(positions)
        return positions
    

    # def smallestXYForGridSpacing(self,image_sizes_px):


    #     for det_name in det_names:
    #         detector = self._master.detectorsManager[det_name]
    #         self.detectors.append(detector)
    #         image_sizes_px.append(detector.shape)
    #     else:
    #         self._logger.debug(f"Lasers not enabled. Setting image_size_px to default 512x512.")
    #         image_sizes_px = [[512,512]]
    #     imageLeastCommonSize = [] 
    #     # Check if image-sizes on all detectors are the same
    #     if image_sizes_px.count(image_sizes_px[0]) == len(image_sizes_px):
    #         imageLeastCommonSize = image_sizes_px[0]
    #     else:
    #         self._logger.debug(f"Check detector settings. Not all colors have same image size on the detectors. Defaulting to smallest size in each dimension.")
    #         # size = 0
    #         # Set desired
    #         image_size_x = image_sizes_px[0][0]
    #         image_size_y = image_sizes_px[0][1]
    #         for image_size_px in image_sizes_px:
    #             if image_size_px[0] < image_size_x:
    #                 image_size_x = image_size_px[0]
    #             if image_size_px[1] < image_size_y:
    #                 image_size_y = image_size_px[1]
    #         imageLeastCommonSize = [image_size_x, image_size_y]

    #     return imageLeastCommonSize

    # def saveFocus(self, bool):
    #     self._skipOrNot = bool
    #     # self._commChannel.sigSaveFocus.emit()

    # @APIExport()
    # def setTileLabel(self, label) -> None:
    #     self._widget.setLabel(label)

    # @APIExport()
    # def getSkipOrNot(self) -> bool:
    #     return self._skipOrNot

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
