# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['ml.py'],
             pathex=['C:\\Users\\sleblanc\\Research\\py\\pysolar-0.6', 'C:\\Users\\lebla\\Research\\fp'],
             binaries=[],
             datas=[],
             hiddenimports=['Tkinter', 'numpy.fft.fftpack_lite', 'Pysolar', 'dateutil.zoneinfo', 'scipy.integrate', 'scipy.integrate._odepack', 'scipy.interpolate', 'scipy.integrate._quadpack'],
             hookspath=['.\\hooks\\'],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['IPython', 'PySide'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='ml',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='arc.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ml')
