import pprint
import xml.etree.ElementTree as ET
import json




data = {('Detector', '488 Cam', 'Model'): '230100355', ('Detector', '488 Cam', 'Pixel size'): [1, 1, 1], ('Detector', '488 Cam', 'Binning'): 1, ('Detector', '488 Cam', 'ROI'): [2048, 1732, 512, 512], ('Detector', '488 Cam', 'Param', 'ExposureTime'): 1400.0, ('Detector', '488 Cam', 'Param', 'Gain'): 0.0, ('Detector', '488 Cam', 'Param', 'Gamma'): 1.0, ('Detector', '488 Cam', 'Param', 'ExposureAuto'): 'Off', ('Detector', '488 Cam', 'Param', 'TriggerMode'): 'Off', ('Detector', '561 Cam', 'Model'): '224602766', ('Detector', '561 Cam', 'Pixel size'): [1, 1, 1], ('Detector', '561 Cam', 'Binning'): 1, ('Detector', '561 Cam', 'ROI'): [2560, 2326, 512, 512], ('Detector', '561 Cam', 'Param', 'ExposureTime'): 9000.0, ('Detector', '561 Cam', 'Param', 'Gain'): 0.0, ('Detector', '561 Cam', 'Param', 'Gamma'): 1.0, ('Detector', '561 Cam', 'Param', 'ExposureAuto'): 'Off', ('Detector', '561 Cam', 'Param', 'TriggerMode'): 'Off', ('Detector', '640 Cam', 'Model'): '224602765', ('Detector', '640 Cam', 'Pixel size'): [1, 1, 1], ('Detector', '640 Cam', 'Binning'): 1, ('Detector', '640 Cam', 'ROI'): [2528, 2252, 512, 512], ('Detector', '640 Cam', 'Param', 'ExposureTime'): 500.0, ('Detector', '640 Cam', 'Param', 'Gain'): 0.0, ('Detector', '640 Cam', 'Param', 'Gamma'): 1.0, ('Detector', '640 Cam', 'Param', 'ExposureAuto'): 'Off', ('Detector', '640 Cam', 'Param', 'TriggerMode'): 'Off', ('Laser', '488AOTF', 'Value'): 100.0, ('Laser', '488AOTF', 'Enabled'): False, ('Laser', '561AOTF', 'Value'): 100.0, ('Laser', '561AOTF', 'Enabled'): False, ('Laser', '640AOTF', 'Value'): 100.0, ('Laser', '640AOTF', 'Enabled'): False, ('Positioner', 'Z', 'Z', 'Position'): 1.0, ('Positioner', 'XY', 'X', 'Position'): '909', ('Positioner', 'XY', 'Y', 'Position'): '-231'}
# keys = []
# values = []
# # for key in data.keys():
# #     keys.append(key)

# # for value in data.values():
# #     values.append(value)

# # test = zip(keys,values)
# # print(list(test)[0])

# root = ET.Element('Expt. Settings')
# order = ET.SubElement(root, 'order', date='2020-01-01', id='12345')
# tree = ET.ElementTree(root)
# tree.write('testSettings.xml')

# for i in range(len(keys)):
#         numlevels = len(keys[i])
#         j=0
#         level0 = ET.SubElement(root, keys[i][j])
#         level1 = ET.SubElement(level0, keys[i][j+1])

#         print(keys[i][j])



# data.keys()
# print(keys)
# print(values)

# pprint.pp(keys[0])




        # setupInfo = self._setupInfo.sim
        # setupInfoKeyList = [a for a in dir(setupInfo) if not a.startswith('__') and not callable(getattr(setupInfo, a))] #Pulls all attribute names from class not dunder (__) and not functions.
        # setupValueList = []
        # for item in setupInfoKeyList:
        #     setupValueList.append(getattr(setupInfo,item)) #Pulls values of the attributes.
        # setupInfoDict = dict(zip(setupInfoKeyList,setupValueList)) #Put names, values in a dict.
        # self._widget.setSIMWidgetFromConfig(setupInfoDict) #Call function in SIMWidget that pulls in dict just created.


 
# Opening JSON file
# with open('test.json', 'r') as openfile:
 
#     # Reading from json file
#     json_object = json.load(openfile)
 
# print(json_object)
# print(type(json_object))
