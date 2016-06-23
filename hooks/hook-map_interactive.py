"""
Some hooks to gather the data from ml.py
"""
import excel_interface as ei
import os

fp = ei.get_curdir()
datas = []
for l in os.listdir(os.path.join(fp,'flt_module')):
    datas.append((fp,l,'flt_module'))