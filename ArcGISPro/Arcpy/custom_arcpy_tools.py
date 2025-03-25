""" Custom Arcpy TOOLS (cat)
Scripts for evaluating and manipulating workspace feature classes, automated ShapeFile download, and bulk loading into a Geodatabase
Final outputs of these processes are intended for downstream mapping, analysis and visualization in ArcGIS Pro
"""
import arcpy # allows for access to ArcGIS pro geoprocessing tools and workflow automation
import os # enables interaction with local system resources (paths to folders and files)
import requests # access data from the web
import zipfile ## need this to process and extract downloaded zipfiles later on
import pandas as pd ## use to check spreadsheet formatting


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


###====================== TOOL2: Takes an input feature class and lists detailed info for the field names, type, length, and unique value counts

def showFieldinfo(fc):
    """
    Outputs detailed field information for a given ArcGIS Feature Class.

    This function prints a summary of all fields in the provided Feature Class, including:
    - Field names
    - Field types (e.g., Text, Integer, Double)
    - Field length (applicable for Text fields)
    - Count of unique values for each field
    
    Additionally, it prints the total record count for the Feature Class.

    Args:
    -----
    fc (str): 
        The path to the Feature Class to be analyzed. Must be accessible within the current ArcPy workspace.
    
    Returns:
    --------
    None
        This function prints the summary information directly to the console. 
        It does not return any values.

    Example:
    --------
    >>> showFieldinfo("C:/Path/To/YourGDB.gdb/YourFeatureClass")
    Summary of Fields in Feature Class: YourFeatureClass
    Name                 Type         Length   Unique_Values
    OBJECTID             OID          -       100          
    Name                 String       50      24           
    Total Record Count:  100
    """
    record_count = arcpy.management.GetCount(fc)
    
    print(f"Summary of Fields in Feature Class: {fc}\n")
    print("Name                 Type         Length   Unique_Values")

    for field in arcpy.ListFields(fc):
        unique_ids = set()
        field_name= str(field.name)
        with arcpy.da.SearchCursor(fc,field_name) as cursor:
            for row in cursor:
                if row[0] is not None:
                    unique_ids.add(row[0])
        print( f" {field.name:20} | {field.type:10} | {str(field.length):5} | {str(len(unique_ids)):10}")
        
    print(f"\nTotal Record Count: {record_count}")
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
    #  why importing all tools, and not just a single one, is highly recommended

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

