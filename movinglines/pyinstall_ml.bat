# script to compile the ml with pyinstaller

C:\Users\lebla\AppData\Local\Programs\Python\Python39\Scripts\pyinstaller.exe -D --hidden-import=Tkinter --hidden-import=numpy.fft.fftpack_lite ^
               --exclude-module=IPython --exclude-module=PySide  ^
               -p C:\Users\sleblanc\Research\py\pysolar-0.6 --hidden-import=Pysolar ^
               --hidden-import=dateutil.zoneinfo ^
               --hidden-import=scipy.integrate --hidden-import=scipy.integrate._odepack ^
               --hidden-import=scipy.interpolate --hidden-import=scipy.integrate._quadpack ^
               --additional-hooks-dir=.\hooks\ ^
               --icon=arc.ico ml.py
			   
			   
			   
			   
#			                 --hidden-import=FixTk --exclude-module=tkinter ^