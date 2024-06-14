"""
Tetsing the functionalities of scripting.
"""

# Make functions into a simple functions
ai = api.imcontrol

positions_start = ai.getPositionerPositions()

print(positions_start)

ai.movePositionerXY('XY', 30.0 , 10.0)

ai.movePositioner('XY', 'X', -20.0)
ai.movePositioner('XY', 'Y', -5.0)


positions_finish = ai.getPositionerPositions()

print(positions_finish)