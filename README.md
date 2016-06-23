# Name:

Moving Lines, version 0.8beta
[http://science.arm.gov/~sleblanc/flight_planning/]
    
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
    3) first line starts with the hash sign '#' then a list of variables to be used
    4) each subsequent line is a move command, which can use simple math and the variables defined in the first line
    5) format of the lines are: bearing,distance,altitude
        where the bearing is the azimuth angle of the plane
        where the distance is the length of that leg
        where the altitude (which can be omitted) is the default altitude of the plane for the next waypoint
    6) enter number of points desired for macro then save in the flt_module directory. It is ready to be used in the software.    
    
## Adding other planes or flight paths:
    1) Press the 'New Flight Path' button
    2) Enter name of new flight path. If it contains the name of a plane (e.g. p3, er2, dc8, c130,baer), will use the predefined speeds for that plane
    3) New flight path will have different color
    
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
    
# Notes and tips about usage:

    - clicking on the first point will link it again
    - second point to be added will have the default transit altitude for that plane (if available)
    - when holding down the mouse button, range circles will appear, along with the sun's azimuthal location at that time
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
        
# Required files (included in distribution):

    - labels.txt : csv files with points on map to be labelled. Each line represent one point, Format: name, longitude, latitude, marker symbol
    - aeronet_locations.txt: csv files with location of aeronet sites. found from : http://aeronet.gsfc.nasa.gov/aeronet_locations.txt
    - sat.tle: Selected data for satellite tracks in form of Two Line Element set from http://www.celestrak.com
    - profiles.txt: text file containing dictionary assignment for map setup defaults. each profile linked to a field mission, python dict format.
    - arc.ico: icon file
    - file.rc: plotting defaults file (python matplotlib.rc format)
    
# Source files:

    - ml.py : Main program. Used to setup the interface, link to the excel spreadsheet and start the program
    - map_interactive.py: Basemap plotting and interactive map clicking support
    - excel_interface.py: interfaces with Excel, Core of the calculations, *contains speed and altitude calculations*
    - gui.py: Handling the button events and functions. Has the saving routines interfaces
    - map_utils.py: various map utilities, like bearing calculations, great circle calculations
    - write_utils.py: writing utitlies, expecially for ICT file creation
    - load_utils.py: loading of various format utilities and conversion of input formats

# To do/wish list:

    - add platform info button next to flight paths (to change its settings)
    - extract altitude, speed and climb time calculations from Excel_interface.py to enable easier modifications
    - Macro generation tool and presets
    - add other forecast imagery from GMAO or others using WMS
    - add current AOD values at AERONET stations
    - add ship tracks, or position of ships
    - add capabilities to load hdf files and put contour as background
    - add remove flight button

# Known Bugs:

    - Sometime slow starting up, especiallly when excel is not open
    - May not recognise platform after loading an saved excel spreadsheet
    - Altitude may not always change adequatly, even after manual input
    - when switching between flight paths, speed may be mixed up
    
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
    
