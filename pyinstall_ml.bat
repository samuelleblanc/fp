# script to compile the ml with pyinstaller
set PYTHONPATH=%PYTHONPATH%;C:\Users\sleblan2\Research\py\pysolar-0.6
Pyinstaller -D --hidden-import=Tkinter --hidden-import=numpy.fft.fftpack_lite ^
               --exclude-module=IPython --exclude-module=PySide  ^
               --hidden-import=FixTk --exclude-module=tkinter ^
               -p C:\Users\sleblan2\Research\py\pysolar-0.6 --hidden-import=Pysolar ^
               --hidden-import=dateutil. ^
               --icon=arc.ico ml.py