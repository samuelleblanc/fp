"""
Some hooks to gather the data from ml.py
"""
import excel_interface as ei
import os

datas = [(os.path.join(ei.get_curdir(),'sat.tle'),'.'),
         (os.path.join(ei.get_curdir(),'arc.ico'),'.'),
         (os.path.join(ei.get_curdir(),'labels.txt'),'.'),
         (os.path.join(ei.get_curdir(),'aeronet_locations.txt'),'.'),
         (os.path.join(ei.get_curdir(),'file.rc'),'.'),
         (os.path.join(ei.get_curdir(),'README.md'),'.'),
         (os.path.join(ei.get_curdir(),'license.txt'),'.'),
         (os.path.join(ei.get_curdir(),'profiles.txt'),'.'),
         (os.path.join(ei.get_curdir(),'platform.txt'),'.')]
