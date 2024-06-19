"""
Script that will run nxn grid and grab data at each grid location.
We might need to include focus correction at each grid position, for sample tilt.
"""
import time
import numpy as np
import math
import logging
import sys



# Logging to the console
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

# Simplify calling of functions by a single command
control = api.imcontrol

# Set positioner info axis_y is set to 'X' for testing purposes
positioner_xy = 'XY' # Must match positioner name in config file
axis_x = 'X'
axis_y = 'Y'  # Change to 'Y' when testing for real

# Image size - I need to grab that from GUI but is hardcoded at the momen
image_pix_x = 512
image_pix_y = 512
pix_size = 0.123 # um

# Grab starting position that we can return to
positions_start = control.getPositionerPositions()
start_position_x = positions_start[positioner_xy][axis_x]
start_position_y = positions_start[positioner_xy][axis_y]
xy_start = [start_position_x, start_position_y]

# Set experiment info
grid_x_num = 3
grid_y_num = 3
overlap_xy = 0
xy_scan_type = 'square' # or 'quad', not sure what that does yet...
count_limit = 9999
save_dir = "D:\\Documents\\4 - software\\python-scripting\\2p5D-SIM\\test_export"

# Determine stage travel range, stage accepts values in microns
frame_size_x = image_pix_x*pix_size
frame_size_y = image_pix_y*pix_size

x_step = (1 - overlap_xy) * frame_size_x
y_step = (1 - overlap_xy) * frame_size_y
xy_step = [x_step, y_step]

assert x_step != 0 and y_step != 0, 'xy_step == 0 - check that xy_overlap is < 1, ot that frame_size is > 0'

if grid_x_num > 0 and grid_y_num > 0:
    x_range = grid_x_num * x_step
    y_range = grid_y_num * y_step
    xy_range = [x_range, y_range]
else:
    print("Grid parameters are not set correct!")

# Generate list of coordinates
positions = []

y_start = xy_start[1]

y_list = list(np.arange(0, grid_y_num, 1)*y_step+y_start)

# Generate positions for each row
for y in y_list:
    # Where to start this row
    x_start = xy_start[0]
    if xy_scan_type == 'square':
        x_stop = x_start - x_range
        # Generate x coordinates
        x_list = list(np.arange(0, -grid_x_num, -1)*x_step+x_start)
    elif xy_scan_type == 'quad':
        x_stop = x_start - math.sqrt(x_range**2 - (y-y_start)**2)
        # Generate x coordinates
        x_list = list(np.arange(x_start, x_stop, -x_step))
        
    # Run every other row backwards to minimize stage movement
    if y_list.index(y) % 2 == 1:
        x_list.reverse()
    
    # Populate the final list
    for x in x_list:
        # print(np.round(x, 2))
        # positions.append([np.round(x, 2),np.round(y, 2)])
        positions.append([x,y])
        
    # Truncate the list if the length/the number of created positions
    # exceeds the specified limit
    if len(positions) > count_limit:
        positions = positions[:count_limit]
        logger.warning(f"Number fo positions was reduced to {count_limit}!")


# control.setRecFolder(save_dir)
# mainWindow.setCurrentModule('imcontrol')
# control.setRecModeSpecFrames(1)

# Move stage at each of the positions and execute an action
for j, pos in enumerate(positions):
    x_set = pos[0]
    y_set = pos[1]
    # SIM trigger sequence comes here
    
    # control.acquireSIMSet()
    # Get it to emit a signal once it is done?
    
    # Data saving is handled on the SIM side, only setting 
    # up of the folder is this side
    
    
    
    # control.setPositioner(positioner_xy, axis_x, x_set)
    # control.setPositioner(positioner_xy, axis_y, y_set)
    # control.startRecording()
    # waitForRecordingToEnd = getWaitForSignal(control.signals().recordingEnded)
    # control.stopRecording()  # It's important to call this after getWaitForSignal!
    print(f"Testing position set at {pos}.")

mainWindow.setCurrentModule('imscripting')
# print(positions)
# rect  = []
# rect_size = 512
# for position in positions:
#     rect.append([[position[1] - 7, position[0] - 7, rect_size, rect_size]])
# print(rect)

# data_image_dummy = np.zeros((grid_x_num*image_pix_x, grid_y_num*image_pix_y))

# print(np.shape(data_image_dummy))

# save_dir = "D:\\Documents\\4 - software\\python-scripting\\2p5D-SIM\\test_export"


# plot_img_with_rectangles(data_image_dummy, rect[0], save_dir, "test")    
# plot_scanning_direction(data_image_dummy, rect[0], save_dir, "test2")

# current_position_x = positions_start[positioner_xy][axis_x]

# current_position_y = positions_start[positioner_xy][axis_y]

# print(current_position_x)

# new_postion_z = 20
# control.setPositioner(positioner_z, axis_z, new_postion_z)
# time.sleep(0.1)
# positions_current = control.getPositionerPositions()
# print(positions_current)