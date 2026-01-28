# Name:

Moving Lines, version 1.64

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1478125.svg)](https://doi.org/10.5281/zenodo.1478125)

~~Get the compiled versions for MAC OS and Windows at:
[https://github.com/samuelleblanc/fp/releases/tag/v1.44]~~   compiled versions not longer maintained, use conda install now (see below)
    
# Purpose:
    
Flight Planning software for creating flight plans for Airborne Science
    
Creates a visual map interface and backend calculations to a spreadsheet flight planning tool
Takes advantage of clickable map for creating a flight plan, and already existing Excel software
    
# Install: 

## Install code from the anaconda package manager (recomended):
1)  If you don't have a anaconda / miniconda / mamba install, please do so. Recommendation to install miniconda following this link [https://www.rho-signal-effective-analytics.com/modules/pre-course/miniconda-installation/].  
    Ensure that the base environment is activated: `conda activate`  
2)  From the command line, create a new environment based on python 3.9, activate it, then install the movinglines package (using mamba is faster than conda).
	```
	conda create -n ml python=3.9
	conda activate ml
	mamba install -c samuelleblanc movinglines
	```  
   *for current conda/anaconda install, without mamba/miniconda/miniforge replace last line with*
	```
	conda install samuelleblanc::movinglines
	```    
 if you encounter errors with conda, ensure that you have the conda-froge channel in conda (it is automatic for mamba)
	```
 	conda config --add channels conda-forge
 	```    
 for ensuring that you only use conda-forge, without breaching licensing issues with anaconda default channels, please look at: [https://conda-forge.org/docs/user/transitioning_from_defaults/]
  
3)  Go through and accept the install of the required packages
4)  at the command line, start the lines software by typing `ml`

   *or*

## For compiled versions: **No longer Maintained**
1) Download appropriate zip file and extract to desired location
2) run the executable (ml for OSX, ml.exe for Win)
        for OSX:
            - ~~run from command line, must cd to directory hosting the ml exectuable~~
            - executable version of OSX is being phased out, please use the conda install method above
        for Windows:
            - double click the ml.exe icon  

   *or*  
## For python installs:
1) `pip install movinglines` (or the conda method descried above)
2) at a command line, start the moving lines software by typing `ml`  
	
# Quick Start: 
    1) Select the mapping profile (defaults to most recent campaign), can change the map boundaries, take-off time, utc offset, projection
    2) wait about 30seconds
    3) Enter date of planned flight in dialog in format yyyy-mm-dd
    4) wait for map to initialize and excel to load
	5) move cursor over map to refresh map
    6) create points, move points by clicking, or by manually entering in excel spreadsheet
    7) Once happy save all the figures, files, excel files, kml files by either selecting each point, or by pressing the 'saveall' button
    
## Adding points:
    1) click and drag on map to create new point 
    2) modify altitudes, speed, or other properties of new point in excel spreadsheet
  *or*
  
    1) enter lat and lon in excel spreadsheet, optionally altitude and speed, delay time, start time
    2) move cursor over map area to refresh *or* press green refresh button
  *or*
  
    1) Press the 'add' button next to 'points:'
    2) Follow the dialog *tip: use the 'between 2 points' for easy adding*
  *or*
	
	1) add a flight module with the button 'flt_module'
	2) see below or follow dialogs
    
## Moving points
    1) Click on point on map, and then drag
*or*
    
    1) change coordinates in Excel spreadsheet
    2) move cursor over map area to refresh
*or*

    1) Use the 'Move' button and select points to move, then follow dialog
    
## Delete points
    1) delete line from the excel spreadsheet
    2) move cursor over map to refresh
    
## Use flt modules for prepared flight plans (similarly to macros)
    1) Select button: 'Add flt module'
    2) select the flt module from the radiobutton list
    3) enter the quantities demanded from the flt file
    
## Creating a flt module (or macro)
    1) in the flt_module folder create a text file
    2) the text file name should be descriptive of the macro with an extension '.flt'
    3) first line starts with the percent sign '%' then a list of variables to be used
    4) Comments can be included, but only at the start of the line, denoted with a hash '#' sign
    5) each subsequent line is a move command, which can use simple math and the variables defined in the first line
    6) format of the lines are: bearing,distance,altitude
        where the bearing is the azimuth angle of the plane
        where the distance is the length of that leg
        where the altitude (which can be omitted) is the altitude of the plane for the next waypoint
    7) enter number of points desired for macro then save in the flt_module directory. It is ready to be used in the software without the need for a restart.
    8) if desired, make a screenshot of the resulting flt_module and save it with the same name in the flt_module folder as a .png
    
## Adding other planes or flight paths:
    1) Press the 'New Flight Path' button
    2) Enter name of new flight path. If it contains the name of a plane (e.g. p3, er2, dc8, c130,baer), will use the predefined speeds for that plane
    3) New flight path will have different color

## Adding figures and model maps:
	1) select 'WMS layer' for widely availabel layers.
*or*
    1) select 'MSS models' or 'MSS Profile' to use bespoke map layers. MSS Profile loads the vertical profile.

	2) choose which website to load the web map service (from the WMS.txt or MSS.txt file). 
	3) follow dialogs for selecting the right times, layer, level, etc.

## Adding any image
    1) Select the image add buttons (Froecast from Bocachica, trajectory image, image, or Tropical tidbit). For general images select 'image button'
    2) Select the image file
    3) if prompts, select the most appropriate image style, if not then use the 'manual' selection and follow those prompts to indicate projection and image file corners.
    4) wait a few moments for image to appear, if not use the 'image' button. Not all image files are compatible, however most .png work.

## Adding image corner definition for easier future loading.  
    1) open the file 'image_corners.json'. 
    2) this json file contains, list of named images, with the corner of the image file in a list (lower-left latitude, lower-left longitude, upper-right latitude, upper-right longitude), or in a dict-like with projection information. 
    
## Adding platform default information:
    1) locate the platform.txt file.
    2) in the file, there is a series of python dict formats with each a defined list of variables that sets the flight characteristics of the plane/platform
    3) modify exisiting pltform dict, or create a new one based on the template and the guidance shown in the file.
    
## Adding satellite tracks:
	1) select the button: "Satellite Tracks"
	2) wait for a moment until the sat.tle and sat.json is loaded. 
	3) toggle the satellite tracks that you wish to see by clicking on the legend entry next to that satellite
	
## Change which flight path is active:
    1) Press the button related to the flight path desired just above the 'New Flight Path' button
**do not switch with Excel Spreadsheet**
    
## Move, zoom the map around:
    1) Buttons at the bottom of the map are used for navigation
    2) from left to right: Home screen (first image seen), Previous view, Next view, Pan, Zoom, subplots properties, save map
	3) Can use the scroll in to zoom into point, or scroll out.
**If zoom is selected, draw rectangle to desired location, will not be able to make new points until zoom unselected**
    
## Saving flight paths for sharing
    1) Press the 'Save all' button to create all figures and save them
    2) Follow dialog to find the desired saving location

## Making a slideshow with preset maps and displays for easier dissemination
    1) Press the 'Save pptx'
    2) Follow the prompts to where you want to save the items. This will create new figures, similar to the 'save all' button.
    
## Opening previously saved flight plans:
    1) Press the Excel File: 'Open' button. 
    2) select the Excel file
    3) will take some time to populate the flight paths
    4) Might need to press refresh button after loading
    
## Save flight plans:
    1) Press the 'Save' button next to Excel File
*or*

    1) Save the Excel file, from Excel using normal dialog
    
## Change definitions of platform speeds, and altitudes
    1) open the platform.txt file
    2) follow the documentation in the header for creating or modifying any line defining the platform
    3) save the file as platform.txt and share
    4) put the new platform.txt in the sam folder as the ml.py script or ml executable
    
# Notes and tips about usage:

    - clicking on the first point will create a waypoint to it
    - second point to be added will have the default transit altitude for that aircraft (if available)
    - when holding down the mouse button, range circles will appear, along with the sun's azimuthal location at that time denoted by the yellow star and dashed lines
    - Saving to: ICT button will create a sample ict file with 60 seconds points interpolated between each waypoint
    - plots of solar angle and altitude profiles is created with the Plots buttons
    
# Requirements:

## Windows:
        - compiled version run windows 64 bit, (32 bit not tested) (Windows 7,8,10)
        - Microsoft Excel
        - optionally Google Earth
    
## OSX:
        - compiled version tested on El Capitan Mac OSX v10.11, 64bit (others not tested)
        - Microsoft Excel
        - optionally Google Earth
    
## source:
        - Python 3.9
        - Numpy
        - Scipy
        - matplotlib
        - ~~basemap from matplotlib (http://matplotlib.org/basemap/)~~ cartopy
        - Tkinter (usually included in python)
        - simplekml, pykml
        - gpxpy
        - owslib
        - xlwings
        - Pysolar (distributed with source)
        - See requirements.txt for full modules dependencies
        
# Required files (included in distribution):

    - labels.txt : csv files with points on map to be labelled. Each line represent one point, Format: name, longitude, latitude, marker and color symbol
    - aeronet_locations.txt: csv files with location of aeronet sites. found from : http://aeronet.gsfc.nasa.gov/aeronet_locations.txt
    - sat.tle: Selected data for satellite tracks in form of Two Line Element set from http://www.celestrak.com
	- sat.json: (new in v1.62) for geostationary satellite footprint definition, saved as a json, with wkt format of their footprint, and proj4 for its projections.
    - profiles.txt: text file containing dictionary assignment for map setup defaults. each profile linked to a field mission, python dict format.
    - platform.txt: text file containing dictionary assignment for details on each platform: max altitude, max speed, speed profile, vertical speed profile, turning rate
    - WMS.txt: list of possible WMS servers for getting map images from the internet.
    - arc.ico: icon file
    - file.rc: plotting defaults file (python matplotlib.rc format)
    - map_icons: folder with icons for use on google earth (optional)
    - flt_modules: folder with multiple flt files. To use when creating the flt_module paths. 
    - ~~map_???.pkl: files to enable faster initial loading of the basemap~~
    
# Source files:

    - ml.py : Main program. Used to setup the interface, link to the excel spreadsheet and start the program
    - map_interactive.py: Basemap plotting and interactive map clicking support
    - excel_interface.py: interfaces with Excel, Core of the calculations, *contains speed and altitude calculations*
    - gui.py: Handling the button events and functions. Has the saving routines interfaces
    - map_utils.py: various map utilities, like bearing calculations, great circle calculations
    - write_utils.py: writing utitlies, expecially for ICT file creation
    - load_utils.py: loading of various format utilities and conversion of input formats
    - aeronet.py: loading and presenting the aeronet real time AOD on the map

# To do/wish list:

    - add platform info button next to flight paths (to change its settings)
    - add ship tracks, or position of ships
    - add capabilities to load hdf files and put contour as background
    - add remove flight button

# Known Bugs:

    - Sometime slow starting up, especiallly when excel is not open 
    
# Modification History:

    Written: Samuel LeBlanc, 2015-08-07, at NASA Ames Research Center, from Santa Cruz, CA
                Copyright 2015 Samuel LeBlanc 
    Modified (v0.7b): Samuel LeBlanc, NASA Ames, 2015-09-06
                       Initial presentation of software. Added smooth dragging and some calculations, with image overlay
    Modified (v0.8b): Samuel LeBlanc, NASA Ames, 2016-06-15
                       Corrected speed trace. 
                       Added sun position calculations
                       Modified some gui placement
                       Added ICT file creation, and save all button
    Modified (v0.9b): Samuel LeBlanc, NASA Ames, 2016-06-22
                       Added flt_module command for creating parts of flights via macros
    Modified (v0.95b): Samuel LeBlanc, NASA Ames, in transit to WFF, 2016-07-11
                       Added platform information file to facilitate modification of
                        default platform parameters (cruising altitude, speed profile, climb time, turning rate)
                       Added button to remove the satellite tracks
                       updated the sat.tle file 
                       bug fix for recognizing platform after excel file load, tried to fix bug in altitude and speed calculations
                       Added selections for altitude in feet/meter and distance in nm/km for flt_module loading.
    Modified (v0.97b): Samuel LeBlanc, NASA Ames, at Santa Cruz, CA, 2016-07-18
                       bug fix for improper parallels and meridians drawing. 
                       Some speed improvements
                       updated aeronet site locations and sat.tle satellite predictions and icon
    Modified (v1.00): Samuel LeBlanc, NASA Ames, CA, 2016-07-22
                       bug fix to sza and azimuth calculations
                       bug fix to aircraft bearing calculations
                       new icons and kmz saving
                       new modes for WMS loading with GEOS and other
                       extracted definitions of platform speeds and altitude to a seperate file
    Modified (v1.03): Samuel LeBlanc, NASA Ames, CA, 2016-07-22
                       bug fix to excel file loading and improper time zone correction
                       new Special Use Airspace button
                       generalized WMS interface for loading maps from the internet
                       special excel spreadsheet fiel saving for pilots 
    Modified (v1.1): Samuel LeBlanc, NASA 
                       bug fixes to presentation and file saving
                       faster updating of the map screen and draggable legend
                       User modifiable default aircraft propeties (platform.txt) and map properties (profiles.txt)
                       Included loading of special map severs (special use airspace, WMS, GEOS)
    Modified (v1.2): Samuel LeBlanc, Sao Tomé, 2017-08-16
                        for_pilots spreadsheet now can be configured to save either in decimal minutes or decimal seconds (defaults to decimal minutes)
                        bug fix in add point button
                        saveall button on mac now has error control
    Modified (v1.21): Samuel LeBlanc, Sao Tomé, 2017-08-16         
                        map plotting bug fixes, and Special Use Airspace (SUA) error mitigation. Bug fix when using 'save all' button
    Modified (v1.22): Samuel LeBlanc, 2019-06-03, Santa Cruz, CA
                        - Bug fixes for line picking and climb time calculations.
    Modified (v1.23): Samuel LeBlanc, 2019-08-05, Bathurst, NB, Canada
                        - added one line saving for pilots.
    Modified (v1.25): Samuel LeBlanc, 2021-04-08, Santa Cruz, CA
                        - added buttons for quick adding the IMPACTS "tropicaltidbits.com" imagery
	Modified (v1.28): Samuel LeBlanc, v1.28, 2021-11-08, Santa Cruz, CA  
						- bug fix for deletion points
	Modified (v1.29): Samuel LeBlanc, v1.29, 2022-01-11, Santa Cruz, CA
						- bug fix for saving multiple excel sheets
						- adding scroll to zoom 
						- adding custom color to labels.txt points
	Modified: Samuel LeBlanc, v1.30, 2022-02-03, Santa Cruz, CA
			- bug fix to for_pilots excel spreadsheet
	Modified: Samuel LeBlanc, v1.40, 2023-05-30, Santa Cruz, CA
			- added new projections
			- added new variables to the profiles.txt format
	Modified: Samuel LeBlanc, v1.41, 2023-06-08, Santa Cruz, CA
			- added surface elevation to elevation plots
			- added plotting of select kml files
			- added FIR boundaries plotting.
			- added the AERONET v3 debugging and defaults
			- modified plotting of satellite tracks for esthetics
	Modified: Samuel LeBlanc, v1.42, 2023-07-20, Santa Cruz, CA 
			- added support for the MSWMS from MSS
			- added extra selections options for the WMS loading.
	Modified: Samuel LeBlanc, v1.43, 2023-07-27, Hampton, VA 
			- bugfix for Mac OS laoding of files, and pkl map files.
	Modified: Samuel LeBlanc, v1.44, 2023-08-04, Snta Cruz, CA 
			- Adding the loading and compatibility with setuptools for pip integration and reglar python modules
    Modified: Samuel LeBlanc, v1.45, 2023-08-10, Santa Cruz, CA
                - Debugging and change of folder systems for pip install
    Modified: Samuel LeBlanc, v1.46, 2023-08-15, Santa Cruz, CA
                - Debugging for MACos and newer matplotlibs
				- Added conda deployment
    Modified: Samuel LeBlanc, v1.47, 2023-11-03, Santa Cruz, CA 
                - adding simple version output from command line (used for testing on conda deployments)
    Modified: Samuel LeBlanc, v1.48, 2024-02-22, Santa Cruz, CA
                - bug fix for forcing max speed, and base speed as start.
                - Added error handling during 'save all'
                - sped up interactivity and point adding
                - Added init time parsing for the MSS models in WMS.
                - upgraded plotting of figures under map for better viewing of text
                - added plot vs alt for all combined platforms and highlight of coordinated points
                - refined speed parameters for G3 and Learjet
	Modified: Samuel LeBlanc, v1.49, 2024-04-09, Santa Cruz, CA
                - bug fix for speeds of turns and timing
                - bug fix for missing comments
                - Added file format outputs in csv for FOREFLIGHT and UFP
	Modified: Samuel LeBlanc, v1.50, 2024-04-10, Santa Cruz, CA
				- general speedup of software
                - new pilot files bug fix for waypoint naming (only 5 digits) and lat/long flip
                - added file output for honeywell FMS for GIII
				- added better handling of satellite tracks defaulting to not visible for speed
                - speeded up interactions with changing labels update
				- added snapping to labeled points
				- added midpoint between 2 points
				- added waypoint name row in excel
	Modified: Samuel LeBlanc, v1.51, 2024-05-14, Santa Cruz, CA
				- Added new automated powerpoint presentation generation
				- improved G3 speed calculations.
	Modified: Samuel LeBlanc, v1.52, 2024-06-04, Pituffik, Greenland, Danemark
				- Added more accurate bank angle and speeds for the G3, and smaller changes to P3
				- changed some automated processing of the powerpoint generations
				- added modules for the P3 and G3 used during ARCSIX
				- Refine pilot files to remove double waypoint names.
				- updated flight speeds for G3
    Modified: Samuel LeBlanc, v1.53, 
    Modified: Samuel LeBlanc, v1.54, 2024-08-04, Pituffik, Greenland
                - Bug fix to table removed extra lines
                - change kml generation to be named waypoints
    Modified: Samuel LeBlanc, v1.54, Pituffik, Greenland
                - Bug fix to table removed extra lines
                - change kml generation to be named waypoints
                - added feature to change day when loading previous file.
    Modified: Samuel LeBlanc, v1.55, Pituffik, Greenland + Santa Cruz, CA
                - Added fix to coloring of the for_pilots file, and formatting.
                - added an ER2 specific file format.
                - Added longer timeout for mss profile
                - Added ability to add magnetic heading indicator to pilot formats, with magnetic declination in profiles.txt
    Modified: Samuel LeBlanc, v1.56, NASA Langley Research Center, Virginia
                - Added 2 bespoke NURTURE flight modules.
                - Added modifications to zeroth longitude of the North Polar Stereo.
                - Slight modifications to turn bank angles for G3.
                - setup files for NURTURE 2026.
    Modified: Samuel LeBlanc, v1.60, 2025-10-01 (first day of a government shutdown) Santa Cruz, CA 
                - bug fix for plotting in multiple different projections, while keeping the great circle lines. 
                - New feature - North Atlantic and Pacific-Oceanic routes, based on flightplandb API. 
                - New feature - modified the image_corners.json file format to handle different types of projections from input images. 
                - Bug fixes to MSS Profile init time checking. 
                - Added projection handling in MSS models.  
                - Updated the labels.txt for arctic locations that may be important to NURTURE. 
                - Added an initial try at a parameterized NASA 777 flight characteristics. 
                - Changed defaults of NURTURE projection to lamber azimuthal equal area. 
    Modified: Samuel LeBlanc, v1.61, 2025-10-07, Santa Cruz, CA
                - Modifying the build environment for ensuring deployment to mac os, via conda
                - Add the simplying read of mss.txt to skip interface if only one url is present.
    Modified: Samuel LeBlanc, v1.62, 2025-10-20, Santa Cruz, CA
                - Adding manual headwind inputs and calculations
                - Adding explicit turn type and turn time descriptions.
                - Improved turn time calculations for the different turn types
                - Adding new excel columns to habndle the headwind, turn types, and potential for time points.
                - Added sat.json for handling the geostationary satellite types
                - Adding multiple new satellites descriptions.
     Modified: Samuel LeBlanc, v1.63, 2025-11-19, Santa Cruz, CA
                - Bug fix on tropical tidbits loading
                - Bug fix on add points
                - Changed units for nautical miles from [nm] to [Nmi]
                - Turn time for overlfly and 90-270 refined (reduced)
                - added automated docx creation
                - modified the for piltos excel writer to use xlswriter (offline) instead of xlwings, to prevent mix-ups
                - Adding the coast buffer indencation
                - Fixed satellite tracks disapearing, and interplay with zoom button
                - Added measurement tool
                - Added help button
		Modified: Samuel LeBlanc, v1.64, 2026-01-27, Santa Cruz, CA
                - cleaning up the point styles for kml - for better plotting on MTS.
                - bug fix on cancel button for MSS
                - fixing up to ensure last point is on the ground.
                - bug fix to missing alt value when saving for pilot excel
                - added function to flip order of a set number of points
                - fixed problem with turn types and wrong amount of delay


# To cite:

Cite as:

Samuel LeBlanc and millercommamatt (2024) “samuelleblanc/fp: Moving Lines: Turn speed bug fix and new pilot formats”. (v1.49) Zenodo. doi: 10.5281/zenodo.10951716.

BibTex:
@misc{samuel_leblanc_2023_1478125,
author = {LeBlanc, Samuel},
doi = {10.5281/zenodo.1478125},
publisher = {Zenodo},
title = {{samuelleblanc/fp: Moving Lines: NASA airborne research flight planning tool release (v1.44)}},
url = {https://doi.org/10.5281/zenodo.1478125},
year = {2023}
}
