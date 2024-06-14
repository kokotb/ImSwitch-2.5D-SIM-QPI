"""
Tetsing the functionalities of scripting.
"""
import time

control = api.imcontrol

positions_start = control.getPositionerPositions()

print(positions_start)


positioner_z = 'Z'
axis_z = 'Z'
current_position_z = positions_start[positioner_z][axis_z]
positioner_xy = 'XY'
axis_x = 'X'
current_position_x = positions_start[positioner_xy][axis_x]

print(current_position_z)
print(current_position_x)

new_postion_z = 20
api.imcontrol.setPositioner(positioner_z, axis_z, new_postion_z)
time.sleep(0.1)
positions_current = control.getPositionerPositions()
print(positions_current)