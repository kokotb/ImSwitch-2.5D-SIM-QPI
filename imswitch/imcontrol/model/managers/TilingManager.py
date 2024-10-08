import numpy as np
from PIL import Image
from scipy import signal as sg
from imswitch.imcontrol.view.guitools.ViewSetupInfo import ViewSetupInfo as SetupInfo
from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger


class TilingManager(SignalInterface):
    """ 
    Tiling functions
    """
    def __init__(self):
        super().__init__()
        self._logger = initLogger(self)
            
    def createXYGridPositionArray(self,grid_x_num, grid_y_num, overlap_xy, startxpos, startypos, projCamPixelSize):

        imageLeastCommonSize = [512,512] #CTNOTE need programmatic, cant deal with at the moment.
        # pixelsize = self._commChannel.sharedAttrs._data[('SIM Parameters','Pixel size')]
        # mag = self._commChannel.sharedAttrs._data[('SIM Parameters','Magnification')]
        # projCamPixelSize = pixelsize/mag
        imageSizePixelsX, imageSizePixelsY = imageLeastCommonSize

        xy_scan_type = 'snake' # or 'quad', not sure what that does yet...
        count_limit = 101

        # Grab starting position that we can return to
        x_start = float(startxpos)
        y_start = float(startypos)
        
        # Determine stage travel range, stage accepts values in microns
        frame_size_x = imageSizePixelsX*projCamPixelSize
        frame_size_y = imageSizePixelsY*projCamPixelSize
        
        # Step-size based on overlap info
        x_step = (1 - overlap_xy) * frame_size_x
        y_step = (1 - overlap_xy) * frame_size_y
        assert x_step != 0 and y_step != 0, 'xy_step == 0 - check that xy_overlap is < 1, and that frame_size is > 0'
        positions = []
        y_list = list(y_start+np.arange(0, grid_y_num, 1)*y_step)
        # ------------Grid scan------------
        # Generate positions for each row
        for y in y_list:
            # Where to start this row

            if xy_scan_type == 'snake':
                # Generate x coordinates
                x_list = list(x_start+np.arange(0, -grid_x_num, -1)*x_step)

                
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
                self.logger.warning(f"Number of positions was reduced to {count_limit}!")
        posOrigin = positions[0]
        positions.pop(0)
        positions.append(posOrigin)

        return positions
# Copyright (C) 2020-2024 ImSwitch developers
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
