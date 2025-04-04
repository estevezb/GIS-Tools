""" Custom Arcpy TOOLS (cat)
Scripts for evaluating and manipulating workspace feature classes, automated ShapeFile download, and bulk loading into a Geodatabase
Final outputs of these processes are intended for downstream mapping, analysis and visualization in ArcGIS Pro
"""
import arcpy # allows for access to ArcGIS pro geoprocessing tools and workflow automation
import os # enables interaction with local system resources (paths to folders and files)
import requests # access data from the web
import zipfile ## need this to process and extract downloaded zipfiles later on
import pandas as pd ## use to check spreadsheet formatting
import webbrowser
from IPython.display import IFrame

###################################################################################################################################################################
#  BE SURE TO INSTALL MAGIC LIBRARY: 
# step1 activate arcgispro-py3 environment: conda activate "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3"
# step2 install library: pip install python-magic-bin on windows, for unix system use conda install -c conda-forge python-magic

import magic ## to validate file type requested from web, custom shapefile download function will depend on this being installed

####################################################################################################################################################################


### How do use these scripts in my own work?:
## 1. Install the libraries mentioned above.

## 2. import all the tools by adding this line at the top of your script:

    #  import custom_arcpy_tools as cat

## 3. call the functions like this using the appropriate arguments: 
    
    ## To list attributes for all Feature classes in the workspace
    # cat.listFC_dataset_Attributes(workspace=None)

    ## To list detailed field info including unique value counts:
    # cat.showFieldinfo(fc)

    ## To create a folder in the same path as your python script
    # cat.get_path_mkfolder(make_folder=False,folder_name=None)

    ## To download and extract a shapefile dataset from a url
    # cat.downloadShapefile(url, target_folder=None):

    ## To load all shapefiles in a user specified path into a geodatabase
    # cat.loadShapefilesToGDB(gdb_path, shapefile_inputs)

    ## To access the ArcGIS Documentation from with a notebook or a stand-alone script as a new browser window
    # cat.open_arcgis_documentation(notebook=True)


    
#====================================================================================================================================================
###====================== TOOL1:  Check Feature Classes that exist in the workspace and their Characteristics

def listFC_dataset_Attributes(workspace=None): # accepts a workspace path parameter,By default uses the existing one if left as None
    """List feature classes in the workspace and checks their key attributes, such as SpatialReference , 
    geometry type, and coordinate systems
    Parameters:
    -----------
    workspace: str, optional
        The file path to the workspace (e.g., geodatabase path) containing the feature classes
        If none, the function will use the current ArcPy workspace
        If no workspace is set will raise an error telling you to set a a workspace

    Returns:
    --------
    None , if no workspace exists
    Otherwise,    Prints the details of all feature classes in the wksp , including
                - Feature Class Name
                - spatial reference name
                - spatial reference type
                - Geometry
                - Well-known ID of the spatial reference
                Also, warns if different spatial references or coordinate systems exists in the dataset
    Raises: 
    -------
    Value Error: 
        If no wksp is set or if not feature classes are found in the workspace
    Exception:
        For general errors that may occur during processing
    
    Example:
    # To list fc in a geodatabase
    >>> listFC_dataset_Attributes(r"c:/Path/To/Your/Workspace.gdb")

    # To use the current wksp already set in Arcpy
    >>> listFC_dataset_Attributes()
    """
    if workspace:
        arcpy.env.workspace= workspace

    if not arcpy.env.workspace:
        
        raise ValueError("No workspace is set! Please specify a workspace") #stops the program, calls out this error
        
        
    try:
        ## Get all the fc classes from the gdb
        list_fc = arcpy.ListFeatureClasses()
        wksp_path= arcpy.env.workspace
        print(f"Workspace is set here {wksp_path}\n")

        if not list_fc:
            print("No feature classes found in the workspace")
            return # exit the function if not fc found
        wkid_list = set()
        CS_types = set() 
        fc_counter= 0
        for fc in list_fc:
            desc= arcpy.Describe(fc) ## Use the Describe Object to access properties of a Feature class like its Spatial Reference

            sr = desc.SpatialReference
            wkid_list.add(sr.factorycode)
            CS_types.add(sr.type)
            fc_counter+=1
            
            print(f"Feature class: , {fc}, Spatial Reference name :, {sr.name}, Spatial Ref Type : {sr.type}, Geometry{desc.shapetype}, WKID: {sr.factorycode}")
            print("-"*150,"\n") # add line and space between prints
        
        print(f"\n{fc_counter} Feature classes found in the workspace path\n")
    
        if len(wkid_list) >1:
            print("Warning Different wkid detected among feature Classes: " , wkid_list)
        if len(CS_types) >1:
            print("Warning Different Coordinate Systems types found among Feature Classes: ", CS_types)
    except Exception as e:
        print(f"Error occurred. Description: {e}, Error Category: {type(e).__name__}")
    except arcpy.ExecuteError:
        arcpy.GetMessages(2)


###====================== TOOL2: Takes an input feature class and lists detailed info for the field names, type, length, and unique value and unique geometry (WKT) counts

def showFieldinfo(fc):
    """
    Outputs detailed field information for a given ArcGIS Feature Class.

    This function prints a summary of all fields in the provided Feature Class, including:
    - Field names
    - Field types (e.g., Text, Integer, Double)
    - Field length (applicable for Text fields)
    - Count of unique values for each field
    
    Additionally, it prints counts of total records and total unique Geometries (by Well-Known Text String) for the Feature Class

    Args:
    fc (str): 
        The path to the Feature Class to be analyzed. Must be accessible within the current ArcPy workspace.
    
    Returns:
    None
        This function prints the summary information directly to the console. 
        It does not return any values.

    Example:
    --------
    >>> showFieldinfo("C:/Path/To/YourGDB.gdb/YourFeatureClass")
    *Summary*
    Fields in the Polygon Feature Class: city_township_unorg

    Name                 Type         Length   Unique_Values
    OBJECTID             | OID        | 4     | 2744      
    Shape                | Geometry   | 0     | 2743      
    GNIS_FEATU           | Integer    | 4     | 2693      
    FEATURE_NA           | String     | 254   | 2249      
    CTU_CLASS            | String     | 25    | 3         
    COUNTY_GNI           | Integer    | 4     | 87        
    COUNTY_COD           | String     | 2     | 87        
    COUNTY_NAM           | String     | 100   | 87        
    POPULATION           | Integer    | 4     | 1312      
    SHAPE_Leng           | Double     | 8     | 2743      
    Shape_Length         | Double     | 8     | 2743      
    Shape_Area           | Double     | 8     | 2743      
    Combined_GNIS_IDs    | String     | 50    | 2743      

    Total Record Count: 2744, Total Geometry Count(by WKT): 2743
    Warning 1 Potential Duplicate Features Detected in the Feature Class
    """
    record_count = arcpy.management.GetCount(fc)[0]
    shape_type = arcpy.Describe(fc).shapeType
      
    print(f"*Summary*\n Fields in the {shape_type} Feature Class: {fc}\n")
    print("Name                 Type         Length   Unique_Values")


    geometry_set = set()
    with arcpy.da.SearchCursor(fc,["SHAPE@WKT"]) as cursor:
        for row in cursor:
            geometry_set.add(row[0])
    for field in arcpy.ListFields(fc):
        unique_ids = set()
        field_name= str(field.name)
        with arcpy.da.SearchCursor(fc,[field_name]) as cursor:
            for row in cursor:
                if row[0] is not None:
                    unique_ids.add(row[0])
        print( f" {field.name:20} | {field.type:10} | {str(field.length):5} | {str(len(unique_ids)):10}")
        
    print(f"\nTotal Record Count: {record_count}, Total Geometry Count(by WKT): {len(geometry_set)}")

    if record_count != len(geometry_set):
        print(f"Warning {(int(record_count)-len(geometry_set))} Potential Duplicate Features Detected in the Feature Class")
    return


###====================== TOOL3: Creates a sub-folder within the folder where your python script exists

### Example local folder Structure:
### Project Folder/
##  |---Script.py
##      |---Subfolder

## checks where the script is and makes a folder in that location
initial_dir= os.getcwd() # capture the initial directory before setting environment for arcpy
print("Initial working directory: ", initial_dir)

def get_path_mkfolder(make_folder=False,folder_name=None):
    """Get the path to your script or notebook and optionally creates a folder in at the same level
        rootFolder/
        |--ScriptFolder/
            |---Script.py
            |---New Folder

    Args:
        make_folder (bool, optional): Set to True to make a new folder. Defaults to False.
        folder_name (str, optional): Name of the Folder to be created. Defaults to None.
    Return:
        str: The path of the created folder, or the script directory
    """
    try:
        script_path=os.path.dirname(os.path.abspath(__file__))
        print("Running a python script file here: ", script_path)

        if make_folder and folder_name:
            subfolder_path = os.path.join(script_path,folder_name)

            #check if the folder exists 
            if not os.path.exist(subfolder_path):
                os.makedirs(subfolder_path)# make the folder
                print("Created subfolder at: ", subfolder_path)
            else:
                print("Folder already exists: ",subfolder_path)
            return subfolder_path # return subfolder path

        print("Script in this folder: ", script_path)
        return  script_path # return script path
    
    # handle typos, undefined paths
    except NameError:
        # handle cases where __file__ is not available , user is in a notebook
        script_path = initial_dir
        print("Running in a notebook here: ", script_path)
        if make_folder and folder_name:
            subfolder_path = os.path.join(script_path,folder_name)
            # check if folder exists
            if not os.path.exists(subfolder_path):
                os.makedirs(subfolder_path) # create the folder
                print("Created subfolder at: ", subfolder_path)
            else:
                print("Folder already exists: ", subfolder_path)
            return subfolder_path
        
        print("Script in this folder: ", script_path)
        return script_path


###===================  TOOL4: Automates ShapeFile dataset download: access, download and store new input shapefile dataset from a url 

 # Note: If the user does not specify the folder for storing the data, this function uses a previous function to get the user's script path
 # uses your scripts folder to create the target folder for storing data
    # fyi, this is the function that will get used if the user does not specify a path: get_path_mkfolder(True, "01 Data"). 
    #  thus, importing all tools in 'cat' script, and not just a single one, is highly recommended

def downloadShapefile(url, target_folder=None):
    """Access and download a shapefile from a url pointing to the shapefile

    Args:
        url (str): Url of the Shapefile. Uses the  requests library to access the file header 
            handles large file size by not streaming all content into memory if the file is above 200 megabytes
            downloads the zip file and then extracts to a local path
        target_folder(str, optional): path to the folder where files should be stored. 
            target_folder defaults to "01 Data" which is created in the same folder where the script exists
    Returns:
        Tuple of File paths, str:  Returns the path to the downloaded zip file
    """
    try:
        # Set up folders where data will be stored
        data_folder = target_folder if target_folder else get_path_mkfolder(True, "01 Data")
        print("Subfolder will be created within: ", data_folder)

        # Create folders for the zipfile download and to hold the extracted files
        file_path = os.path.join(data_folder, r"ShapeFile_Inputs\downloadedData.zip")
        extracted_zipFolder = os.path.join(data_folder, r"ShapeFile_Inputs\ExtractedZip") 
        
        # Check folders exist
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path)) # make the folder to hold the download if it does not exists
            print("Set the path for the download to: ", file_path)
        if not os.path.exists(extracted_zipFolder):
            os.makedirs(extracted_zipFolder) # make the folder to hold the extracted files if it does not exists
            print("Set the path for Extracted zip files to", extracted_zipFolder)

            # get the file size
            response_head= requests.head(url)

            if 'Content-Length' in response_head.headers:
                response_header= response_head.headers

                file_size = response_header['Content-Length']

                file_size_mb= round(int(file_size) / (1000000)) # convert bytes to megabytes
                print(f"Shapefile Data File size ~: {file_size_mb} megabytes")
            else:
                print("Content length header not found in response. Proceeding with download")

            # check file size
            if file_size_mb <200:
                # Download file
                response= requests.get(url)
                with open(file_path, "wb") as f:
                    f.write(response.content)

            else: # Download file in chunks
                response = requests.get(url, stream=True)
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536): # chunk size to load into memory from the response
                        if chunk:
                            chunk.write(response.content)

            print("Download Successful")

            ## Validate the filetype is zip
            if magic.from_file(file_path, mime=True) == "application/zip": # extracts, checks the filetype
                print("Extracting data from zip file...")
                # read the zip file
                with zipfile.ZipFile(file_path, "r") as zip_f:
                    zip_f.extractall(extracted_zipFolder) # extract the zipfile to the target folder
                    print("Extraction complete. Files extracted to", extracted_zipFolder)

            else:
                print("Error : Downloaded file is not a valid zip file")
                return None, None
            
            return extracted_zipFolder, file_path
        
    # handle url request errors
    except requests.exceptions.RequestException as e:
        print(f"Error occurred during the Download{e}")
        return None
    # handle general errors
    except Exception as e:
        print("Unexpected error", e, type(e).__name__)
        return None, None 





###====================== TOOL5:  Loads all the shapefiles in a user specified local folder into a local ArcGIS Geodatabase


def loadShapefilesToGDB(gdb_path, shapefile_inputs):
    """Loads all shapefiles in a folder into a geodatabase

    Args:
        gdb_path (str): Path to the geodatabase
        shapefile_inputs (str): Path to the folder holding the shapefiles

    Returns:
        list: Returns  a list of shapefile paths that were used for loading into the GDB, or an emtpy list if no shapefiles were processed
    """
    try:
        # use extracted zipfiles if the path exists, otherise use the specified path to the files
        if not shapefile_inputs or not os.path.exists(shapefile_inputs):
            print("Invalid path to shapefile folder provided")
            return [] # return empty list
        
        # Loop through the folder with extracted files and compile a list of all the shape file paths
        shapefile_list = [] # start an empty list to hold .shp files

        for f in os.listdir(shapefile_inputs):
            if f.endswith(".shp"):
                full_shp_path= os.path.join(shapefile_inputs,f) # get the full path for each file
                shapefile_list.append(full_shp_path) # add to a list

        ###================================  Batch Convert shapefile to Feature classes in the Gdb
        # check the list of shp files exists
        if not shapefile_list:
            print("no shape files found for extraction")
            return []
        
        else:
        ## Load the shapefiles into the gdb
            ### TOOL: arcpy.conversion.FeatureClassToGeodatabase(Input_Features, Output_Geodatabase)
            arcpy.conversion.FeatureClassToGeodatabase(shapefile_list,gdb_path)
            print(f" Successfully Loaded shapefiles into into the {gdb_path}")
            
            return shapefile_list
    
    except Exception as e:
        print("Error Loading Shapefiles into the GDB ", e, type(e).__name__)
    except arcpy.ExecuteError:
        print("Arcpy Error: ", arcpy.GetMessages(2)) 


###===================  TOOL6: Access the ArcGIS Pro documentation from with a notebook or a stand-alone script as a new window



def open_arcgis_documentation(notebook=True):
    """
    Displays or opens the ArcGIS geoprocessing tools documentation.

    This function points directly to the ArcGIS Pro documentation URL
    for geoprocessing tools. It will either display the URL in an iframe
    (when running in Jupyter Notebook) or open the URL in the user's
    default web browser (when running as a standalone script).

    Args:
        notebook (bool, optional): 
            - If True, displays the documentation in a Jupyter Notebook using an iframe.
            - If False, opens the documentation in the default web browser.
            Defaults to True.

    Returns:
        None
    """
    # Fixed URL for ArcGIS geoprocessing tools documentation
    tool_url = "https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/basics/find-geoprocessing-tools.htm"
    
    try:
        if notebook:
            # Display documentation in Jupyter Notebook iframe
            return IFrame(tool_url, width="100%", height="600px")
        else:
            # Open documentation in the web browser
            webbrowser.open(tool_url)
            print(f"Opening documentation in web browser: {tool_url}")
    except Exception as e:
        print(f"Error accessing documentation: {e}")


###===================  TOOL7: Detect Ovelapping Features within a Feature Class using PairwiseIntersect


def check_Fc_NonselfOverlap(input_fc, output_fc_name):
    """ Detects overlapping features within a feature class using PairwiseIntersect.
        Returns duplicate pair object ID and count
    Args:
        input_fc (str): Full path or name of the feature class
        output_fc_name: output feature class name for PairwiseIntersect results
    Returns:
        count (int) : number of overlapping features 
        overlap_ids (list):  list of Object IDs of overlapping features 
        output_fc (str) : Name of the output overlap feature class 
    Example:
    --------
    fc = "city_township_unorg"
    input_fc = fc 
    output_fc_name = "overlap_check2"

    >>> check_Fc_NonselfOverlap(input_fc, output_fc_name)
        Successfully completed PairwiseIntersect Analysis
        Successfully filtered PairwiseIntersect features
        PairwiseIntersect detected 1 overlaps for the following objects Ids: 
        [2745]
        (1, [2745], 'overlap_check2')
    """
    # Check for overlap within a feature class of CTU polygons

    base_name = os.path.basename(input_fc)
    safe_name= arcpy.ValidateTableName(base_name) 
    field_name= f"FID_{safe_name}"
    field_name_1= f"FID_{safe_name}_1"
    where_c = f"{field_name} > {field_name_1}"
    out_fc = output_fc_name
    overlapping_ids_list= set()

    try:
    ### TOOL: arcpy.analysis.PairwiseIntersect(in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {output_type})
        arcpy.analysis.PairwiseIntersect([input_fc, input_fc], out_fc, join_attributes="ONLY_FID") # We only want FID to track which of the original ObjectIDs overlap
        print("Successfully completed PairwiseIntersect Analysis")

        with arcpy.da.SearchCursor(out_fc,[field_name],where_clause=where_c) as cursor:
            for row in cursor:
                dup_id = row[0]
                overlapping_ids_list.add(dup_id)

    ### =========================   Filter for actual overlaps (not self-intersections)
    ### Step1: Create a temporary layer from the pairwise overlap feature class
    ### Step2: Select those paired features whose FID values do not match, overlapping features
    ### Step3: Count the number of those overlapping features

        ### TOOL: arcpy.management.MakeFeatureLayer(in_features, out_layer, {where_clause}, {workspace}, {field_info})
        arcpy.management.MakeFeatureLayer(out_fc, "overlap_lyr")

    ### TOOL: arcpy.management.SelectLayerByAttribute(in_layer_or_view, {selection_type}, {where_clause}, {invert_where_clause})
        arcpy.management.SelectLayerByAttribute("overlap_lyr", "NEW_SELECTION",
                                            where_c) # keep only one intersection of the pair (A->B) to clearly mark one overlap 
        print("Successfully filtered PairwiseIntersect features")
        
        count = int(arcpy.management.GetCount("overlap_lyr")[0])
        print(f" PairwiseIntersect detected {count} overlaps for the following objects Ids: \n{list(overlapping_ids_list)}")

        return count, list(overlapping_ids_list), out_fc

    except Exception as e:
        print("Error Occurred", e, type(e).__name__)
    except arcpy.ExecuteError:
        print("ArcPy Error", arcpy.GetMessages(2))