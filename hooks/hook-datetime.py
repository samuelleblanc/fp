# to compile the dateutils zoneinfo data
from dateutil import zoneinfo

try:
     finfo = zoneinfo.ZONEINFOFILE
except:
     import os
     finfo = os.path.join(os.path.dirname(zoneinfo.__file__),zoneinfo.ZONEFILENAME)
datas = [(finfo,'dateutil/zoneinfo/')]
