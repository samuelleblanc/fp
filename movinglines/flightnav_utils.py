

import tkinter.messagebox as tkMessageBox


def parse_tracks(track):
    'Extracts the track information into a dict with named latitudes and longitudes for each track node, removes double tracks, and retains the navaid fixes'
    
    track_out = {}
    
    for t in track:
        track_out[t.ident] = {'lats':[nd.lat for nd in t.route.nodes],
                              'lons':[nd.lon for nd in t.route.nodes],
                              'validFrom':t.validFrom,
                              'validTo':t.validTo,
                              'navaid':[(nd.ident,nd.lon,nd.lat) for nd in t.route.nodes if nd.type.lower()=='fix'],
                              'levels':t.route.eastLevels + t.route.westLevels}

    return track_out


def get_NATs():
    'function to go and fetch from the flighplandb api the north atlantic tracks'
    import asyncio
    import flightplandb
    tkMessageBox.showwarning('Obtaining the NAT routes','Using data from the Flight Plan Database [https://flightplandatabase.com] \n The route data is for flight simulation use only and is not suitable for real-world aviation or navigation.')
    try:
        nat_tracks = asyncio.run(flightplandb.nav.nats())
    except Exception as ei:
        tkMessageBox.showwarning('Error obtaining the NAT routes',f'Error occurred when fetching the NAT routes: {ei}')
        return None
        
    return parse_tracks(nat_tracks)
    
    
def get_POCATS():
    import asyncio
    import flightplandb
    'function to go and fetch from the flighplandb api the Pacific Oceanic Airborne tracks'
    tkMessageBox.showwarning('Obtaining the POCATS routes','Using data from the Flight Plan Database [https://flightplandatabase.com] \n The route data is for flight simulation use only and is not suitable for real-world aviation or navigation.')
    try:
        pocat_tracks = asyncio.run(flightplandb.nav.pacots())
    except Exception as ei:
        tkMessageBox.showwarning('Error obtaining the POCATS routes',f'Error occurred when fetching the POCATS routes: {ei}')
        return None
        
    return parse_tracks(pocat_tracks)
    
    
def get_recent_FAACIFP(file_path=None):
    'Quick function to check if the FAACIFP18 file is recent enough, based on the website: https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/cifp/download/'
    import os
    file_path = os.path.abspath('./FAACIFP18')
    
    return file_path
    
    
def nearest_vor_rdme(lat, lon, vors, mag_decl=11.0,file_path=''):
    """
    Find the nearest VOR in vors [(ident, vlat, vlon)] and return the rDME string
    formatted as '{IDENT}{radial:03d}{dist_nm:03d}', e.g. 'INK355016'.
    Radial is the magnetic bearing from the VOR to the waypoint.
    """
    import map_utils as mu
    if not vors:
        return ''
    best_ident, best_dist_km, best_radial = '', float('inf'), 0
    for ident, vlat, vlon in vors:
        dist_km = mu.spherical_dist([lat, lon], [vlat, vlon])
        if dist_km < best_dist_km:
            best_dist_km = dist_km
            best_ident = ident
            best_radial = mu.bearing([vlat, vlon], [lat, lon])
    dist_nm = int(round(best_dist_km / 1.852))
    if file_path:
        mag_decl = lookup_vor_declination(file_path, target_vor=best_ident)
    if mag_decl is None:
        tkMessageBox.showwarning('Problem with rDME',f'Error occured when finding the magnetic declination of the VOR for rDME')
        return ''
    mag_radial = int(round((360.0 + best_radial - mag_decl) % 360.0))
    
    return '{}{:03d}{:03d}'.format(best_ident, mag_radial, dist_nm)
    
def load_vor_navaids():
    """Download OurAirports navaids.csv and return [(ident, lat, lon)] for VOR/VORTAC/VOR-DME navaids."""
    import requests, csv, io
    VOR_TYPES = {'VOR', 'VOR-DME', 'VORTAC'}
    url = "https://davidmegginson.github.io/ourairports-data/navaids.csv"
    vors = []
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.content.decode('utf-8', errors='replace'))))
        for row in rows:
            if (row.get('type') or '').strip().upper() not in VOR_TYPES:
                continue
            ident = (row.get('ident') or '').strip().upper()
            try:
                vlat = float(row.get('latitude_deg') or '')
                vlon = float(row.get('longitude_deg') or '')
            except ValueError:
                continue
            if ident:
                vors.append((ident, vlat, vlon))
    except Exception:
        pass
    return vors
    
def lookup_vor_declination(file_path: str, target_vor: str):
    """
    Scans a FAACIFP18 file line-by-line, targeting a specific VOR identifier.
    Returns the magnetic declination as a signed float (East = +, West = -), 
    or None if the VOR record is not found.
    """
    # Ensure standard ARINC 424 padding (exactly 3 chars, padded with spaces if shorter)
    target_vor = f"{target_vor.strip():<3}"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # Structurally reject short procedural lines immediately
            if len(line) < 79:
                continue
                
            # Direct index matches for Record Type 'D', Sub-type 'V', and the VOR Name
            if line[4] == 'D' and line[13:16] == target_vor:
                mag_var_raw = line[74:79].strip()    # Extract variation block (e.g., 'E0150')
                
                if len(mag_var_raw) == 5:
                    direction = mag_var_raw[0]       # 'E' or 'W'
                    try:
                        degrees = int(mag_var_raw[1:]) / 10.0
                        return -degrees if direction == 'W' else degrees
                    except ValueError:
                        print('Value Error in rDME calc - lookup vor for declination')
                        return None
                        
    return None  # Return None if the master record wasn't found

