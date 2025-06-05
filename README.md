# GIS Tools Repository

A Repository of GIS Tools, including ArcGISPro Scripts and Tools

## Overview
This repository primarily contains a collection of GIS tools designed for use in ArcGIS Pro. It includes custom ArcPy scripts, geoprocessing workflows, and tools for streamlining data processing and analysis related to spatial datasets. Also, included are tools for analysis of UAV data, including a ground control point pixel coordinate extraction tools for use with Open Drone Map Ground control point workflows.

The tools focus on automating workflows, enhancing geospatial data preprocessing, or performing very specific custom tasks like damage classification and raster band extraction.

## Folder Structure
GIS Tools/

├── ArcGISPro/

│   ├── Arcpy/

|           |── custom_arcpy_tools.py

│   ├── DamageClassification_WorkFlowTools/

│   │      ├── BuildingDamage.atbx

│   │      ├── BuildingDamage_PreprocessingToolBox.zip

│   │      ├── Instructions Installing and Using Tool in ArcGIS Pro.txt

│   │      ├── extractBands_exportRaster.py

│   │      

│   ├── DataValidation

│   ├── UAV

├── README.md

## Features
Building Damage Assessment:

- Tools for assessing and classifying building damage using spatial datasets.

- Includes preprocessing workflows and advanced toolbox utilities.

Raster Band Extraction:

- Script to extract specific bands from raster datasets and export as new raster layers.

Custom ArcPy Tools:

- Collection of functions and utilities to enhance geospatial workflows, including shapefile processing and conversions to geodatabases.

Detailed Instructions:

- Instructions Installing and Using Tool in ArcGIS Pro.txt guides users on installation and usage.

## Requirements
Software:

- ArcGIS Pro

- Python (ArcPy)

Libraries:

- Python packages: arcpy, os, requests, zipfile, magic (if applicable)

Ensure ArcGIS Pro is properly installed and licensed.

## Installation
Clone the repository to your local machine:

```bash
git clone https://github.com/estevezb/GIS-Tools.git
cd GIS-Tools
```
Install any required Python packages --use ArcGIS Pro's built-in Python environment or your custom environment

## Example Custom Tool Usage: ArcGIS Pro Damage Classification tools
- Load and configure the tools in ArcGIS Pro:

- Unzip the toolbox files (BuildingDamage_PreprocessingToolBox.zip).

- Add the .atbx toolbox to your ArcGIS Pro project.

- Use the provided scripts (extractBands_exportRaster.py, custom_arcpy_tools.py) for specific tasks:

Run the scripts within ArcGIS Pro’s Python window or an external Python IDE with ArcPy enabled.

## Instructions
Refer to the following resources for detailed steps:

Installing and Using Tools:

Instructions Installing and Using Tool in ArcGIS Pro.txt provides detailed setup instructions.

## ArcPy Function Descriptions:

Review the comments and documentation within scripts for code-level guidance.

## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests for improvements or additional tools.

## License
This repository is licensed under the MIT License. See the LICENSE file for more information.

## Contact
For questions or support, contact bestevez100@gmail.com