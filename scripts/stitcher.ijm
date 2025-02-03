// Author: Boštjan Kokot, Laboratory of Biophysics (Condensed Matter Department - F5, Jozef Stefan Institute)
// Intended for internal use
// Contact: bostjan.kokot@ijs.si
// Webpage: lbf.ijs.si
// Created:  23.01.2025              
// Modified: 28.01.2025 (save date is more recent)

// Script to automatically stitch together tiles for all time points in
// Currently implemented for one channel per folder
// Be aware that each time point can have slightly different sizes due to
// the nature of the stitcher

// Current version will work on a folder with single channel

// Set folders
dir_in = "D:/Nextcloud/2022 - 2.5D SIM - share/Measurements/250123 - Testing_saving_metada/241003161441_488MTG_10by10_10over/WF/";
channel_folders = newArray("488", "561", "640");
dir_out_name = "exp"

// Set tiling parameters
tile_x = 10;
tile_y = 10;
tile_overlap = 10; // 0-100 %

// Import and stitcher settings (should remain the same for our naming structure)
index_first_file = 0; // Stitcher needs this for accurate counting
pattern_start = "f"; // Pattern to discren data files from anything else
list_split_swap = "pos{iiii}"; // Swap pattern # of i is # of digits
list_split_swap_index = 1; // Set the split indec of the changing position

// Old dev comments 24.01.2025
//file_names_pattern = "f0000_pos"+"{iiii}"+"_488_0d00h00m00s000ms"+".tif"
//dir_out = dir_in;

// Select what to run
display = true;
save_to_folder = false;

// Start of the code
startTime = getTime();

// Create the output folder
dir_out = dir_in  + dir_out_name + "/"
File.makeDirectory(dir_out);

// Batch mode keeps everything that would display in the background
// Also making it faster
setBatchMode(true); //Start batch mode
// Loop over channels
n_folders = channel_folders.length
for(m=0; m<n_folders; m++){
	// Make sure we have directory present to process
	dir_in_sub = dir_in + channel_folders[m] + "/";
	if (File.isDirectory(dir_in_sub)){
		// Get unique names
		
		list = getFileList(dir_in_sub);
		list_no_duplicates = newArray(list.length);
		list_no_duplicates_split = newArray(list.length);
		list_split_same = "";
		j = 0;
		
		for (i=0; i<list.length; i++) {
			if (File.isFile(dir_in_sub + list[i])){
				if(startsWith(list[i], pattern_start)){
//					print(list[i]);
					list_split = split(list[i], "_");
					list_split_compare = list_split[0];
					if (list_split_compare != list_split_same){
//						print(list_split_same);
						list_split_same = list_split[0];
//						print(list_split_same);
						list_no_duplicates[j] = list[i];
//						print("--------------------------------");
//						print(list_no_duplicates[j]);
//						print("--------------------------------");
						j += 1;
					}
					
				}
			}
		}
		
		// Create a no duplicates list (with the right vector size) and name them uniquely
		list_no_duplicates_short = newArray(j);
		list_stitcher = newArray(j);
		
		for (i=0; i<j; i++) {
			list_no_duplicates_short[i] = list_no_duplicates[i];
			
			list_split_no_duplicates_short = split(list_no_duplicates_short[i], "_");
			// Create names to go into stitcher
			list_split_no_duplicates_short[list_split_swap_index] = list_split_swap;
			list_split_join = "";
			for (k=0; k<list_split_no_duplicates_short.length; k++) {
				if (k==0){
					list_split_join = list_split_no_duplicates_short[k];
				}
				else{
					list_split_join += "_"+list_split_no_duplicates_short[k];
				}
			}
			
			list_stitcher[i] = list_split_join;
//			print(list_stitcher[i]);
		}
		
		// Run stitcher 
		total_runs = list_stitcher.length;
		for (i=0; i<list_stitcher.length; i++) {
			
			file_names_pattern = list_stitcher[i];
			
			if (display){
				run(
					"Grid/Collection stitching", 
					"type=[Grid: snake by rows] order=[Right & Down                ]"+
					" grid_size_x="+tile_x+" grid_size_y="+tile_y+" tile_overlap="+tile_overlap+
					" first_file_index_i="+index_first_file+
					" directory=["+dir_in_sub+"]"+
					" file_names="+file_names_pattern+
					" output_textfile_name=TileConfiguration.txt"+
					" fusion_method=[Linear Blending] regression_threshold=0.30"+
					" max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50"+
					" compute_overlap computation_parameters=[Save computation time (but use more RAM)]"+
					" image_output=[Fuse and display]");
					
				// Select generated window
				selectWindow("Fused");
				// Generate new file name removing tile identifier 
				name_save_add = "_";
				list_split = split(list_no_duplicates_short[i], "_");
				list_split = "_"+list_split[list_split_swap_index];
				name_save = removeExtension(list_no_duplicates_short[i]);
				name_save = replace(name_save, list_split, "_stitched");
				
				saveAs("Tiff", dir_out+name_save);
				close();
				print("Done with "+i+1+"\\"+total_runs+": "+name_save);
			}
			if (save_to_folder){	
				run(
					"Grid/Collection stitching", 
					"type=[Grid: snake by rows] order=[Right & Down                ]"+
					" grid_size_x="+tile_x+" grid_size_y="+tile_y+" tile_overlap="+tile_overlap+
					" first_file_index_i="+index_first_file+
					" directory=["+dir_in_sub+"]"+
					" file_names="+file_names_pattern+
					" output_textfile_name=TileConfiguration.txt"+
					" fusion_method=[Linear Blending] regression_threshold=0.30"+
					" max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50"+
					" compute_overlap computation_parameters=[Save computation time (but use more RAM)]"+
					" image_output=[Write to disk]"+
					" output_directory=["+dir_out+"]");
			}
		}		
	}
	else{
		print("Directory "+m+1+"\\"+n_folders+" NOT PRESENT!: "+channel_folders[m]);
	}

	print("Done with "+m+1+"\\"+n_folders+": "+channel_folders[m]);
}
setBatchMode(false); //End batch mode
endTime = getTime(); 
calTimeInSeconds = (endTime - startTime)/1000;
print("Computation time: "+calTimeInSeconds+" s");

// Functions

function removeExtension(file_name){
	// Removes file extensions
	// Expects no zeros in name except suffix
	// Returns file name without extension
	
	split_name = split(file_name, ".");
	file_name_no_extension = replace(file_name, "."+split_name[1], "");
	
	return file_name_no_extension;
}