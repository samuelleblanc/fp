# script to save run the nuitka command with proper path setting
del PYTHONPATH
set PYTHONPATH=C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Scripts
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\include
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\DLLs
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\owslib\
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\Scripts
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\numpy
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\scipy
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\win32com
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\win32com\include
set PYTHONPATH=%PYTHONPATH%;C:\Python27_64\WinPython-64bit-2.7.6.4\python-2.7.6.amd64\Lib\site-packages\PIL
set PYTHONPATH=%PYTHONPATH%;C:\Users\sleblan2\Research\py
set PYTHONPATH=%PYTHONPATH%;C:\Users\sleblan2\Research\py\pysolar-0.6
"C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall" amd64
nuitka --standalone --recurse-not-to=py2exe --recurse-not-to=pandas --recurse-not-to=zmq --recurse-not-to=geopy --recurse-not-to=IPython --recurse-not-to=jinja2 --recurse-not-to=nose --recurse-not-to=sphinx --recurse-not-to=sqlalchemy --recurse-not-to=pyqt --recurse-not-to=PyQt4 --recurse-not-to=tornado --recurse-directory=scipy.special._ufuncs_cxx --recurse-directory=scipy.integrate --recurse-plugins=dateutil.zoneinfo --recurse-plugins=matplotlib.mpl-data --recurse-plugins=mpl_toolkits.basemap.data --recurse-directory=numpy.fft --recurse-directory=numpy.core --recurse-directory=scipy.linalg --recurse-directory=scipy.sparse.csgraph --recurse-directory=scipy.special --recurse-to=scipy.misc.imread --windows-icon=arc.ico --recurse-all ml.py
