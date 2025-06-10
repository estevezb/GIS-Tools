#!/usr/bin/env python
# coding: utf-8

# In[ ]:

""" =======================================================================================================
        SCHEMA GUIDED ETL WORKFLOW: Load CSV INPUTS to ArcGIS Geodatabase Using a Feature Class Schema  
    =======================================================================================================

    This script enables use of a pre-defined feature class schema to align, clean, and load csv file inputs into a file geodatabase.
    Assumes there is an existing feature class with a defined schema. Displays a GUI for required user inputs: paths and field names.
    

    REQUIRED USER INPUTS:
    
    The user will be prompted with a new window for 4 inputs:
        - Geodatabase folder path
        - Input csv file path
        - Feature class name with a known schema 
        - Input table field names to be mapped to the schema

        Note: User will be prompted to add a field when that field exists in the Schema but not in the input table
"""
import arcpy
import pandas as pd
import usaddress
import logging
import os 
import sys
import tempfile
import easygui

# Logging configuration all log messages at INFO level and above (including WARNING, ERROR, and CRITICAL) are written to etl_process.log.
logging.basicConfig(filename="etl_process.log", 
                    filemode="w", # w=overwrite the logfile, "a" = append to the log
                    level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s"
)
print("Logging to:", os.path.abspath("etl_process.log"))

# In[ ]:


##================================================================
## =============================== Main ETL Workflow : User Inputs
##================================================================

## =============================== Set Paths to inputs and outputs
# prompt for geodatabase
gdb_path = easygui.diropenbox(msg= "Select the geodatabase folder (.gdb)", default= os.getcwd())
if not gdb_path or not gdb_path.lower().endswith(".gdb"):
    print("No geodatabase selected or the selected file is not a geodatabase (.gdb). Exiting")
    sys.exit()

# promot for input csv
input_table = easygui.fileopenbox(msg="Select the input CSV file", default= os.getcwd() +"/*.csv")
if not input_table:    
    print("No input table selected. Exiting")
    sys.exit()


if not os.path.exists(gdb_path) or not os.path.exists(input_table):
    print("Geodatabase or input table was not found. Ensure correct path was input")
    logging.error("File not found Error gdb_path=%s, input_table=%s", gdb_path, input_table)
    raise FileNotFoundError (f"Missing {gdb_path if not os.path.exists(gdb_path) else ''} {input_table if not os.path.exists(input_table) else ''}")

validation_issues_path = os.path.join(gdb_path,"ValidationIssues.csv")

try:
    arcpy.env.workspace = gdb_path
    arcpy.env.overwriteOutput = True
    print(f"\nSetting workspace to: {gdb_path} and searching for Feature Classes...\n")
    logging.info("Setting workspace to %s", gdb_path)
    for fc in arcpy.ListFeatureClasses():
        print(f"Feature classes found:{fc}")
        logging.info("Feature classes found %s", fc)
except arcpy.ExecuteError:
    print(arcpy.GetMessages())
    logging.error("Arcpy Error occured %s", arcpy.GetMessages())



## ===============================  Select a feature class to use as a template Schema 

# prompt for feature class
featureClass_name= easygui.enterbox(msg="Enter Feature Class name or pattern (e.g., *Address*)", default= "*Address*") # specify feature class name, * use wildcard partial matching or full name

if not featureClass_name:
    print("No Feature class name entered. Exiting")
    sys.exit()

# Check fc exists
try:
    
    template_fc = arcpy.ListFeatureClasses(featureClass_name)[0] # existing feature class
    logging.info("Feature class loaded %s", template_fc)
    print("Feature class loaded", template_fc)
    if not arcpy.Exists(template_fc):
        print("Feature class not found")

except arcpy.ExecuteError():
    print(arcpy.GetMessages())
    logging.error("Arcpy Error occured %s", arcpy.GetMessages())

## =============================== Define the field mappings to use:
# Extract schema dynamically
def get_schema(feature_class):
    """Extract the schema (field names and types) from a given feature class, excluding system fields.

    Args:
        feature_class (str): The path to the feature class from which to extract the schema.

    Returns:
        dict: A dictionary mapping field names to their ArcGIS field types.
    """
    logging.info("Extracting schema from geodatabase...")
    print("Extracting schema from geodatabase...")
    fields = arcpy.ListFields(feature_class)
    # extract dictionary of field names and data type for select fields to build a schema from template feature class
    schema = {field.name: field.type for field in fields if field.name not in ["OBJECTID", "Shape", "created_user","created_date","last_edited_user","last_edited_date"]}
    return schema

# Get feature class schema
schema = get_schema(template_fc)
schema_fields = list(schema.keys())

# Read input table columns for default mapping suggestions
df = pd.read_csv(input_table) # need to load to reconcile potential field additions
input_df = pd.read_csv(input_table, nrows=1)
input_columns = list(input_df.columns)
default_values = [col if col in input_columns else '' for col in schema_fields] # extract the exact matches

# prompt for user input with default values displayed
user_values = easygui.multenterbox(
    msg="Map each schema field to an input column name (Defaults Displayed):",
    title="Field Mapping",
    fields=schema_fields,
    values=default_values
)
if user_values:
    field_mapping_dict = dict(zip(schema_fields, user_values))

# Ensure all mapped columns exist in the DataFrame, add missing

for schema_field, input_col in field_mapping_dict.items():
    if input_col and input_col not in input_columns:
        # prompt user for a default value for the new column
        default_val = easygui.enterbox(msg=f"Input column '{input_col}' for schema field '{schema_field}' \n" 
                                       f"does not exist in the input CSV file\n"
                                       f" Enter a default value for the new column (leave blank for an empty string): ", 
                                       title="Add Missing Column")
        if default_val is None:
            default_val = ""

        # add missing columns (i.e., only present in the feature class schema) to the input table
        df[input_col]= default_val
        # Update input table for missing columns
        df.to_csv(input_table,index=False)
        print(f"Added missing column {input_col} with default value {default_val} to input table")
        logging.info(f"Added missing column {input_col} with default value {default_val} to input table")


##============================================================
## =============================== End of User Inputs
##============================================================


# Validate and clean data
def clean_and_align_data(df, schema, field_mapping_dict, standardize_address=False):
    """Validate, clean, and align a DataFrame to match a target ArcGIS schema.

    This function renames columns, coerces data types, checks for missing values and duplicates, optionally standardizes addresses,
    and saves validation issues to a CSV file.

    Args:
        df (pd.DataFrame): The input DataFrame to clean and align.
        schema (dict): Dictionary mapping schema field names to ArcGIS field types.
        field_mapping_dict (dict): Mapping from schema field names to input column names.
        standardize_address (bool, optional): Whether to standardize addresses using usaddress. Defaults to False.

    Returns:
        pd.DataFrame: The cleaned and aligned DataFrame.
    """
    logging.info("Starting data validation and cleaning...")
    print("Starting data validation and cleaning...")
    validation_issues = []

    # Rename columns to match schema
    #  df.rename(columns={old:new}), in rename normally keys (k) are old names while value (v) is new, flipped to rename here {input_col: schema_field}
    df = df.rename(columns={v: k for k, v in field_mapping_dict.items()})
    for field, dtype in schema.items():
        if field in df.columns:
            # Handle ArcGIS types
            if dtype in ["Short", "Long", "Integer"]:
                df[field] = pd.to_numeric(df[field], errors="coerce").astype("Int64")
            elif dtype in ["Float", "Double"]:
                df[field] = pd.to_numeric(df[field], errors="coerce")
            elif dtype in ["Text", "String"]:
                df[field] = df[field].astype(str)
            elif dtype == "Date":
                df[field] = pd.to_datetime(df[field], errors="coerce")


    # Check for missing values
    missing_values = df[df.isnull().any(axis=1)]
    if not missing_values.empty:
        validation_issues.append(missing_values)
        logging.warning(f"Found {len(missing_values)} rows with missing values.")
        print(f"Found {len(missing_values)} rows with missing values.")

    # Check for duplicate records
    num_duplicates = df.duplicated().sum()

    if num_duplicates > 0 :
        logging.warning(f"{num_duplicates} duplicate rows found and removed")
        print(f"{num_duplicates} duplicate rows found and removed")
        df[df.duplicated(Keep=True)].to_csv("duplicates_found.csv", index=False)

    else:
        logging.info("No duplicate rows found")
        print("No duplicate rows found")

    # Drop duplicates
    df = df.drop_duplicates()

    # Optional: Standardize addresses
    if standardize_address:
        logging.info("Standardizing addresses using usaddress library...")
        print("Standardizing addresses using usaddress library...")
        def parse_address(addr):
            try:
                parsed = usaddress.tag(addr)[0]
                return f"{parsed.get('AddressNumber', '')} {parsed.get('StreetName', '')} {parsed.get('StreetNamePostType', '')}"
            except:
                return addr  # Keep original if parsing fails

        df["address"] = df["address"].apply(parse_address)

    # Save validation issues
    if validation_issues:
        validation_issues_df = pd.concat(validation_issues)
        validation_issues_df.to_csv(validation_issues_path, index=False)
        logging.info("Validation issues saved to CSV.")
        print("Validation issues saved to CSV.")

    return df

### Load data into geodatabase
# Use tempfile for temp CSV
def load_to_gdb(df, table_name, field_mappings=None):
    """Load a DataFrame into a geodatabase table using arcpy.TableToTable, with optional field mappings.

    Args:
        df (pd.DataFrame): The DataFrame to load.
        table_name (str): The name of the output table in the geodatabase.
        field_mappings (arcpy.FieldMappings, optional): FieldMappings object for schema alignment. Defaults to None.

    Returns:
        None
    """
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        temp_csv = tmp.name
        df.to_csv(temp_csv, index=False)
        logging.info(f"Loading {table_name} into geodatabase...")
        print(f"Loading {table_name} into geodatabase...")
        arcpy.conversion.TableToTable(temp_csv, gdb_path, table_name, field_mapping=field_mappings)
        logging.info(f"{table_name} successfully loaded into geodatabase.")
        print(f"{table_name} successfully loaded into geodatabase.")
    # Optionally, remove temp file after use
    os.remove(temp_csv)

### Map input table fields to the schema of an existing feature class
def map_fields(input_table, template_fc, field_mapping_dict):
    """Build arcpy.FieldMappings for mapping input table fields to a template feature class schema.

    Args:
        input_table (str): Path to the input table (CSV or table).
        template_fc (str): Path to the template feature class.
        field_mapping_dict (dict): Mapping from schema field names to input column names.

    Returns:
        arcpy.FieldMappings: Configured FieldMappings object for use in TableToTable.
    """
    field_mappings = arcpy.FieldMappings()
    ### iterate through each pair of pre-defined mappings and Create a FieldMap() for each field
    for schema_field, input_col in field_mapping_dict.items():
        # Create a FieldMap for each field
        fm= arcpy.FieldMap()
        # add the input field from csv
        fm.addInputField(input_table,input_col)
        # Set the output field name to match the schema
        out_field = fm.outputField
        out_field.name = schema_field 

        ### set the type  / length/ alias from the template feature class
        # loop uses the current schema field to access the feature classes field properties
        for f in arcpy.ListFields(template_fc):
            if f.name == schema_field: ### if name matches current schema field
                out_field.type = f.type # set outfield properties to match current field
                out_field.length = f.length
                out_field.aliasName= f.aliasName
                break # exit f loop after match is found and set
        fm.outputField = out_field # finalize field settings
        # Add the FieldMap to the FieldMappings
        field_mappings.addFieldMap(fm)
    return field_mappings

### Extract working directory from notebook or script path
try: 
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("python script located here", script_dir)
    logging.info("python script located here %s", script_dir)
    wkdir=script_dir
except NameError:
    notebook_dir= os.getcwd() # Assumes you only launched Jupyter Notebook when you opened the current notebook file  
    print("notebook located here", notebook_dir)
    logging.error("notebook located here %s", notebook_dir)
    wkdir= notebook_dir


# Print a Summary of user mappings
print("\nField Mapping Summary:\n")
print("{:<20} | {:<20}".format("Schema Field","Input Column"))
print("*"*43)

for schema_field, input_col in field_mapping_dict.items():

    print("{:<20} | {:<20}".format(schema_field,input_col))

logging.info("ETL process started...")
print("\nETL process started\n")

try:
    arcpy.env.workspace = gdb_path
    arcpy.env.overwriteOutput = True
    print(f"Setting workspace to: {gdb_path}")
    logging.info("Setting workspace to %s", gdb_path)
    for fc in arcpy.ListFeatureClasses():
        print(f"Feature classes found:{fc}")
        logging.info("Feature classes found %s", fc)
except arcpy.ExecuteError:
    print(arcpy.GetMessages())
    logging.error("Arcpy Error occured %s", arcpy.GetMessages())

# Check fc exists
try:
    
    template_fc = arcpy.ListFeatureClasses(featureClass_name)[0] # existing feature class
    logging.info("Feature class loaded %s", template_fc)
    print("Feature class loaded", template_fc)
    if not arcpy.Exists(template_fc):
        print("Feature class not found")

except arcpy.ExecuteError():
    print(arcpy.GetMessages())
    logging.error("Arcpy Error occured %s", arcpy.GetMessages())



# Load the input table

# Clean and align input data to schema names and data format
cleaned_df = clean_and_align_data(df, schema, field_mapping_dict, standardize_address=False)

### Map the fields in the input table to the feature class schema 
field_mappings = map_fields(input_table, template_fc, field_mapping_dict)

# Load cleaned data and validation issues into geodatabase
load_to_gdb(cleaned_df, "CleanedData", field_mappings)
load_to_gdb(pd.read_csv(validation_issues_path), "ValidationIssues")
load_to_gdb(df, "InputAddressData")

logging.info("ETL process completed successfully.")
print("ETL process completed successfully.")
logging.shutdown()
