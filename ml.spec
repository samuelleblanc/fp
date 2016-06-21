# -*- mode: python -*-

block_cipher = None


a = Analysis(['ml.py'],
             pathex=['C', 'Userssleblan2Researchpypysolar-0.6', '/Users/samuel/Research/fp'],
             binaries=None,
             datas=None,
             hiddenimports=['Tkinter', 'numpy.fft.fftpack_lite', 'FixTk', 'Pysolar', 'dateutil.zoneinfo', 'scipy.integrate', 'scipy.integrate._odepack', 'scipy.interpolate', 'scipy.integrate._quadpack', 'FileDialog'],
             hookspath=['./hooks/'],
             runtime_hooks=[],
             excludes=['IPython', 'PySide', 'tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='ml',
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='arc.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='ml')
