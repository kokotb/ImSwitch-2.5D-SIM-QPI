"""
Script that will run nxn grid and grab data at each grid location.
We might need to include focus correction at each grid position, for sample tilt.
"""
import time

# Simplify calling of functions by a single command
control = api.imcontrol

# Set positioner info axis_y is set to 'X' for testing purposes
positioner_xy = 'XY' # Must match positioner name in config file
axis_x = 'X'
axis_y = 'X'  # Change to 'Y' when testing for real

# Image size - I need to grab that from GUI but is hardcoded at the momen
image_pix_x = 512
image_pix_y = 512

# Grab starting position that we can return to
positions_start = control.getPositionerPositions()
start_position_x = positions_start[positioner_xy][axis_x]
start_position_y = positions_start[positioner_xy][axis_y]

# Set experiment info
grid_x_num = 3
grid_y_num = 3
overlap_xy = 0

# Determine stage travel range
frame_size_x = image_pix_x
frame_size_y = image_pix_y

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


current_position_x = positions_start[positioner_xy][axis_x]

current_position_y = positions_start[positioner_xy][axis_y]

print(current_position_x)

new_postion_z = 20
api.imcontrol.setPositioner(positioner_z, axis_z, new_postion_z)
time.sleep(0.1)
positions_current = control.getPositionerPositions()
print(positions_current)