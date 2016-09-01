# Excel Interface codes to be used in coordination with moving_lines flight planning software
# Copyright 2015 Samuel LeBlanc

import numpy as np
from xlwings import Range
from datetime import datetime
from scipy import interpolate
import write_utils as wu
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import map_interactive as mi
from map_interactive import pll
import map_utils as mu

class dict_position:
    """
    Purpose:
        Class that creates an easy storage for position coordinates.
        Encompasses array values of positions, altitude, time, dist.
        Along with program to update excel spreadsheet with info, read spreadsheet data,
        and update calculations for distances
    Inputs: (at init)
        lon0: [degree] initial longitude (optional, defaults to Namibia Walvis bay airport), can be string
        lat0: [degree] initial latitude (optional, defaults to Namibia Walvis bay airport), can be string
        speed: [m/s] speed of aircraft defaults to p3 value of 150 m/s (optional)
        UTC_start: [decimal hours] time of takeoff, defaults to 7.0 UTC (optional)
        UTC_conversion: [decimal hours] conversion (dt) used to change utc to local time (optional), local = utc + dt
        alt0: [m] initial altitude of the plane, airport altitude (optional)
        verbose: if True then outputs many command line comments while interaction is executed, defaults to False
        filename: (optional) if set, opens the excel file and starts the interaction with the first sheet
        datestr: (optional) The flight day in format YYYY-MM-DD, if not set, default to today in utc.
        color: (optional) the color of the flight path defaults to red.
        sheet_num: (optional, defaults to 1) the sheet number to switch to
        profile: (optional) if set, uses a dict of basemap profile to set for the initial lat lons, alt, utc_start, utc_conversion, name
    Outputs:
        dict_position class 
    Dependencies:
        numpy
        xlwings
        Excel (win or mac)
        map_interactive
        map_utils
        simplekml
        gpxpy
        tempfile
        os
        datetime
        Pyephem
    Required files:
        none
    Example:
        ...
    Modification History:
        Written: Samuel LeBlanc, 2015-08-07, Santa Cruz, CA
        Modified: Samuel LeBlanc, 2015-08-11, Santa Cruz, CA
                 - update and bug fixes
        Modified: Samuel LeBlanc, 2015-08-14, NASA Ames, CA
                - added save to kml functionality
        Modified: Samuel LeBlanc, 2015-08-18, NASA Ames, CA
                - added open excel functionality via the filename option and extra method
        Modified: Samuel LeBlanc, 2015-08-21, Santa Cruz, CA
                - added save to GPX functionality
                - added datestr for keeping track of flight days
                - added functionality for comments and space for sza/azi
        Modified: Samuel LeBlanc, 2015-08-24, Santa Cruz, CA
                - added multi flight path handling funcitonality, by generating new sheets
                - added newsheetonly keyword and name keyword
        Modified: Samuel LeBlanc, 2015-09-02, Santa Cruz, CA
                - added color keyword
        Modified: Samuel LeBlanc, 2015-09-10, NASA Ames, Santa Cruz, CA
	        - added init codes for loading a single sheet of a workbook
        Modified: Samuel LeBlanc, 2015-09-15, NASA Ames, CA
                    - added handling of the profile dict of lat lon and starting positions
        Modified: Samuel LeBlanc, 2016-07-10, NASA Ames, from Santa Cruz, CA
                 - added handling of platform info from external files.
                 - added bearing info to excel file and flight planning version info with date
        Modified: Samuel LeBlanc, 2016-07-22, NASA Ames, from Santa Cruz, CA
                 - modified kml saving to also save a kmz with included icons
                 - modified kml/kmz to have the altitude and link to ground set.
                 - removed dependency of Pysolar, fixed bug in azimuth calculations
        Modified: Samuel LeBlanc, 2016-07-28, NASA Ames, CA
                 - fixed utc convertion issue when reading in an excel file
        Modified: Samuel LeBlanc, 2016-08-25, NASA P3, transit from Barbados to Ascension
                 - added inserts method to insert a point in between other points.
        Modified: Samuel LeBlanc, 2016-08-30, Swakopmund, Namibia
                 - added a force speed calculation
        Modified: Samuel LeBlanc, 2016-08-31, Swakopmund, Namibia
                 - fixed saving for pilots, added delay time in comments
                 - 
    """
    import numpy as np
    from xlwings import Range,Sheet
    from datetime import datetime

    import map_interactive as mi
    from map_interactive import pll
    import map_utils as mu

    def __init__(self,lon0='14 38.717E',lat0='22 58.783S',speed=150.0,UTC_start=7.0,
                 UTC_conversion=+1.0,alt0=0.0,
                 verbose=False,filename=None,datestr=None,
                 newsheetonly=False,name='P3 Flight path',sheet_num=1,color='red',
                 profile=None,campaign='None',version='v1.02',platform_file='platform.txt'):

        if profile:
            lon0,lat0,UTC_start = profile['Start_lon'],profile['Start_lat'],profile['UTC_start']
            UTC_conversion,alt0,name,campaign = profile['UTC_conversion'],profile['start_alt'],profile['Plane_name'],profile['Campaign']
        self.__version__ = version
        self.comments = [' ']
        self.lon = np.array([pll(lon0)])
        self.lat = np.array([pll(lat0)])
        self.speed = np.array([speed])
        self.alt = np.array([alt0])
        self.UTC_conversion = UTC_conversion
        self.utc = np.array([UTC_start])
        self.UTC = self.utc
        self.legt = self.UTC*0.0
        self.dist = self.UTC*0.0
        self.cumdist = self.UTC*0.0
        self.cumlegt = self.legt
        self.delayt = self.legt
        self.bearing = self.lon*0.0
        self.endbearing = self.lon*0.0
        self.turn_deg = self.lon*0.0
        self.turn_time = self.lon*0.0
        self.climb_time = self.lon*0.0
        self.sza = self.lon*0.0
        self.azi = self.lon*0.0
        self.datetime = self.lon*0.0
        self.speed_kts = self.speed*1.94384449246
        self.alt_kft = self.alt*3.28084/1000.0
        self.head = self.legt
        self.color = color
        self.googleearthopened = False
        self.netkml = None
        self.verbose = verbose
        self.name = name
        self.campaign = campaign
        self.platform, self.p_info,use_file = self.get_platform_info(name,platform_file)
        self.pilot_format = self.p_info.get('pilot_format','DD MM SS')
        if use_file:
            print 'Using platform data for: {} from platform file: {}'.format(self.platform,platform_file)
        else:
            print 'Using platform data for: {} from internal defaults'.format(self.platform)

        if datestr:
            self.datestr = datestr
        else:
            self.datestr = datetime.utcnow().strftime('%Y-%m-%d')
        self.calculate()
        if not filename:
            self.sheet_num = sheet_num
            self.wb = self.Create_excel(newsheetonly=newsheetonly,name=name)
            try:
                self.write_to_excel()
            except:
                print 'writing to excel failed'
        else:
            self.wb = self.Open_excel(filename=filename,sheet_num=sheet_num,campaign=campaign,platform_file=platform_file)
            self.check_xl()
            self.calculate()
            self.write_to_excel()
	    self.sheet_num = sheet_num
        
    def get_platform_info(self,name,filename):
        """
        Function that reads the platform info from seperate file. 
        If sucessfuly uses these info to prepare speeds, altitudes, climb time, turn time, and others
        
        """
        from ml import read_prof_file
        import tkMessageBox
        platform = None
        p_info = None
        use_file = False
        try:
            p = read_prof_file(filename)
            for d in p:
                if any(o in name for o in d['names']):
                    platform = d['Platform']
                    p_info = d
                    use_file = True
                    break
            if not p_info:
                tkMessageBox.showwarning('Platform not found','Platform values not found in file: {}.\nUsing internal defaults.'.format(filename))
                platform = self.check_platform(name)
                p_info = self.default_p_info(platform)
        except IOError:
            print '** Error reading platform information file: {} **'.format(filename)
            print '** Using default platform profiles **'
            platform = self.check_platform(name)
            p_info = self.default_p_info(platform)
        if p_info['warning']:
            tkMessageBox.showwarning('Check needed','Platform default speeds and altitude may be off for {}. Please double check.'.format(platform))
        return platform, p_info, use_file
            
    def default_p_info(self,platform):
        'function that returns the default dict of platform info'
        if platform=='p3':
            p_info = {'Platform':'p3','names':['p3','P3','P-3','p-3','p 3','P 3'],
                      'max_alt':7500.0,'base_speed':130.0,'speed_per_alt':0.0075,
                      'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                      'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':6000.0,
                      'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                      'rate_of_turn':None,'turn_bank_angle':15.0,
                      'warning':False}
        elif platform=='er2':
            p_info = {'Platform':'er2','names':['er2','ER2','ER-2','er-2','ER 2','er 2'],
                        'max_alt':19000.0,'base_speed':70.0,'speed_per_alt':0.0071,
                        'max_speed':300.0,'max_speed_alt':30000.0,'descent_speed_decrease':0.0,
                        'climb_vert_speed':10.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':24.0,'vert_speed_per_alt':0.0011,
                        'rate_of_turn':None,'turn_bank_angle':15.0,
                        'warning':False}
        elif platform=='dc8':
            p_info = {'Platform':'dc8','names':['dc8','DC8','DC-8','dc-8','DC 8','dc 8'],
                        'max_alt':13000.0,'base_speed':130.0,'speed_per_alt':0.0075,
                        'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':15.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':15.0,'vert_speed_per_alt':0.001,
                        'rate_of_turn':None,'turn_bank_angle':15.0,
                        'warning':False}
        elif platform=='c130':
            p_info = {'Platform':'c130','names':['c130','C130','C-130','c-130','C 130','c 130'],
                        'max_alt':7500.0,'base_speed':130.0,'speed_per_alt':0.0075,
                        'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':10.0,'descent_vert_speed':-10.0,'alt_for_variable_vert_speed':0.0,
                        'vert_speed_base':10.0,'vert_speed_per_alt':0.001,
                        'rate_of_turn':None,'turn_bank_angle':20.0,
                        'warning':False}
        elif platform=='bae146':
            p_info = {'Platform':'bae146','names':['bae','BAE','146'],
                        'max_alt':8500.0,'base_speed':130.0,'speed_per_alt':0.002,
                        'max_speed':150.0,'max_speed_alt':8000.0,'descent_speed_decrease':15.0,
                        'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':8000.0,
                        'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                        'rate_of_turn':None,'turn_bank_angle':20.0,
                        'warning':True}
        elif platform=='ajax':
            p_info = {'Platform':'ajax','names':['ajax','Ajax','AJAX','alphajet','alpha','alpha-jet'],
                        'max_alt':9500.0,'base_speed':160.0,'speed_per_alt':0.09,
                        'max_speed':250.0,'max_speed_alt':9000.0,'descent_speed_decrease':5.0,
                        'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':8000.0,
                        'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                        'rate_of_turn':None,'turn_bank_angle':25.0,
                        'warning':True}
        else:
            p_info = {'Platform':'p3','names':['p3','P3','P-3','p-3','p 3','P 3'],
                      'max_alt':7500.0,'base_speed':130.0,'speed_per_alt':0.0075,
                      'max_speed':175.0,'max_speed_alt':6000.0,'descent_speed_decrease':15.0,
                      'climb_vert_speed':5.0,'descent_vert_speed':-5.0,'alt_for_variable_vert_speed':6000.0,
                      'vert_speed_base':4.5,'vert_speed_per_alt':7e-05,
                      'rate_of_turn':None,'turn_bank_angle':15.0,
                      'warning':True}
	    return p_info
        
    def check_platform(self,name):
        'Simple program that check the name of the flight path to platforms names'
        if any(p in name for p in ['p3','P3','P-3','p-3','p 3','P 3']): platform = 'p3'
        if any(p in name for p in ['er2','ER2','ER-2','er-2','ER 2','er 2']): platform = 'er2'
        if any(p in name for p in ['dc8','DC8','DC-8','dc-8','DC 8','dc 8']): platform = 'dc8'
        if any(p in name for p in ['c130','C130','C-130','c-130','C 130','c 130']): platform = 'c130'
        if any(p in name for p in ['bae','BAE','146']): platform = 'bae146'
        try:
            if not platform: platform = 'NA'
        except UnboundLocalError:
            platform = 'NA'
        return platform
        
    def get_rate_of_turn(self):
        'Function to calculate the rate of turn of the plane'
        if self.p_info.get('rate_of_turn'):
            rate_of_turn = self.p_info.get('rate_of_turn')
        elif self.p_info.get('turn_bank_angle'):
            rate_of_turn = 1091.0*np.tan(self.p_info['turn_bank_angle']*np.pi/180)/self.speed[0]
        else:            
            default_bank_angle = 15.0
            rate_of_turn = 1091.0*np.tan(default_bank_angle*np.pi/180)/self.speed[0] # degree per second
        return rate_of_turn

    def calculate(self):
        """
        Program to fill in all the missing pieces in the dict_position class
        Involves converting from metric to aviation units
        Involves calculating distances
        Involves calculating time of flight local and utc
        Fills in the waypoint numbers

        Assumes that blank spaces/nan are to be filled with new calculations
        """
        self.rate_of_turn = self.get_rate_of_turn()
        if not np.isfinite(self.rate_of_turn):
            self.rate_of_turn = 2.4
        self.n = len(self.lon)
        self.WP = range(1,self.n+1)
        for i in xrange(self.n-1):
            self.dist[i+1] = mu.spherical_dist([self.lat[i],self.lon[i]],[self.lat[i+1],self.lon[i+1]])
            if np.isfinite(self.alt.astype(float)[i+1]):
                self.alt_kft[i+1] = self.alt[i+1]*3.28084/1000.0
            elif np.isfinite(self.alt_kft.astype(float)[i+1]):
                self.alt[i+1] = self.alt_kft[i+1]*1000.0/3.28084
            else:
                self.alt[i+1] = self.get_alt(self.alt[0],self.alt[i])
                self.alt_kft[i+1] = self.alt[i+1]*3.28084/1000.0
            if np.isfinite(self.speed.astype(float)[i+1]):
                self.speed_kts[i+1] = self.speed[i+1]*1.94384449246
            elif np.isfinite(self.speed_kts.astype(float)[i+1]):
                self.speed[i+1] = self.speed_kts[i+1]/1.94384449246
            else:
                self.speed[i+1] = self.calcspeed(self.alt[i],self.alt[i+1])
                self.speed_kts[i+1] = self.speed[i+1]*1.94384449246  
            self.bearing[i] = mu.bearing([self.lat[i],self.lon[i]],[self.lat[i+1],self.lon[i+1]])
            self.endbearing[i] = (mu.bearing([self.lat[i+1],self.lon[i+1]],[self.lat[i],self.lon[i]])+180)%360.0
            try:
                self.bearing[i+1] = mu.bearing([self.lat[i+1],self.lon[i+1]],[self.lat[i+2],self.lon[i+2]])
            except:
                self.bearing[i+1] = self.endbearing[i]
            try:
                self.turn_deg[i+1] = abs(self.endbearing[i]-self.bearing[i+1])
            except:
                self.turn_deg[i+1] = 0.0
            self.turn_time[i+1] = (self.turn_deg[i+1]/self.rate_of_turn)/60.0
            if not np.isfinite(self.delayt.astype(float)[i+1]):
                self.delayt[i+1] = self.turn_time[i+1]
            #else:
            #    self.delayt[i+1] = self.delayt[i+1]+self.turn_time[i+1]
            self.climb_time[i+1] = self.calc_climb_time(self.alt[i],self.alt[i+1]) #defaults to P3 speed
            self.legt[i+1] = (self.dist[i+1]/(self.speed[i+1]/1000.0))/3600.0
            if self.legt[i+1] < self.climb_time[i+1]/60.0:
                self.legt[i+1] = self.climb_time[i+1]/60.0
            self.legt[i+1] += self.delayt[i+1]/60.0
            self.utc[i+1] = self.utc[i]+self.legt[i+1]
            if not np.isfinite(self.utc[i+1]):
                print self.utc
                import pdb; pdb.set_trace()
            
        self.local = self.utc+self.UTC_conversion
        self.dist_nm = self.dist*0.53996
        self.cumdist = self.dist.cumsum()
        self.cumdist_nm = self.dist_nm.cumsum()
        self.cumlegt = np.nan_to_num(self.legt).cumsum()
        
        self.datetime = self.calcdatetime()
        self.sza,self.azi = mu.get_sza_azi(self.lat,self.lon,self.datetime)
        
        self.time2xl()
        
    def force_calcspeed(self):
        """
        Program to override the current speed written in and calculate a new one
        """
        self.n = len(self.lon)
        for i in xrange(self.n-1):
            self.speed[i+1] = self.calcspeed(self.alt[i],self.alt[i+1])
            self.speed_kts[i+1] = self.speed[i+1]*1.94384449246

    def calcspeed(self,alt0,alt1):
        """
        Simple program to estimate the speed of the aircraft:
        P3 from Steven Howell based on TRACE-P
        ER2 from Samuel LeBlanc based on SEAC4RS
        """
        if self.p_info.get('base_speed'):
            TAS = self.p_info['base_speed'] + alt1*self.p_info['speed_per_alt']
            if alt1>self.p_info['max_speed_alt']:
                TAS = self.p_info['max_speed']
            if alt1>alt0+200.0:
                TAS = TAS-self.p_info['descent_speed_decrease']        
        else:
            if self.platform=='p3':
                TAS = 130.0+alt1/1000.0*7.5
                if alt1>6000.0:
                    TAS = 130.0+6*7.5
                if alt1>alt0+200.0:
                    TAS = TAS -15.0
            elif self.platform=='er2':
                TAS = 70+alt0*0.0071
            else:
                TAS = 130.0
        if not np.isfinite(TAS):
            TAS = 130.0
        return TAS

    def get_alt(self,alt0,alti):
        'Program to guesstimate the cruising altitude'
        if alti!=alt0:
            return alti
        if self.p_info.get('max_alt'):
            return self.p_info['max_alt']
        else:
            if self.platform=='p3':
                return 7500.0
            elif self.platform=='er2':
                return 19000.0
            elif self.platform=='c130':
                return 7500.0
            elif self.platform=='dc8':
                return 13000.0
            else:
                return alti
        
    def calc_climb_time(self,alt0,alt1):
        """
        Simple program to calculate the climb/descent time from previous missions
        Uses parameterization for P3 and ER2 for now.
        Default parameters are used when nothing is set.
        Uses altitude from previous point (alt0) and next point (alt1) in meters
        returns minutes of climb/descent time
        """
        if alt1>alt0:
            climb = True
            if not alt1: climb = False
        else:
            climb = False
        if self.p_info.get(''):
            if climb:
                if alt1>self.p_info['alt_for_variable_vert_speed']:
                    speed = self.p_info['vert_speed_base']-\
                            self.p_info['vert_speed_per_alt']*(alt1+alt0)/2.0
                else:
                    speed = self.p_info['climb_vert_speed']
            else:
                speed = self.p_info['descent_vert_speed']
        else:
            if self.platform=='p3':
                if climb:
                    if alt1 > 6000:
                        speed = 4.5-7e-05*(alt1+alt0)/2.0
                    else:
                        speed = 5.0
                else:
                    speed = -5.0
            elif self.platform=='er2':
                if climb:
                    speed = 24.0-0.0011*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            elif self.platform=='dc8':
                if climb:
                    speed = 15.0-0.001*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            elif self.platform=='c130':
                if climb:
                    speed = 10.0-0.001*(alt1+alt0)/2.0
                else:
                    speed = -10.0
            else:
                if climb:
                    speed = 5.0
                else:
                    speed = -5.0
        climb_time = (alt1-alt0)/speed/60.0
        if not np.isfinite(climb_time):
            climb_time = 5.0
            print 'climb time not finite for platform: %s, alt0:%f, alt1:%f' % (self.platform,alt0,alt1)
        return climb_time

    def calcdatetime(self):
        """
	Program to convert a utc time and datestr to datetime object
	"""
	from datetime import datetime
	dt = []
	for i,u in enumerate(self.utc):
            Y,M,D = [int(s) for s in self.datestr.split('-')]
            try:    
                hh = int(u)
            except ValueError:
                print 'Problem on line :%i with value %f'%(i,u)
                continue
	    mm = int((u-hh)*60.0)
	    ss = int(((u-hh)*60.0-mm)*60.0)
	    ms = int((((u-hh)*60.0-mm)*60.0-ss)*1000.0)
	    while hh > 23:
	    	hh = hh-24
		D = D+1
	    try:
                dt.append(datetime(Y,M,D,hh,mm,ss,ms))
            except ValueError:
                print 'Problem on line: %i with datetime for datestr: %s' %(i,self.datestr)
                print Y,M,D
                self.get_datestr_from_xl()
                Y,M,D = [int(s) for s in self.datestr.split('-')]
                try:
                    dt.append(datetime(Y,M,D,hh,mm,ss,ms))
                except ValueError:
                    print 'Big problem on 2nd try of calcdatetime with datestr, line: %i'%i
                    continue
	return dt

    def time2xl(self):
        """
        Convert the UTC fractional hours to hh:mm format for use in excel
        """
        self.cumlegt_xl = self.cumlegt/24.0
        self.utc_xl = self.utc/24.0
        self.local_xl = self.local/24.0
        self.legt_xl = self.legt/24.0

    def write_to_excel(self):
        """
        writes out the dict_position class values to excel spreadsheet
        """
        import numpy as np
        from xlwings import Range
        self.wb.set_current()
        Range('A2').value = np.array([self.WP,
                                      self.lat,
                                      self.lon,
                                      self.speed,
                                      self.delayt,
                                      self.alt,
                                      self.cumlegt_xl,
                                      self.utc_xl,
                                      self.local_xl,
                                      self.legt_xl,
                                      self.dist,
                                      self.cumdist,
                                      self.dist_nm,
                                      self.cumdist_nm,
                                      self.speed_kts,
                                      self.alt_kft,
                                      self.sza,
                                      self.azi,
                                      self.bearing,
                                      self.climb_time
                                      ]).T
        for i,c in enumerate(self.comments):
            Range('U%i'%(i+2)).value = c
        Range('G2:J%i'% (self.n+1)).number_format = 'hh:mm'
        Range('E2:E%i'% (self.n+1)).number_format = '0'
        Range('B:B').autofit('c')
        Range('C:C').autofit('c')

    def check_xl(self):
        """
        wrapper for checking excel updates.
        Reruns check_updates_excel whenever a line is found to be deleted
        """
        while self.check_updates_excel():
            if self.verbose:
                print 'line removed, cutting it out'

    def check_updates_excel(self):
        """
        Check for any change in the excel file
        If there is change, empty out the corresponding calculated areas
        Priority is always given to metric
        """
        from xlwings import Range
        import numpy as np
        self.wb.set_current()
        tmp = Range('A2:U%i'%(self.n+1)).value
        tmp0 = Range('A2:U2').vertical.value
        tmp2 = Range('B2:U2').vertical.value
        dim = np.shape(tmp)
        if len(dim)==1:
            tmp = [tmp]
            dim = np.shape(tmp)
        dim0 = np.shape(tmp0)
        if len(dim0)==1: dim0 = np.shape([tmp0])
        n0,_ = dim0
        n1,_ = dim
        dim2 = np.shape(tmp2)
        if len(dim2)==1: dim2 = np.shape([tmp2])
        n2,_ = dim2
        if n0>n1:
            tmp = tmp0
        if n2>n0:
            tmp2 = Range('A2:U%i'%(n2+1)).value
            if len(np.shape(tmp2))==1:
                tmp = [tmp2]
            else:
                tmp = tmp2
            if self.verbose:
                print 'updated to the longer points on lines:%i' %n2
        if self.verbose:
            print 'vertical num: %i, range num: %i' %(n0,n1)
        num = 0
        num_del = 0
        for i,t in enumerate(tmp):
            if len(t)<16: continue
            wp,lat,lon,sp,dt,alt,clt,utc,loc,lt,d,cd,dnm,cdnm,spkt,altk = t[0:16]
            try:
                sza,azi,bear,clbt,comm = t[16:21]
            except:
                sza,azi,comm = t[16:19]
            if wp > self.n:
                num = num+1
                self.appends(lat,lon,sp,dt,alt,clt,utc,loc,lt,d,cd,dnm,cdnm,spkt,altk,comm=comm)
            elif not wp: # check if empty
                if not lat:
                    num = num+1
                    self.dels(i)
                    self.move_xl(i)
                    self.n = self.n-1
                    return True
                else:
                    num = num+1
                    self.appends(lat,lon,sp,dt,alt,clt,utc,loc,lt,d,cd,dnm,cdnm,spkt,altk,comm=comm)
            else:
                changed = self.mods(i,lat,lon,sp,spkt,dt,alt,altk,comm)
                if i == 0:
                    if self.utc[i] != utc*24.0:
                        self.utc[i] = utc*24.0
                        changed = True
                if changed: num = num+1
                if self.verbose:
                    print 'Modifying line #%i' %i
        if self.n>(i+1):
            if self.verbose:
                print 'deleting points'
            for j in range(i+1,self.n-1):
                self.dels(j)
                self.n = self.n-1
                num = num+1
        if num>0:
            if self.verbose:
                print 'Updated %i lines from Excel, recalculating and printing' % num
            self.calculate()
            self.write_to_excel()
        self.num_changed = num
        return False

    def move_xl(self,i):
        """
        Program that moves up all excel rows by one line overriding the ith line
        """
        from xlwings import Range
        linesbelow = Range('A%i:U%i'%(i+3,self.n+1)).value
        n_rm = (self.n+1)-(i+3)
        linelist = False
        for j,l in enumerate(linesbelow):
            if type(l) is list:
                try:
                    l[0] = l[0]-1
                except:
                    yup = True
                linesbelow[j] = l
                linelist = True
        if not linelist:
            try:
                linesbelow[0] = linesbelow[0]-1
            except:
                yup = True
        Range('A%i:U%i'%(i+2,i+2)).value = linesbelow
        Range('A%i:U%i'%(self.n+1,self.n+1)).clear_contents()

    def dels(self,i):
        """
        program to remove the ith item in every object
        """
        import numpy as np
        if i+1>len(self.lat):
            print '** Problem: index out of range **'
            return
        self.lat = np.delete(self.lat,i)
        self.lon = np.delete(self.lon,i)
        self.speed = np.delete(self.speed,i)
        self.delayt = np.delete(self.delayt,i)
        self.alt = np.delete(self.alt,i)
        self.alt_kft = np.delete(self.alt_kft,i)
        self.speed_kts = np.delete(self.speed_kts,i)
        self.cumlegt = np.delete(self.cumlegt,i)
        self.utc = np.delete(self.utc,i)
        self.local = np.delete(self.local,i)
        self.legt = np.delete(self.legt,i)
        self.dist = np.delete(self.dist,i)
        self.cumdist = np.delete(self.cumdist,i)
        self.dist_nm = np.delete(self.dist_nm,i)
        self.cumdist_nm = np.delete(self.cumdist_nm,i)
        self.bearing = np.delete(self.bearing,i)
        self.endbearing = np.delete(self.endbearing,i)
        self.turn_deg = np.delete(self.turn_deg,i)
        self.turn_time = np.delete(self.turn_time,i)
        self.climb_time = np.delete(self.climb_time,i)
        self.sza = np.delete(self.sza,i)
        self.azi = np.delete(self.azi,i)
        self.comments.pop(i)
        try:
            self.WP = np.delete(self.WP,i)
        except:
            self.WP = range(1,len(self.lon))
        #print 'deletes, number of lon left:%i' %len(self.lon)

    def appends(self,lat,lon,sp=None,dt=None,alt=None,
                clt=None,utc=None,loc=None,lt=None,d=None,cd=None,
                dnm=None,cdnm=None,spkt=None,altk=None,
                bear=0.0,endbear=0.0,turnd=0.0,turnt=0.0,climbt=0.0,
                sza=None,azi=None,comm=None):
        """
        Program that appends to the current class with values supplied, or with defaults from the command line
        """
        import numpy as np
        self.lat = np.append(self.lat,lat)
        self.lon = np.append(self.lon,lon)
        self.speed = np.append(self.speed,sp)
        self.delayt = np.append(self.delayt,dt)
        self.alt = np.append(self.alt,alt)
        if not clt: clt = np.nan
        if not utc: utc = np.nan
        if not loc: loc = np.nan
        if not lt: lt = np.nan
        self.cumlegt = np.append(self.cumlegt,clt*24.0)
        self.utc = np.append(self.utc,utc*24.0)
        self.local = np.append(self.local,loc*24.0)
        self.legt = np.append(self.legt,lt*24.0)
        self.dist = np.append(self.dist,d)
        self.cumdist = np.append(self.cumdist,cd)
        self.dist_nm = np.append(self.dist_nm,dnm)
        self.cumdist_nm = np.append(self.cumdist_nm,cdnm)
        self.speed_kts = np.append(self.speed_kts,spkt)
        self.alt_kft = np.append(self.alt_kft,altk)
        self.bearing = np.append(self.bearing,bear)
        self.endbearing = np.append(self.endbearing,endbear)
        self.turn_deg = np.append(self.turn_deg,turnd)
        self.turn_time = np.append(self.turn_time,turnt)
        self.climb_time = np.append(self.climb_time,climbt)
        self.sza = np.append(self.sza,sza)
        self.azi = np.append(self.azi,azi)
        self.comments.append(comm)
        
    def inserts(self,i,lat,lon,sp=None,dt=None,alt=None,
                clt=None,utc=None,loc=None,lt=None,d=None,cd=None,
                dnm=None,cdnm=None,spkt=None,altk=None,
                bear=0.0,endbear=0.0,turnd=0.0,turnt=0.0,climbt=0.0,
                sza=None,azi=None,comm=None):
        """
        Program that appends to the current class with values supplied, or with defaults from the command line
        """
        import numpy as np
        self.lat = np.insert(self.lat,i,lat)
        self.lon = np.insert(self.lon,i,lon)
        self.speed = np.insert(self.speed,i,sp)
        self.delayt = np.insert(self.delayt,i,dt)
        self.alt = np.insert(self.alt,i,alt)
        if not clt: clt = np.nan
        if not utc: utc = np.nan
        if not loc: loc = np.nan
        if not lt: lt = np.nan
        self.cumlegt = np.insert(self.cumlegt,i,clt*24.0)
        self.utc = np.insert(self.utc,i,utc*24.0)
        self.local = np.insert(self.local,i,loc*24.0)
        self.legt = np.insert(self.legt,i,lt*24.0)
        self.dist = np.insert(self.dist,i,d)
        self.cumdist = np.insert(self.cumdist,i,cd)
        self.dist_nm = np.insert(self.dist_nm,i,dnm)
        self.cumdist_nm = np.insert(self.cumdist_nm,i,cdnm)
        self.speed_kts = np.insert(self.speed_kts,i,spkt)
        self.alt_kft = np.insert(self.alt_kft,i,altk)
        self.bearing = np.insert(self.bearing,i,bear)
        self.endbearing = np.insert(self.endbearing,i,endbear)
        self.turn_deg = np.insert(self.turn_deg,i,turnd)
        self.turn_time = np.insert(self.turn_time,i,turnt)
        self.climb_time = np.insert(self.climb_time,i,climbt)
        self.sza = np.insert(self.sza,i,sza)
        self.azi = np.insert(self.azi,i,azi)
        self.comments.insert(i,comm)

    def mods(self,i,lat=None,lon=None,sp=None,spkt=None,
             dt=None,alt=None,altk=None,comm=None):
        """
        Program to modify the contents of the current class if
        there is an update on the line, defned by i
        If anything is not input, then the default of NaN is used
        comments are treated as none
        """
        import numpy as np
        if i+1>len(self.lat):
            print '** Problem with index too large in mods **'
            return
        changed = False
        compare_altk = True
        compare_speedk = True
        self.toempty = {'speed':0,'delayt':0,'alt':0,'speed_kts':0,'alt_kft':0}
        if lat is None: lat = np.nan
        if lon is None: lon = np.nan
        if sp is None: sp = np.nan
        if spkt is None: spkt = np.nan
        if dt is None: dt = np.nan
        if alt is None: alt = np.nan
        if altk is None: altk = np.nan
        if self.lat[i] != lat:
            self.lat[i] = lat
            changed = True
        if self.lon[i] != lon:
            self.lon[i] = lon
            changed = True
        if self.speed[i] != sp:
            if np.isfinite(sp):
                self.speed[i] = sp
                self.toempty['speed_kts'] = 1
                compare_speedk = False
                changed = True
        if self.speed_kts[i] != spkt:
            if np.isfinite(spkt)&compare_speedk:
                self.speed_kts[i] = spkt
                self.toempty['speed'] = 1
                changed = True
        if self.delayt[i] != dt:
            if i != 0:
                self.delayt[i] = dt
                changed = True
        if self.alt[i] != alt:
            if np.isfinite(alt):
                self.alt[i] = alt
                self.toempty['alt_kft'] = 1
                compare_altk = False
                changed = True
        if self.alt_kft[i] != altk:
            if np.isfinite(altk)&compare_altk:
                self.alt_kft[i] = altk
                self.toempty['alt'] = 1
                changed = True
        for s in self.toempty:
            if self.toempty.get(s):
                v = getattr(self,s)
                v[i] = np.nan
                setattr(self,s,v)
        if not self.comments[i] == comm:
            if comm: 
                self.comments[i] = comm
                changed = True
        return changed

    def Open_excel(self,filename=None,sheet_num=1,campaign='None',platform_file='platform.txt'):
        """
        Purpose:
            Program that opens and excel file and creates the proper links with pytho
        Inputs:
            filename of excel file to open
            sheet_num: what sheet to activate and load
            campaign: (optional) if set, does ask to verify the campaign for each sheet
        Outputs:
            wb: workbook instance
        Dependencies:
            xlwings
            Excel (win or mac)
            re
            tkSimpleDialog (for datestr)
            datetime
        Example:
            ...
        History:
            Written: Samuel LeBlanc, 2015-08-18, NASA Ames, CA
            Modified: Samuel LeBlanc, 2016-06-07, NASA Ames, CA
                      - updated to handle the new excel format with climb time and bearing
                      - added datestr checking and dialog interface
            Modified: Samuel LeBlanc, 2016-07-28, NASA Ames, CA
                      - updated to handle the platform file definitions and check on utc_conversion factor
        """
        from xlwings import Workbook, Sheet, Range
        import numpy as np
        if not filename:
            print 'No filename found'
            return
        try:
            wb = Workbook(filename)
        except Exception,ie:
            print 'Exception found:',ie
            return
        self.name = Sheet(sheet_num).name
        Sheet(sheet_num).activate()
        print 'Activating sheet:%i, name:%s'%(sheet_num,Sheet(sheet_num).name)
        self.platform, self.p_info,use_file = self.get_platform_info(self.name,platform_file)
        print 'Using platform data for: %s' %self.platform
        self.datestr = str(Range('W1').value).split(' ')[0]
        self.verify_datestr()
        if campaign is not 'None':
            self.campaign
        else:
            self.campaign = str(Range('X1').value).split(' ')[0]
            self.verify_campaign()
        self.UTC_conversion = self.verify_UTC_conversion()
        return wb
        
    def verify_datestr(self):
        'Verify the input datestr is correct'
        import re
        import tkSimpleDialog
        if not self.datestr:
            self.datestr = tkSimpleDialog.askstring('Flight Date','No datestring found!\nPlease input Flight Date (yyyy-mm-dd):')
        if not re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}',self.datestr):
            self.datestr = tkSimpleDialog.askstring('Flight Date','No datestring found!\nPlease input Flight Date (yyyy-mm-dd):')
        if not self.datestr:
            print 'No datestring found! Using todays date'
            from datetime import datetime
            self.datestr = datetime.utcnow().strftime('%Y-%m-%d')
            
    def verify_campaign(self):
        'verify the input campaign value'
        import tkSimpleDialog
        self.campaign = tkSimpleDialog.askstring('Campaign name','Please verify campaign name:',initialvalue=self.campaign)
        
    def verify_UTC_conversion(self):
        'verify the input UTC conversion when reading a excel file'
        from xlwings import Range
        tmp0 = Range('A2:U2').value
        _,_,_,_,_,_,_,utc,loc,_,_,_,_,_,_,_ = tmp0[0:16]
        return loc*24-utc*24

    def Create_excel(self,name='P3 Flight path',newsheetonly=False):
        """
        Purpose:
            Program that creates the link to an excel file
            Starts and populates the first line and titles of the excel workbook
        Inputs:
            none
        Outputs:
            wb: workbook instance 
        Dependencies:
            xlwings
            Excel (win or mac)
        Required files:
            none
        Example:
            ...
        Modification History:
            Written: Samuel LeBlanc, 2015-07-15, Santa Cruz, CA
            Modified: Samuel LeBlanc, 2015-08-07, Santa Cruz, CA
                    - put into the dic_position class, modified slightly
            Modified: Samuel LeBlanc, 2015-08-25, NASA Ames, CA
                    - modify to permit creation of a new sheet within the current workbook
            
        """
        from xlwings import Workbook, Sheet, Range, Chart
        import numpy as np
        if newsheetonly:
            Sheet(1).add(name=name)
            self.sheet_num = self.sheet_num+1
            wb = Workbook.current()
        else:
            wb = Workbook()
            self.name = name
            Sheet(1).name = self.name
        Range('A1').value = ['WP','Lat\n[+-90]','Lon\n[+-180]',
                             'Speed\n[m/s]','delayT\n[min]','Altitude\n[m]',
                             'CumLegT\n[hh:mm]','UTC\n[hh:mm]','LocalT\n[hh:mm]',
                             'LegT\n[hh:mm]','Dist\n[km]','CumDist\n[km]',
                             'Dist\n[nm]','CumDist\n[nm]','Speed\n[kt]',
                             'Altitude\n[kft]','SZA\n[deg]','AZI\n[deg]',
                             'Bearing\n[deg]','ClimbT\n[min]','Comments']
        top_line = Range('A1').horizontal
        address = top_line.get_address(False,False)
        from sys import platform
        if platform.startswith('win'):
            from win32com.client import Dispatch
            xl = Dispatch("Excel.Application")
         #   xl.ActiveWorkbook.Windows(1).SplitColumn = 0.4
            xl.ActiveWorkbook.Windows(1).SplitRow = 1.0
            xl.Range(address).Font.Bold = True
        top_line.autofit()
        Range('G2:J2').number_format = 'hh:mm'
        Range('W1').value = self.datestr
        Range('X1').value = self.campaign
        Range('Z1').value = 'Created with'
        Range('Z2').value = 'moving_lines'
        Range('Z3').value = self.__version__
        Range('W:W').autofit('c')
        Range('X:X').autofit('c')
        Range('Z:Z').autofit('c')
        #Range('A2').value = np.arange(50).reshape((50,1))+1
        return wb

    def switchsheet(self,i):
        'Switch the active sheet with name supplied'
        from xlwings import Sheet
        Sheet(i+1).activate()

    def save2xl(self,filename=None):
        """
        Simple to program to initiate the save function in Excel
        Same as save button in Excel
        """
        self.wb.save(filename)

    def get_datestr_from_xl(self):
        'Simple program to get the datestr from the excel spreadsheet'
        self.datestr = str(Range('W1').value).split(' ')[0]
        
    def save2txt(self,filename=None):
        """ 
	Simple method to save the points to a text file.
	For input with idl and matlab
	"""
	f = open(filename,'w+')
	f.write('#WP  Lon[+-180]  Lat[+-90]  Speed[m/s]  delayT[min]  Altitude[m]'+
            '  CumLegT[H]  UTC[H]  LocalT[H]'+
            '  LegT[H]  Dist[km]  CumDist[km]'+
            '  Dist[nm]  CumDist[nm]  Speed[kt]'+
            '  Altitude[kft]  SZA[deg]  AZI[deg]  Bearing[deg]  Climbt[min]  Comments\n')
        for i in xrange(self.n):
            f.write("""%-2i  %+2.8f  %+2.8f  %-4.2f  %-3i  %-5.1f  %-2.2f  %-2.2f  %-2.2f  %-2.2f  %-5.1f  %-5.1f  %-5.1f  %-5.1f  %-3.1f %-3.2f  %-3.1f  %-3.1f  %-3.1f  %-3i  %s  \n""" %(
                    i+1,self.lon[i],self.lat[i],self.speed[i],
                    self.delayt[i],self.alt[i],self.cumlegt[i],
                    self.utc[i],self.local[i],self.legt[i],
                    self.dist[i],self.cumdist[i],self.dist_nm[i],self.cumdist_nm[i], 
                    self.speed_kts[i],self.alt_kft[i],self.sza[i],self.azi[i],self.bearing[i],self.climb_time[i],self.comments[i]))


    def save2kml(self,filename=None):
        """
        Program to save the points contained in the spreadsheet to a kml file
        """
        import simplekml
        from xlwings import Sheet
        if not filename:
            raise NameError('filename not defined')
            return
        if not self.netkml:
            self.netkml = simplekml.Kml(open=1)
            self.netkml.name = 'Flight plan on '+self.datestr
            net = self.netkml.newnetworklink(name=self.datestr)
            net.link.href = filename
            net.link.refreshmode = simplekml.RefreshMode.onchange
            net.link.camera = simplekml.Camera(latitude=self.lat[0], longitude=self.lon[0], altitude=3000.0, roll=0, tilt=0,
                          altitudemode=simplekml.AltitudeMode.relativetoground)
            filenamenet = filename+'_net.kml'
            self.netkml.save(filenamenet)
            self.kml = simplekml.Kml(open=1)
        for j in xrange(Sheet.count()):
            self.switchsheet(j)
            self.name = Sheet(j+1).name
            self.check_xl()
            self.calculate()
            self.kmlfolder = self.kml.newfolder(name=self.name)
            #self.kml.document = simplekml.Folder(name = self.name)
            self.print_points_kml(self.kmlfolder)
            self.print_path_kml(self.kmlfolder,color=self.color,j=j)
        self.kml.camera = simplekml.Camera(latitude=self.lat[0], longitude=self.lon[0], altitude=3000.0, roll=0, tilt=0,
                          altitudemode=simplekml.AltitudeMode.relativetoground)
        self.kml.save(filename)
        try: 
            self.kml.savekmz(filename.replace('kml','kmz'))
        except:
            print 'saving kmz didnt work'
            
        if not self.googleearthopened:
            #self.openGoogleEarth(filenamenet)
            self.openGoogleEarth(filename.replace('kml','kmz'))
            self.googleearthopened = True

    def print_points_kml(self,folder):
        """
        print the points saved in lat, lon
        """
        import simplekml
        from excel_interface import get_curdir
        if not self.kml:
            raise NameError('kml not initilaized')
            return
        for i in xrange(self.n):
            pnt = folder.newpoint()
            pnt.name = 'WP # {}'.format(self.WP[i])
            pnt.coords = [(self.lon[i],self.lat[i],self.alt[i]*10.0)]
            pnt.altitudemode = simplekml.AltitudeMode.relativetoground
            pnt.extrude = 1
            try:
                path = self.kml.addfile(get_curdir()+'//map_icons//number_{}.png'.format(self.WP[i]))
                pnt.style.iconstyle.icon.href = path
            except:
                pnt.style.iconstyle.icon.href = get_curdir()+'//map_icons//number_{}.png'.format(self.WP[i])
            pnt.description = """UTC[H]=%2.2f\nLocal[H]=%2.2f\nCumDist[km]=%f\nspeed[m/s]=%4.2f\ndelayT[min]=%f\nSZA[deg]=%3.2f\nAZI[deg]=%3.2f\nBearing[deg]=%3.2f\nClimbT[min]=%f\nComments:%s""" % (self.utc[i],self.local[i],self.cumdist[i],
                                                                   self.speed[i],self.delayt[i],self.sza[i],
                                                                   self.azi[i],self.bearing[i],self.climb_time[i],self.comments[i])

    def print_path_kml(self,folder,color='red',j=0):
        """
        print the path onto a kml file
        """
        import simplekml
        import numpy as np
        cls = [simplekml.Color.red,simplekml.Color.blue,simplekml.Color.green,simplekml.Color.cyan,
               simplekml.Color.magenta,simplekml.Color.yellow,simplekml.Color.black,simplekml.Color.lightcoral,
               simplekml.Color.teal,simplekml.Color.darkviolet,simplekml.Color.orange]
        path = folder.newlinestring(name=self.name)
        coords = [(lon,lat,alt*10) for (lon,lat,alt) in np.array((self.lon,self.lat,self.alt)).T]
        path.coords = coords
        path.altitudemode = simplekml.AltitudeMode.relativetoground
        path.extrude = 1
        path.style.linestyle.color = cls[j]
        path.style.linestyle.width = 4.0

    def openGoogleEarth(self,filename=None):
        """
        Function that uses either COM object or appscript (not yet implemented)
        to load the new Google Earth kml file
        """
        if not filename:
            print 'no filename defined, returning'
            return
        from sys import platform
        from os import startfile
        if platform.startswith('win'):
            try:
                from win32com.client import Dispatch
                ge = Dispatch("GoogleEarth.ApplicationGE")
                ge.OpenKmlFile(filename,True)
            except:
                startfile(filename)
        else:
            startfile(filename)

    def save2gpx(self,filename=None):
        'Program to save the waypoints and track in gpx format'
        if not filename:
            print '** no filename selected, returning without saving **'
            return
        import gpxpy as g
        import gpxpy.gpx as gg
        f = gg.GPX()
        route = gg.GPXRoute(name=self.datestr)
        for i,w in enumerate(self.WP):
            rp = gg.GPXRoutePoint(name='WP#%i'%w,latitude=self.lat[i],
                                  longitude=self.lon[i],
                                  elevation = self.alt[i],
                                  time = self.utc2datetime(self.utc[i]),
                                  comments = self.comments[i]
                                  )
            route.points.append(rp)
        f.routes.append(route)
        fp = open(filename,'w')
        fp.write(f.to_xml())
        fp.close()
        print 'GPX file saved to:'+filename      
		
    def save2ict(self,filepath=None):
        'Program to save the flight track as simulated ict file. Similar to what is returned from flights'
        from datetime import datetime
        import re
        if not filepath:
            print '** no filepath selected, returning without saving **'
            return
        dt = 60 #seconds
        # setup data dict
        dict_in = {'Start_UTC':{'original_data':self.utc*3600.0,'unit':'seconds from midnight UTC','long_description':'time keeping'},
                   'Latitude':{'original_data':self.lat,'unit':'Degrees (North positive)','long_description':'Planned latitude position of the aircraft','format':'4.9f'},
                   'Longitude':{'original_data':self.lon,'unit':'Degrees (East positive)','long_description':'Planned longitude position of the aircraft','format':'4.9f'},
                   'Altitude':{'original_data':self.alt,'unit':'meters (above sea level)','long_description':'Planned altitude of the aircraft','format':'5.0f'},
                   'speed':{'original_data':self.speed,'unit':'meters per second (m/s)','long_description':'Estimated speed of aircraft'},
                   'SZA':{'original_data':self.sza,'unit':'degrees from zenith','long_description':'Elevation position of the sun in the sky per respect to zenith'},
                   'AZI':{'original_data':self.azi,'unit':'degrees from north','long_description':'Azimuthal position of the sun in the sky per respect to north'},
                   'Bearing':{'original_data':self.bearing,'unit':'degrees from north','long_description':'Direction of travel of the plane per respect to north'}}
        d_dict = self.interp_points_for_ict(dict_in,dt=dt) 
        # setup header dict
        hdict = {'PI':'Samuel LeBlanc',
                 'Institution':'NASA Ames Research Center',
                 'Instrument':'Simulated flight plan',
                 'campaign':self.campaign,
                 'time_interval':dt,
                 'now':datetime.strptime(self.datestr,'%Y-%m-%d'),
                 'special_comments':'Simulated aircraft data interpolated from flight plan waypoints',
                 'PI_contact':'Samuel LeBlanc, samuel.leblanc@nasa.gov',
                 'platform':self.platform,
                 'location':'N/A',
                 'instrument_info':'None',
                 'data_info':'Compiled with flight planner: moving lines {version}'.format(version=self.__version__),
                 'uncertainty':'Undefined',
                 'DM_contact':'See PI',
                 'project_info':self.campaign,
                 'stipulations':'None',
                 'rev_comments':"""  RA: First iteration of the flight plan"""}
        order = ['Latitude','Longitude','Altitude','speed','Bearing','SZA','AZI']
        fcomment = self.name.upper().replace(self.platform.upper(),'').strip('_').strip('-').strip()
        wu.write_ict(hdict,d_dict,filepath=filepath+'//',
                     data_id='{}-Flt-plan'.format(self.campaign),loc_id=self.platform,date=self.datestr.replace('-',''),rev='RA',order=order,file_comment=fcomment)
        
    def interp_points_for_ict(self,dict_in,dt=60.0):
        'Program to interpolate between the waypoints to have a consistent time, defined by dt (defaults to 60 seconds), the variables to be interpolated is defined by dict_in'
        utcs = np.arange(self.utc[0]*3600,self.utc[-1]*3600,dt)
        # create a dict of points using the input dict as a basis, requires it to have the original_data key for each dict entry
        # should be replaced by a interpolator that uses great circles
        for k in dict_in.keys():
            if k=='Start_UTC': 
                dict_in[k]['data'] = utcs
            else:
                fx = interpolate.interp1d(self.utc*3600,dict_in[k]['original_data'],bounds_error=False)
                dict_in[k]['data'] = fx(utcs)
        return dict_in      

    def utc2datetime(self,utc):
        'Program to convert the datestr and utc to valid datetime class'
        from datetime import datetime
        y,m,d = self.datestr.split('-')
        year = int(y)
        month = int(m)
        day = int(d)
        hour = int(utc)
        minut = (utc-hour)*60
        minutes = int(minut)
        secon = (minut-minutes)*60
        seconds = int(secon)
        microsec = int((secon-seconds)*100)
        return datetime(year,month,day,hour,minutes,seconds,microsec)

    def exremove(self):
        'Program to remove the current Sheet'
        print 'Not yet'
        pass
        

def populate_ex_arr(filename=None,colorcycle=['red','blue','green']):
    """
    Purpose:
        Program that opens an excel file, and runs through the sheets 
        creates an array of dict_position
    Input:
        filename of excel file
	colorcycle
    Output:
        excel_interface dict_position array
    Dependeices:
        xlwings
    History:
        written: Samuel LeBlanc, NASA Ames, Santa Cruz, CA 2015-09-10
    """
    from xlwings import Workbook,Sheet
    import excel_interface as ex
    arr = []
    wb = Workbook(filename)
    num = Sheet.count()
    for i in range(num):
        if i==0:
            campaign = 'None'
        else:
            campaign = arr[i-1].campaign
        arr.append(ex.dict_position(filename=filename,sheet_num=i+1,color=colorcycle[i],campaign='None'))
    return arr
    
def save2xl_for_pilots(filename,ex_arr):
    """
    Purpose:
        Program that opens and saves a new excel file, and runs through the current opened sheets 
        creates an excel file in the format defined for pilots. format option is defined in the dict_position
    Input:
        filename: filename of new excel file
        ex_arr: array of excel interface dict_position to be saved
    Output:
        new file
    Dependices:
        xlwings
    History:
        written: Samuel LeBlanc, NASA Ames, CA 2016-07-28
    """
    from xlwings import Workbook,Sheet,Range
    from excel_interface import format_lat_lon
    wb_pilot = Workbook()
    sheet_one = True
    for a in ex_arr:
        if sheet_one:
            Sheet(1).name = a.name
            sheet_one = False
        else:
            Sheet(1).add(name=a.name)
        Range('A1').value = ['WP','Lat\n[+-90]','Lon\n[+-180]',
                             'Altitude\n[kft]','Comments']
        top_line = Range('A1').horizontal
        address = top_line.get_address(False,False)
        from sys import platform
        if platform.startswith('win'):
            from win32com.client import Dispatch
            xl = Dispatch("Excel.Application")
            xl.ActiveWorkbook.Windows(1).SplitRow = 1.0
            xl.Range(address).Font.Bold = True
        top_line.autofit()
        Range('G2:J2').number_format = 'hh:mm'
        Range('W1').value = a.datestr
        Range('X1').value = a.campaign
        Range('Z1').value = 'Created with'
        Range('Z2').value = 'moving_lines'
        Range('Z3').value = a.__version__
        Range('W:W').autofit('c')
        Range('X:X').autofit('c')
        Range('Z:Z').autofit('c')
        for i in range(len(a.lon)):
            lat_f,lon_f = format_lat_lon(a.lat[i],a.lon[i],format=a.pilot_format)
            if a.delayt[i]>3.0:
                comment = 'delay: {} min, {}'.format(a.delayt[i],a.comments[i])
            else:
                comment = a.comments[i]
            Range('A{:d}'.format(i+2)).value = [a.WP[i],lat_f,lon_f,a.alt_kft[i],comment]
    wb_pilot.save(filename)
    wb_pilot.close()        
        
def format_lat_lon(lat,lon,format='DD MM SS'):
    'Lat and lon formatter'
    if format == 'DD MM SS':
        def deg_to_dms(deg):
            d = int(deg)
            md = abs(deg - d) * 60
            m = int(md)
            sd = (md - m) * 60
            return [d, m, sd]
        latv = deg_to_dms(lat)
        lonv = deg_to_dms(lon)
        lat_f = '{:02d} {:02d} {:02.3f}'.format(latv[0],latv[1],latv[2])
        lon_f = '{:02d} {:02d} {:02.3f}'.format(lonv[0],lonv[1],lonv[2])
    return lat_f,lon_f
        
def get_curdir():
    'Program that gets the path of the script: for use in finding extra files'
    from os.path import dirname, realpath
    from sys import argv
    if __file__:
        path = dirname(realpath(__file__))
    else:
        path = dirname(realpath(argv[0]))
    return path