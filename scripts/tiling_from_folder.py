"""
This code is meant for tiling of reconstructed SIM data acquired in grid with 
certain overlap.

Parts of code were taken from our internal script prepared by Petra Cotar in
January 2022: export_TZCXY_from_msr_4.3.py

Further developments may include: SIM stack to wide-field image tiling.
July 2024
Bostjan Kokot, contact: bostjan.kokot@ijs.si
"""

# import javabridge as jv
import numpy as np
import glob
import tifffile
import os
# import imagej


def create_tiling_from_tif(tiling_paths, num_columns, num_rows, overlay):
    """
    Creates tiling from tifs that were acquired in a snake shape (alphabetic order should be the same as the acquisition).
    It is writen for a multidimensional stack, 5 or 4 dimensional (e.g. TCZYX or TZYX).
    :param tiling_paths: paths of tif files that should be combined in to one image
    :param num_columns: number of columns in tile acquisition
    :param num_rows: number of rows in tile acquisition
    :param overlay: amount of overlay between neighboring images (e.g. 0.1 = 10%)
    :return: combined image
    """
    all_tifs = tiling_paths
    stack1 = tifffile.imread(all_tifs[0])
    dim_len = len(stack1.shape)
    dimx = 4
    dimy = 3
    for row in range(num_rows):
        new_row = []
        if row % 2 == 0:
            num_list = range(num_columns)
        else:
            num_list = range(num_columns - 1, -1, -1)
        for count, column in enumerate(num_list):
            if dim_len == 5:
                stack = tifffile.imread(all_tifs[row * num_columns + column])
            elif dim_len == 4:
                stack = np.array([tifffile.imread(all_tifs[row * num_columns + column])])
            elif dim_len == 3:
                stack = np.array([[tifffile.imread(all_tifs[row * num_columns + column])]])
            else:
                print('wrong number of dimensions!!!')
                return None
            if count != (num_columns - 1):
                shape_x = stack.shape[dimx]
                cut_off = int(shape_x * (1-overlay))
                stack = stack[:, :, :, :, 0:cut_off]
            if count == 0:
                new_row = np.copy(stack)
            else:
                new_row = np.concatenate((new_row, stack), axis=dimx)
        new_row = np.array(new_row)
        tifffile.imwrite(f'test_cut2_{row}.tif', new_row, imagej=True)
        if row != num_rows:
            shape_y = new_row.shape[dimy]
            cut_off = int(shape_y * (1-overlay))
            new_row = new_row[:, :, :, 0:cut_off, :]
        if row == 0:
            final_tiling = new_row
        else:
            final_tiling = np.concatenate((final_tiling, new_row), axis=dimy)

    return final_tiling


def getUniqueNamesByPattern(file_names, pattern):
    all_names_unique = []
    # Split by time
    for name in file_names:
        start = name.find(pattern)
        if start != -1:
            new = name[0:start + len(pattern) + 4]
            all_names_unique.append(new)
    # List of unique names for time points
    all_names_unique = list(set(all_names_unique))
    all_names_unique = sorted(all_names_unique)
    num_names = len(all_names_unique)
    return num_names, all_names_unique


def getNamesByPattern(file_names, pattern):
    all_names_unique = []
    # Split by time
    for name in file_names:
        start = name.find(pattern)
        if start != -1:
            all_names_unique.append(name)
    # List of unique names for time points
    all_names_unique = list(set(all_names_unique))
    all_names_unique = sorted(all_names_unique)
    num_names = len(all_names_unique)
    return num_names, all_names_unique


##############################
#      SET PARAMETERS        #
##############################
input_dir = "D:\\Documents\\4 - software\\python-scripting\\2p5D-SIM\\test_export\\recon"
exp_names = ["2024_07_11-04-15-53_PM"]
single_channels_names = ['488nm', '561nm', '640nm']
name_pattern = "Reconstruction" # can be wf or something else
t_pattern = "frame_"
number_of_rows = 5
number_of_columns = 5

# Choose operations that will be performed, note that export and reordering 
# can't be done in the same run
create_tiling = True                                   # can be True or False


##############################
#         ALL DONE           #
##############################

# # Create export directory
# save_path_stack = os.path.join(input_dir, 'export_stack')
# try:
#     os.mkdir(save_path_stack)
# except OSError as error:
#     print(error)
    
# Create tiling directory
save_path_tiling = os.path.join(input_dir, 'tiling')
try:
    os.mkdir(save_path_tiling)
except OSError as error:
    print(error)

    
#TODO: Recognize "Reconstruction" pattern, only take those files
#TODO: Recognize number of channels in folder
#TODO: Recognize number of time-points in folder
#TODO: Recognize the number of tiles - maybe better to keep it as user input
#TODO: Hardcode tiles 5x5 for development
#TODO: Make an image overlay in python


# Perform tiling
if create_tiling:
    # Repeat for each 
    for exp_name in exp_names:
        # Get all tif files
        all_paths = glob.glob(input_dir + f'\\{exp_name}*{name_pattern}*.tif')
        all_names = [os.path.basename(x) for x in all_paths]
        all_names_unique = []
        
        
        
        if all_names == []:
            print(f"{exp_name} not present in folder. Skipping analysis.")
            continue
        
        # # Split by time
        # for part in all_names:
        #     start = part.find(t_pattern)
        #     new = part[0:start + len(t_pattern) + 4]
        #     all_names_unique.append(new)
        # # List of unique names for time points
        # all_times = list(set(all_names_unique))
        # all_times = sorted(all_times)
        # num_times = len(all_times)
        
        num_times, all_times = getUniqueNamesByPattern(all_names, t_pattern)
        
        # Do each chan seprately
        for ch in single_channels_names:
            # num_rois_times, all_rois_times = getUniqueNamesByPattern(all_names, ch)
            # Do each time point separately
            for num_time, name_time in enumerate(all_times):
                roi_names_unique = []
                # Get all unique ROI names for this time point
                # num_rois, all_rois = getNamesByPattern(all_rois_times, name_time)
                
                roi_names_import = glob.glob(f'{input_dir}\\{name_time}*{ch}*.tif')
                # for roi in all_rois:
                #     roi_names_import = glob.glob(f'{input_dir}\\{name_time}*{ch}.tif')
                #     roi_names_import.append(all_rois_org[0])
                # for roi in all_rois: 
                #     num, all_rois_org = getNamesByPattern(all_names, roi)
                #     roi_names_import.append(all_rois_org[0])
                print("")
                # for part in all_names: 
                #     is_part = part.find(name_time)
                #     if is_part != -1:
                #         start = part.find(name_pattern)
                #         new = part[0:start + len(name_pattern)]
                #         roi_names_unique.append(new)
                # all_rois = list(set(roi_names_unique))
                # all_rois = sorted(all_rois)
                # num_rois = len(all_rois)
                
                # Tile each chan
                chan_names_unique = []
                for chan in single_channels_names:
                    # Get name patterns
                    for part in all_names: 
                        is_part = part.find(chan)
                        if is_part != -1:
                            start = is_part
                            new = part[0:start + len(chan)]
                            chan_names_unique.append(new)
                    all_rois_chan = list(set(chan_names_unique))
                    all_rois_chan = sorted(all_rois_chan)
                    num_rois_chan = len(all_rois_chan)

                    print("")
        # # Get all the unique names (positions), needs changing if the name structure is different!!!!
        # for part in all_names:
        #     start = part.find(name_pattern)
        #     new = part[0:start + len(name_pattern) + 1]
        #     all_names_unique.append(new)
        # # List of unique names - channels omitted
        # all_times_rois = list(set(all_names_unique))
        # all_times_rois = sorted(all_times_rois)
        # num_times_rois = len(all_times_rois)
        

        
        # for i, roi in enumerate(all_times_rois):
        #     print(f'----ROI{i+1} out of {num_times_rois}----')
        #     print(f'{roi} \n')
        #     roi_times = glob.glob(input_dir + f'\\{roi}*.tif')
        # print(roi_times)
    # print('\ncreating panoramas ...')
    # tiling_from = [input_dir]
    # endings = ['Reconstruction_']
    # for ch in single_channels_names:
    #     endings.append(ch)
    # for til_path in tiling_from:
    #     for ending in endings:
    #         all_paths = glob.glob(f'{til_path}\\*{ending}*.tif')
    #         print(all_paths)
    #         all_names = [os.path.basename(x) for x in all_paths]
            # all_names_unique = []
            # # get all the unique names (positions), needs changing if the name structure is different!!!!
            # for part in all_names:
            #     start = part.find('_xy')
            #     new = part[0:start]
            #     all_names_unique.append(new)
            # all_unique_tilings = sorted(list(set(all_names_unique)))
            # for tiling_name in all_unique_tilings:
            #     print(f'\n--- {tiling_name}{ending} ---')
            #     cur_tiling_paths = glob.glob(f'{til_path}\\{tiling_name}*{ending}*.tif')
            #     tiling = create_tiling_from_tif(cur_tiling_paths, number_of_rows, number_of_columns, image_overlay)
            #     tifffile.imwrite(f'{save_path_tiling}\\{tiling_name}_{ending}_tiling.tif', tiling, imagej=True)
