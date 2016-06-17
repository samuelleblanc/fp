def get_aeronet(daystr=None):
    """ 
    Purpose:
       Program to go and get the aeronet data on the day defined by daystr
       Returns an numpy named array, with station names, lat, lon, average daily aods per site and wavelength
    Inputs:
       daystr: (optional, defaults to today) day for aeronet data in format yyyy-mm-dd.
               if day is in future, it is changed to today
    Outputs:
       numpy structured array with one entry per station
    Dependencies:
       urllib
       StringIO
       BeautifulSoup
       Numpy
       datetime
       warnings
    Example:
       ...
    History:
       Written: Samuel LeBlanc, 2015-10-02, Santa Clara, CA
    """
    import numpy as np
    from BeautifulSoup import BeautifulSoup
    from StringIO import StringIO
    from urllib import urlopen
    from datetime import datetime

    dd = datetime.utcnow().strftime('%Y-%m-%d')
    if not daystr:
        daystr = dd
    else:
        if daystr > dd:
	    daystr = dd
	    import warnings
	    warnings.warn("Date set to future, using today's date")
    url = 'http://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v2_globe?year={yyyy}&month={mm}&day={dd}&year2={yyyy}&month2={mm}&day2={dd}&LEV10=1&AVG=20'.format(yyyy=daystr[0:4],mm=int(daystr[5:7]),dd=int(daystr[8:10]))
    print 'Getting file from internet: at aeronet.gsfc.nasa.gov'
    print url
    try:
        html = urlopen(url).read()
        soup = BeautifulSoup(html)
    except:
        print 'failed to communicate with internet returning nothing'
	return False
    lines = []
    for br in soup.findAll('br'):
        nt = br.nextSibling
	lines.append(nt.strip()+'\n')
    s = StringIO(''.join(lines))
    s.seek(0)
    try:
        dat = np.genfromtxt(s,delimiter=',',names=True,dtype=None)
    except IndexError:
        print 'Failed to read the returned html file'
	return False
    fields_to_ignore = ['AERONET_Site_Name','Principal_Investigator','PI_Email','Dateddmmyy']
    for label in dat.dtype.names:
        if not label in fields_to_ignore:
	    if dat[label].dtype.type is np.str_:
	         dat[label] = np.genfromtxt(dat[label])
    return dat
