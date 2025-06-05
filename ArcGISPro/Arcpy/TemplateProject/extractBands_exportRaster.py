# Esri start of added imports
import sys, os, arcpy
# Esri end of added imports

# Esri start of added variables
g_ESRI_variable_1 = '#'
# Esri end of added variables

import arcpy
import os 


###================== Set up folders and settings 

# set input raster, output folder and raster name
input_raster = arcpy.GetParameterAsText(0) # get input raster path
output_folder = arcpy.GetParameterAsText(1) # get output folder
output_raster_name = arcpy.GetParameterAsText(2) # get the raster name
output_cell_size = arcpy.GetParameterAsText(3) # get the desired cell size
# combine to make output file path
output_raster = os.path.join(output_folder, output_raster_name+ ".tif")

# Set environment workspace and enable output overwrite option
arcpy.env.workspace = output_folder
arcpy.env.overwriteOutput=True



###================== Extract bands and save the raster as 8-bit TIF  

try:
    extracted_raster = arcpy.ia.ExtractBand(input_raster,[1,2,3],missing_band_action='Fail' )


    # Delete the temporary raster before reusing the same name
    if arcpy.Exists("in_memory\\temp_raster"):
        arcpy.Delete_management(g_ESRI_variable_1)
    
    # save the output raster temporarily
    temp_raster = g_ESRI_variable_1
    extracted_raster.save(temp_raster)

    # resample to 0.1 meter per pixel
    resampled_raster= os.path.join(output_folder,"resampled_temp.tif")
    arcpy.management.Resample(temp_raster,resampled_raster,cell_size=output_cell_size, resampling_type="BILINEAR")
    

    # copy to specify the no data value converting 0,0,0 pixels to NoData rather than 0,0,0 pixel appearing as black after removing the alpha channel
    # convert to 8-bit unsigned with proper scaling if not already done.
    arcpy.management.CopyRaster(resampled_raster,output_raster,pixel_type="8_BIT_UNSIGNED", scale_pixel_value="ScalePixelValue",nodata_value=0, format="TIFF") # no data value is 0, change if your no Data value is different

    # Display the output in ArcGIS
    arcpy.SetParameterAsText(4,output_raster)
    
    # add success message (green text) to show it completes
    arcpy.AddMessage(f"Saved resampled raster with NoData value applied at {output_raster}")

except Exception as e:
    arcpy.AddError(f"Error processing raster: {str(e)}") # critical errors that cause failure (red text)
    arcpy.AddMessage(arcpy.GetMessages()) # show all messages, missing inputs, updates, success messages
