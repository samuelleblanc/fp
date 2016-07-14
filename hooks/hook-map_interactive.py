"""
Some hooks to gather the data from ml.py
"""
import excel_interface as ei
import os

fp = ei.get_curdir()
datas = []
for l in os.listdir(os.path.join(fp,'flt_module')):
    datas.append((os.path.join(fp,'flt_module',l),'flt_module'))
for l in os.listdir(os.path.join(fp,'map_icons')):
    datas.append((os.path.join(fp,'map_icons',l),'map_icons'))
for l in os.listdir(os.path.join(fp,'map_*.pkl')):
    datas.append((os.path.join(fp,l),'.\\'))
