"""
Program designed to interactively prepare flight plans
Uses interaction between excel and python basemap

The main program is called moving_lines, with its mehtod of Create_interaction

To start the program, after import movinglines do movinglines.main()

By Samuel LeBlanc, samuel.leblanc@nasa.gov
"""

__all__ = ['excel_interface','map_interactive','map_utils','gui','ml','aeronet','load_utils','write_utils']
#import excel_interface
#import map_interactive
#import map_utils
#import gui
#import aeronet
#import load_utils
#import write_utils
from .version import __version__
__author__ = 'Samuel LeBlanc'
__credits__ = 'Bay Area Environmental Research Institute / NASA Ames Research Center'
#import ml
from .ml import Create_interaction as main

#Start,ui = ml.Create_interaction(test=False)


