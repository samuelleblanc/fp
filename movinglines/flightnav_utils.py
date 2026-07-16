

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
    
    
def nearest_vor_rdme(lat, lon, vors, mag_decl=0.0):
    """
    Find the nearest VOR in vors [(ident, vlat, vlon)] and return the rDME string
    formatted as '{IDENT}{radial:03d}{dist_nm:03d}', e.g. 'INK355016'.
    Radial is the magnetic bearing from the VOR to the waypoint.
    """
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
    mag_radial = int(round((360.0 + best_radial - mag_decl) % 360.0))
    return '{}{:03d}{:03d}'.format(best_ident, mag_radial, dist_nm)