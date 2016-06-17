"""
Program designed to interactively prepare flight plans
Uses interaction between excel and python basemap

The main program is called moving_lines, with its mehtod of Create_interaction

To start the program, after import flight_planning do flight_planning.Start()

By Samuel LeBlanc, samuel.leblanc@nasa.gov
"""

__all__ = ['excel_interface','map_interactive','map_utils','gui','moving_lines_v3']
import excel_interface
import map_interactive
import map_utils
import gui
import moving_lines_v3
Start = moving_lines_v3.Create_interaction
__version__ = moving_lines_v3.__version__

