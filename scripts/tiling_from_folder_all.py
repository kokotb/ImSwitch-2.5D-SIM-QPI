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
import time
# import imagej


def create_tiling_from_tif_TZYX(tiling_paths, num_columns, num_rows, overlay):
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


def create_tiling_from_tif_XY(tiling_paths, num_columns, num_rows, overlay, is_sim_stack):
    """
    Creates tiling from tifs that were acquired in a snake shape (alphabetic order should be the same as the acquisition).
    It is adjusted for a two-dimensional stack.
    :param tiling_paths: paths of tif files that should be combined in to one image
    :param num_columns: number of columns in tile acquisition
    :param num_rows: number of rows in tile acquisition
    :param overlay: amount of overlay between neighboring images (e.g. 0.1 = 10%)
    :return: combined image
    """
    all_tifs = tiling_paths
    stack1 = tifffile.imread(all_tifs)
    
    dim_len = len(stack1.shape) # [tiles, x, y]
    # dimx, dimy = stack1.shape
    
    dimx = 1
    dimy = 0
    for row in range(num_rows):
        new_row = []
        if row % 2 == 0:
            num_list = range(num_columns)
        else:
            num_list = range(num_columns - 1, -1, -1)
        for count, column in enumerate(num_list):
            if dim_len != 3:
                print('wrong number of dimensions!!!')
                return None
            else:
                # Import the correct stack at correct position
                stack = tifffile.imread(all_tifs[row * num_columns + column])
            if count != (num_columns - 1):
                shape_x = stack.shape[dimx]
                cut_off = int(shape_x * (1-overlay))
                stack = stack[:, 0:cut_off]
            if count == 0:
                new_row = np.copy(stack)
            else:
                new_row = np.concatenate((new_row, stack), axis=dimx)
        new_row = np.array(new_row)
        # For development - uncomment if snake-scan does not seem right
        # tifffile.imwrite(f'test_cut2_{row}.tif', new_row, imagej=True)
        if row != num_rows:
            shape_y = new_row.shape[dimy]
            cut_off = int(shape_y * (1-overlay))
            new_row = new_row[0:cut_off, :]
        if row == 0:
            final_tiling = new_row
        else:
            final_tiling = np.concatenate((final_tiling, new_row), axis=dimy)

    return final_tiling


def create_tiling_from_tif_XY_stack_to_WF(tiling_paths, num_columns, num_rows, overlay, is_sim_stack):
    """
    Creates tiling from tifs that were acquired in a snake shape (alphabetic order should be the same as the acquisition).
    It is adjusted for a two-dimensional stack.
    :param tiling_paths: paths of tif files that should be combined in to one image
    :param num_columns: number of columns in tile acquisition
    :param num_rows: number of rows in tile acquisition
    :param overlay: amount of overlay between neighboring images (e.g. 0.1 = 10%)
    :return: combined image
    """
    all_tifs = tiling_paths
    
    
    
    if is_sim_stack:
        stack1_in = tifffile.imread(all_tifs)
        # FIXME: Remove when actual SIM data, in just for Arduino simulator
        normalize = np.shape(stack1_in)[0]
        stack1 = []
        for stack in stack1_in:
            # stack1.append(np.sum(stack[-3:], 0, dtype=np.int16))
            stack1.append(np.sum(stack[-3:], 0)/normalize)
    
        # Needs that because doing calculus with np
        stack1 = np.array(stack1, dtype="uint16")
    else:
        stack1 = tifffile.imread(all_tifs)
    dim_len = len(stack1.shape) # [tiles, x, y]
    # tile_num, dimx, dimy = stack1.shape
    
    dimx = 1
    dimy = 0
    for row in range(num_rows):
        new_row = []
        if row % 2 == 0:
            num_list = range(num_columns)
        else:
            num_list = range(num_columns - 1, -1, -1)
        for count, column in enumerate(num_list):
            if dim_len != 3:
                print('wrong number of dimensions!!!')
                return None
            else:
                # Import the correct stack at correct position
                # stack = tifffile.imread(all_tifs[row * num_columns + column])
                stack = stack1[row * num_columns + column] 
            if count != (num_columns - 1):
                shape_x = stack.shape[dimx]
                cut_off = int(shape_x * (1-overlay))
                stack = stack[:, 0:cut_off]
            if count == 0:
                new_row = np.copy(stack)
            else:
                new_row = np.concatenate((new_row, stack), axis=dimx)
        new_row = np.array(new_row)
        # For development - uncomment if snake-scan does not seem right
        # tifffile.imwrite(f'test_cut2_{row}.tif', new_row, imagej=True)
        if row != num_rows:
            shape_y = new_row.shape[dimy]
            cut_off = int(shape_y * (1-overlay))
            new_row = new_row[0:cut_off, :]
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
# input_dir = "D:\\Nextcloud\\2022 - 2.5D SIM - share\\Measurements\\240802_5by5Stacks\\astack\\5by5_0overlap"
# input_dir = "D:\\Nextcloud\\2022 - 2.5D SIM - share\\Measurements\\240802_5by5Stacks\\astack\\5by5_0p3overlap"
# input_dir = "D:\\Nextcloud\\2022 - 2.5D SIM - share\\Measurements\\240802_5by5Stacks\\astack\\5by5_0p5overlap"
input_dir = "D:\\Nextcloud\\2022 - 2.5D SIM - share\\1 - analysis\\sensitivity\\SIM\\240918110201_CT_HanaSampleWell2"
# input_dir = "D:\\Nextcloud\\2022 - 2.5D SIM - share\\Measurements\\240802_5by5Stacks\\astack\\5by5_Neg0p5overlap"

# Set if you want to run tiling from folder
# input_dir = dir_path = os.path.dirname(os.path.realpath(__file__))
exp_names = ["f"]
name_pattern = "_stack" # can be wf or something else
t_pattern = "f"

# input_dir = "D:\\Documents\\4 - software\\python-scripting\\2p5D-SIM\\test_export\\fortilingrecon"
# exp_names = ["2024_07_"]
# name_pattern = "Reconstruction"
# t_pattern = "frame_"

single_channels_names = ['510', '580', '660']
number_of_rows = 1
number_of_columns = 1
image_overlay = 0.58
# image_overlay = 0

# Choose operations that will be performed, note that export and reordering 
# can't be done in the same run
create_tiling = True                                   # can be True or False
combine_timepoints = False
combine_timepoints_colors_separate = True
single_chan_tiling = False
is_sim_stack = True # True for SIM_stack, false for Reconstructed images
# reorder_stack = True

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
    
# Create tiling directory
save_path_tiling_time = os.path.join(input_dir, 'tiling_t')
try:
    os.mkdir(save_path_tiling_time)
except OSError as error:
    print(error)
    
# Change dir to tiling diectory
os.chdir(save_path_tiling)

    
#TODO: Recognize "Reconstruction" pattern, only take those files
#TODO: Recognize number of channels in folder
#TODO: Recognize number of time-points in folder
#TODO: Recognize the number of tiles - maybe better to keep it as user input
#TODO: Hardcode tiles 5x5 for development
#TODO: Make an image overlay in python


# Perform tiling
if create_tiling:
    name_tiling = 'tiling'
    print('\nCreating panoramas ...')
    # Repeat for each experiment
    for exp_name in exp_names:
        # Get all tif files
        all_paths = glob.glob(input_dir + f'\\{exp_name}*{name_pattern}*.tif')
        all_names = [os.path.basename(x) for x in all_paths]
        all_names_unique = []
        
        if all_names == []:
            print(f"{exp_name} not present in folder. Skipping analysis.")
            continue
        
        num_times, all_times = getUniqueNamesByPattern(all_names, t_pattern)
        
        start = time.time()
        # Do each chan separately
        time_stack_colors = []
        for num_ch, ch in enumerate(single_channels_names):
            print(f'--Chan {num_ch+1} out of {len(single_channels_names)}----')
            # Do each time point separately
            start_chan = time.time()
            single_chan_time_stack = []
            for num_time, name_time in enumerate(all_times):
                print(f'----Time {num_time+1} out of {num_times}----')
                # Get all ROI names for this chan and this time point
                roi_names_import = glob.glob(f'{input_dir}\\{name_time}*{ch}*.tif')
                tiling = create_tiling_from_tif_XY_stack_to_WF(roi_names_import, number_of_rows, number_of_columns, image_overlay, is_sim_stack)
                single_chan_time_stack.append(tiling)
                if single_chan_tiling:
                    tifffile.imwrite(f'{save_path_tiling}\\{name_time}_{ch}_{name_tiling}.tif', tiling, metadata={"axes": "YX", "Channel": {"Name": ch}}, imagej=True)
            time_stack_colors.append(single_chan_time_stack)    
            if combine_timepoints_colors_separate:
                # if num_times < 2:
                #     single_chan_time_stack = np.array(single_chan_time_stack)
                #     tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_{ch}_{name_tiling}.tif', single_chan_time_stack, metadata={"axes": "YX", "Channel": {"Name": ch}}, imagej=True)
                #     end_chan = time.time()
                #     dt_chan = end_chan - start_chan
                #     print(f'Chan {num_ch+1} done in {int(dt_chan):03} s')
                # else:    
                single_chan_time_stack = np.array(single_chan_time_stack)
                tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_{ch}_{name_tiling}.tif', single_chan_time_stack, metadata={"axes": "TYX", "Channel": {"Name": ch}}, imagej=True)
                end_chan = time.time()
                dt_chan = end_chan - start_chan
                print(f'Chan {num_ch+1} done in {int(dt_chan):03} s')
        
        if combine_timepoints:
            # if num_times < 2:
            #     time_stack_colors_out = np.array(time_stack_colors)
            #     time_stack_colors_out = np.swapaxes(time_stack_colors_out,0,1)
            #     tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_cAll_{name_tiling}.tif', time_stack_colors_out, metadata={"axes": "CYX", "Channel": {"Name": single_channels_names}}, imagej=True)
            #     # Bigger tiffs
            #     # tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_cAll_{name_tiling}.tif', time_stack_colors_out, metadata={"axes": "CYX", "Channel": {"Name": single_channels_names}}, imagej=True, bigtiff=True)
            # else:
            time_stack_colors_out = np.array(time_stack_colors, )
            time_stack_colors_out = np.swapaxes(time_stack_colors_out,0,1)
            tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_cAll_{name_tiling}.tif', time_stack_colors_out, metadata={"axes": "TCYX", "Channel": {"Name": single_channels_names}}, imagej=True)
            # Bigger tiffs
            # tifffile.imwrite(f'{save_path_tiling_time}\\{exp_name}_tAll_cAll_{name_tiling}.tif', time_stack_colors_out, metadata={"axes": "TCYX", "Channel": {"Name": single_channels_names}}, imagej=True, bigtiff=True)
                
        end = time.time()
        dt = end - start
        print(f'Tiling done in {int(dt):03} s')
        
        