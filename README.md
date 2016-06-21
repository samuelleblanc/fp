# flight_planning
Collection of python codes for use with flight planning software

Currently interfaces a basemap with and excel spreadsheet
Makes clickable points in the basemap reflected in the excel spreadsheet

The main script to run the program is moving_lines_v3.py. 
This creates a gui with basemap, and a set of buttons.

Button functions are handled by gui.py. 
The functions for the Basemap instance and its interactivity are handled by map_interactive.py
The functions for interfacing with Excel is handled by excel_interface.py

To do:
- add other forecast imagery from GMAO or others using WMS
- make more accurate flight time calculations (accounting for climbing and descending)
- add current AOD values at AERONET stations
- add ship tracks, or position of ships
- add calipso ground track
- add capabilities to load hdf files and put contour as background
- add remove flight button

Known Bugs:
- Sometime slow starting up
- Slow when loading excel file
- Altitude may not always change adequatly, even after manual input
- delaytime may be modified, even after manual input
- when switching between flight paths, speed may be mixed up
