# script to compile the ml with pyinstaller
Pyinstaller -D --hidden-import=Tkinter --hidden-import=numpy.fft.fftpack_lite \
               --exclude-module=IPython --exclude-module=PySide  \
               --exclude-module=tkinter \
               -p C:\Users\sleblan2\Research\py\pysolar-0.6 \
	       --hidden-import=Pysolar \
               --hidden-import=dateutil.zoneinfo \
               --hidden-import=scipy.integrate \
               --hidden-import=scipy.integrate._odepack \
               --hidden-import=scipy.interpolate \
               --hidden-import=scipy.integrate._quadpack \
               --additional-hooks-dir=./hooks/ \
               --hidden-import=FileDialog \
               --exclude-module=FixTk \
               --icon=arc.ico ml.py
