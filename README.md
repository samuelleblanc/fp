# Name:

Moving Lines, version 1.21
Get the compiled versions for MAC OS and Windows at:
[http://engineering.arm.gov/~sleblanc/flight_planning/]
    
# Purpose:
    
Flight Planning software for creating flight plans for Airborne Science
    
Creates a visual map interface and backend calculations to a spreadsheet flight planning tool
Takes advantage of clickable map for creating a flight plan, and already existing Excel software
    
# Quick Start (for compiled versions):

    1) Download appropriate zip file and extract to desired location
    2) Requires Microsoft Excel
    3) run the executable (ml for OSX, ml.exe for Win)
        for OSX:
            - run from command line, must cd to directory hosting the ml exectuable
        for Windows:
            - double click the ml.exe icon
    4) Select the mapping profile (defaults to ORACLES), can change the map boundaries, take-off time, utc offset
    5) wait about 30seconds
    6) Enter date of planned flight in dialog in format yyyy-mm-dd
    7) wait for map to initialize and excel to load
    8) move cursor over map to refresh map
    9) create points, move points by clicking or by manually entering in excel spreadsheet
    10) Once happy save all the figures, files, excel files, kml files by either selecting each point, or by pressing the 'saveall' button
    
## Adding points:
    1) click and drag on map to create new point 
    2) modify altitudes, speed, or other properties of new point in excel spreadsheet
  *or*
  
    1) enter lat and lon in excel spreadsheet, optionally altitude and speed, delay time, start time
    2) move cursor over map area to refresh *or* press green refresh button
  *or*
  
    1) Press the 'add' button next to 'points:'
    2) Follow the dialog
    
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
    
## Adding platform default information:
    1) locate the platform.txt file.
    2) in the file, there is a series of python dict formats with each a defined list of variables that sets the flight characteristics of the plane/platform
    3) modify exisiting pltform dict, or create a new one based on the template and the guidance shown in the file.
    
## Change which flight path is active:
    1) Press the button related to the flight path desired just above the 'New Flight Path' button
**do not switch with Excel Spreadsheet**
    
## Move, zoom the map around:
    1) Buttons at the bottom of the map are used for navigation
    2) from left to right: Home screen (first image seen), Previous view, Next view, Pan, Zoom, subplots properties, save map
**If zoom is selected, draw rectangle to desired location, will not be able to make new points until zoom unselected**
    
## Saving flight paths for sharing
    1) Press the 'Save all' button to create all figures and save them
    2) Follow dialog to find the desired saving location
    
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
    - second point to be added will have the default transit altitude for that plane (if available)
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
        - Python 2.7
        - Numpy
        - Scipy
        - matplotlib
        - basemap from matplotlib (http://matplotlib.org/basemap/)
        - Tkinter (usually included in python)
        - simplekml, pykml
        - gpxpy
        - owslib
        - xlwings
        - Pysolar (distributed with source)
        - See requirements.txt for full modules dependencies
        
# Required files (included in distribution):

    - labels.txt : csv files with points on map to be labelled. Each line represent one point, Format: name, longitude, latitude, marker symbol
    - aeronet_locations.txt: csv files with location of aeronet sites. found from : http://aeronet.gsfc.nasa.gov/aeronet_locations.txt
    - sat.tle: Selected data for satellite tracks in form of Two Line Element set from http://www.celestrak.com
    - profiles.txt: text file containing dictionary assignment for map setup defaults. each profile linked to a field mission, python dict format.
    - platform.txt: text file containing dictionary assignment for details on each platform: max altitude, max speed, speed profile, vertical speed profile, turning rate
    - WMS.txt: list of possible WMS servers for getting map images from the internet.
    - arc.ico: icon file
    - file.rc: plotting defaults file (python matplotlib.rc format)
    - map_icons: folder with icons for use on google earth (optional)
    - flt_modules: folder with multiple flt files. To use when creating the flt_module paths. 
    - map_???.pkl: files to enable faster initial loading of the basemap
    
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
    - Altitude may not always change adequatly, even after manual input (**possibly resolved**)
    - when switching between flight paths, speed may be mixed up (**possibly resolved**)
    
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