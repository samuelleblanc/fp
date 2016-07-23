def get_aeronet(daystr=None,lat_range=[],lon_range=[]):
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
       Modified: Samuel LeBlanc, 2016-07-12, WFF, CA
    """
    import numpy as np
    from BeautifulSoup import BeautifulSoup
    from StringIO import StringIO
    from urllib import urlopen
    from datetime import datetime
    from load_utils import recarray_to_dict
    
    def safe_list_get (l, idx, default):
        try:
            return l[idx]
        except IndexError:
            return default

    dd_now = datetime.utcnow()
    dd = dd_now.strftime('%Y-%m-%d')
    if not daystr:
        daystr = dd
    else:
        if daystr > dd:
	    daystr = dd
	    import warnings
	    warnings.warn("Date set to future, using today's date")
  
    url = 'http://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v2_globe?year={yyyy}&month={mm}&day={dd}&year2={yyyy}'+\
          '&month2={mm}&day2={dd}&LEV10=1&AVG=20'
    if lat_range:
        url = url+'&lat1={lat1:f}&lat2={lat2:f}&lon1={lon1:f}&lon2={lon2:f}'
    url = url.format(yyyy=daystr[0:4],mm=int(daystr[5:7]),dd=int(daystr[8:10]),lat1=safe_list_get(lat_range,0,None),
                    lat2=safe_list_get(lat_range,1,None),lon1=safe_list_get(lon_range,0,None),lon2=safe_list_get(lon_range,1,None))
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
    
    return recarray_to_dict(dat)
    
def plot_aero(m,aero,no_colorbar=True,a_max = 1.5):
    """
    Simple function that takes a basemap plotting object ( m) and plots the points of the aeronet sites with their value in color
    For easy aeronet visualisation
    """
    from matplotlib import cm
    from matplotlib.lines import Line2D
    import numpy as np
    x,y = m(aero['Longitude'].astype('double'),aero['Latitude'].astype('double'))
    
    if no_colorbar:
        colors = np.round(aero['AOT_500'].astype('double')/a_max*7.0)/7.0
        c_ar = np.linspace(0,a_max,7)
        leg_ar = ['{:1.2f} - {:1.2f}'.format(c,c_ar[i+1]) for i,c in enumerate(c_ar[0:-1])]
    else:
        colors = aero['AOT_500'].astype('double')

    cls = cm.gist_ncar(c_ar/a_max)
    
    bb = m.scatter(x,y,c=colors,cmap=cm.gist_ncar,marker='s',
                   vmin=0.0,vmax=a_max,edgecolors='None',s=100)
                   
    if no_colorbar:
        fakepoints = []
        for i,cl in enumerate(cls):
            fakepoints.append(Line2D([0],[0],color=cl,linestyle='None',marker='s',markeredgecolor='None'))
        cbar = m.ax.legend(fakepoints,leg_ar,numpoints=1,frameon=True,loc='lower right',bbox_to_anchor=(0.45,1.04),title='AOD 500 nm',ncol=2)
        try:
            m.ax.add_artist(cbar)
        except:
            pass
    else:
        try:
            cbar = m.colorbar(m.ax,bb)
            cbar.set_label('AOD 500 nm')
        except:
            pass
    u = [bb,cbar]
    return u