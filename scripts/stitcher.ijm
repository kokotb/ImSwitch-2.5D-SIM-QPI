// Author: Boštjan Kokot, Laboratory of Biophysics (Condensed Matter Department - F5, Jozef Stefan Institute)
// Intended for internal use
// Contact: bostjan.kokot@ijs.si
// Webpage: lbf.ijs.si
// Created:  23.01.2025              
// Modified: 23.01.2025 (save date is more recent)

// Current version will probably work on a folder
// Next upgrade would be to package the elaborate finding of duplicates into functions

// Set parameters
dir_in = "D:/Nextcloud/2022 - 2.5D SIM - share/Measurements/250123 - Testing_saving_metada/241003161441_488MTG_10by10_10over/WF";
dir_out_name = "exp"
index_first_file = 0;
file_names_pattern = "f0000_pos"+"{iiii}"+"_488_0d00h00m00s000ms"+".tif"
dir_out = dir_in;
tile_x = 10;
tile_y = 10;
tile_overlap = 10; // 0-100 %
pattern_start = "f";
list_split_swap = "pos{iiii}";
list_split_swap_index = 1;

// Select what to run
display = false;
save_to_folder = true;

// Start of the code
startTime = getTime();

// Create the output folder
dir_out = dir_in + "/" + dir_out_name
File.makeDirectory(dir_out);

// Get unique names
list = getFileList(dir_in);
list_no_duplicates = newArray(list.length);
list_no_duplicates_split = newArray(list.length);
list_split_same = ""
j = 0

print(dir_in+list[1])
for (i=0; i<list.length; i++) {
	if (File.isFile(dir_in + "/" + list[i])){
		if(startsWith(list[i], pattern_start)){
			print(list[i]);
			list_split = split(list[i], "_");
			list_split_compare = list_split[0];
			if (list_split_compare != list_split_same){
				print(list_split_same);
				list_split_same = list_split[0];
				print(list_split_same);
				list_no_duplicates[j] = list[i];
				print("--------------------------------");
				print(list_no_duplicates[j]);
				print("--------------------------------");
				j += 1;
			}
			
		}
	}
}


// Create a duplicateless list
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
	list_stitcher[k] = list_split_join;
	print(list_stitcher[k]);
}

//list_split[list_split_swap_index] = list_split_swap;
//
//// Create names to go into stitcher
//print(list_split.length);
//list_split_join = "";
//for (i=0; i<list_split.length; i++) {
//	if (i==0){
//		list_split_join = list_split[i];
//	}
//	else{
//		list_split_join += "_"+list_split[i];
//	}
//}
//print(list_split_join);

setBatchMode(false); //Start batch mode

// Run stitcher 
for (i=0; i<list_stitcher.length; i++) {
	file_names_pattern = list_stitcher[i];
	if (display){
		run(
			"Grid/Collection stitching", 
			"type=[Grid: snake by rows] order=[Right & Down                ]"+
			" grid_size_x="+tile_x+" grid_size_y="+tile_y+" tile_overlap="+tile_overlap+
			" first_file_index_i="+index_first_file+
			" directory=["+dir_in+"]"+
			" file_names="+file_names_pattern+
			" output_textfile_name=TileConfiguration.txt"+
			" fusion_method=[Linear Blending] regression_threshold=0.30"+
			" max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50"+
			" compute_overlap computation_parameters=[Save computation time (but use more RAM)]"+
			" image_output=[Fuse and display]");
	}
	
	if (save_to_folder){	
		run(
			"Grid/Collection stitching", 
			"type=[Grid: snake by rows] order=[Right & Down                ]"+
			" grid_size_x="+tile_x+" grid_size_y="+tile_y+" tile_overlap="+tile_overlap+
			" first_file_index_i="+index_first_file+
			" directory=["+dir_in+"]"+
			" file_names="+file_names_pattern+
			" output_textfile_name=TileConfiguration.txt"+
			" fusion_method=[Linear Blending] regression_threshold=0.30"+
			" max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50"+
			" compute_overlap computation_parameters=[Save computation time (but use more RAM)]"+
			" image_output=[Write to disk]"+
			" output_directory=["+dir_out+"]");
	}
}

setBatchMode(false); //End batch mode
endTime = getTime(); 
calTimeInSeconds = (endTime - startTime)/1000;
print("Computation time: "+calTimeInSeconds+" s");