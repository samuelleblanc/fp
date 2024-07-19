#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate ground tracks and footprints as kml files for Google Earth.

This downloads the latest TLE (two-line element) file for a chosen satellite
and generates a ground track for a specified number of future
time points. Then it takes an input footprint and builds the corners of a
polygon to save into a .kml document.

TODO: Fix the bug where it can't create a polygon passing over the 180
Longitude without circling around Earth. I think I can just convert to
cartesian coordinates (x, y, z) but simplekml doesn't seem like it accepts
anything but lat lon coordinates.

Current workaround: Just don't make lines or polygons that cross the
Antimeridian. Make the labels though.

Author:
    James Allen - Wed 19 Jun 2024
"""

# %% Imports

from datetime import datetime, timedelta
import requests

from geopy.distance import distance
import numpy as np
import pandas as pd
import pvlib
import simplekml
from simplekml import Style
from skyfield.api import load, EarthSatellite, wgs84

# %% Functions


# a hash associating a NORAD catalog number for each satellite we're
# interested in. Note that this is in the MySQL table webstore.overhead_pass
satToCatalogNumber = {
    "AQUA": 27424,
    "NPP": 37849,
    "OCEANSAT-2": 35931,
    "LANDSAT-8": 39084,
    "SENTINEL-3A": 41335,
    "JPSS1": 43013,
    "SEAHAWK-1": 43820,
    "SENTINEL-3B": 43437,
    "SENTINEL-2A": 40697,
    "SENTINEL-2B": 42063,
    "GCOM-C": 43065,
    "JPSS2": 54234,
    "PACE": 58928,
    "EARTHCARE": 59908
}

satToSwath = {
    "PACE": 50,
    "EARTHCARE": [35,115]
}

satToColor = {
    "PACE": {'line':'black','poly':'red'},
    "EARTHCARE": {'line':'darkgreen','poly':'azure'}
}

def fetch_latest_tle(sat="PACE"):
    """
    Fetch the latest TLE data for the PACE satellite.

    Parameters
    ----------
    sat : str, optional. Defaults to "PACE"
        The satellite we're getting the TLE for. Should be a key in
        satToCatalogNumber.

    Returns
    -------
    list of str
        TLE lines for the PACE satellite.
    """
    url = (f"https://celestrak.org/NORAD/elements/gp.php?"
           f"CATNR={satToCatalogNumber[sat]}")
    response = requests.get(url)
    tle_lines = response.text.splitlines()
    return tle_lines[1:3]


def load_tle(tle_file):
    """
    Load TLE data from a file.

    Parameters
    ----------
    tle_file : str
        Path to the TLE file.

    Returns
    -------
    list of str
        TLE lines.
    """
    with open(tle_file, 'r') as file:
        tle_lines = file.readlines()
    return [line.strip() for line in tle_lines]


def build_timestamps(start_datetime=None, time_resolution=1, time_length=1.0):
    """
    List dates for overpass predictions at a specified resolution.

    Notes
    -----
    - Orbit prediciton is dependent on the time resolution; too long, and the
        bearing calculations are too far apart as the lat/lons shift rapidly.
    - This takes one timestamp before and after the official start since
        polygons are built off these as midpoints.

    Parameters
    ----------
    start_datetime : datetime, optional
        First timepoint for orbit predictions. Defaults to the most recent
        midnight UTC.
    time_resolution : int, default 1
        Temporal resolution of predictions in minutes.
    time_length : float
        Number of days to forecast orbit locations.

    Returns
    -------
    DatetimeIndex
        Timestamps for groundtrack positions
    """
    if start_datetime is None:
        now = datetime.utcnow()
        start_datetime = (datetime(now.year, now.month, now.day)
                          - timedelta(minutes=time_resolution))

    # Calculate the end time based on time length
    start_datetime = pd.Timestamp(start_datetime, tz="UTC")
    end_datetime = pd.Timestamp(
        start_datetime + timedelta(days=time_length, minutes=time_resolution))

    # Generate date range from resolution and convert to a list
    return pd.date_range(start=start_datetime, end=end_datetime,
                         freq=f'{time_resolution}min')


def predict_groundtrack(tle_lines, dates, satellite_name='PACE'):
    """
    Predict satellite orbital ground track from TLE data.

    Parameters
    ----------
    tle_lines : list of str
        Two lines of TLE data.
    dates : list of DatetimeIndex
        List of dates for prediction.

    Returns
    -------
    np.ndarray
        Predicted positions [latitude, longitude] in decimal degrees.
    """
    satellite = EarthSatellite(tle_lines[0], tle_lines[1], satellite_name)
    ts = load.timescale()

    # Convert dates to skyfield times
    t = ts.from_datetimes(dates)

    # Calculate geocentric positions, then subpoints
    geocentric = satellite.at(t)
    subpoint = wgs84.subpoint_of(geocentric)

    # Extract latitudes and longitudes
    latitudes = subpoint.latitude.degrees
    longitudes = subpoint.longitude.degrees

    return np.column_stack((latitudes, longitudes))


def calc_solar_zeniths(lat, lon, date):
    """
    Calculate solar zenith angles, given data time and coordinates.

    Used for calculating day/night of position (zenith > 90 degrees).

    Parameters
    ----------
    lat : float or array-like
        Latitude(s) in degrees.
    lon : float or array-like
        Longitude(s) in degrees.
    date : datetime or array-like
        Date(s) and time(s) of the observation.

    Returns
    -------
    array
        Solar zenith angles in degrees.
    """
    solar_position = pvlib.solarposition.get_solarposition(date, lat, lon)
    return solar_position["zenith"].values


def calculate_headings(start_point, end_point):
    """
    Calculate the headings between two points using numpy.

    Parameters
    ----------
    start_point : tuple of latitude, longitude in decimal degrees
        Start point for bearing calculation.
    end_point : tuple of latitude, longitude in decimal degrees
        End point for bearing calculation.
    """
    lat1, lon1 = np.radians(start_point)
    lat2, lon2 = np.radians(end_point)

    delta_lon = lon2 - lon1
    x = np.sin(delta_lon) * np.cos(lat2)
    y = (np.cos(lat1) * np.sin(lat2)
         - (np.sin(lat1) * np.cos(lat2) * np.cos(delta_lon)))
    initial_bearing = np.arctan2(x, y)
    initial_bearing = np.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing


def calculate_perpendicular_headings(bearing):
    """
    Calculate the headings perpendicular to the given bearing.

    Parameter
    ---------
    bearing : float
        Bearing between points in decimal degrees.
    """
    bearing1 = (bearing + 90) % 360
    bearing2 = (bearing - 90 + 360) % 360
    return bearing1, bearing2


def get_midpoint_headings(tle_lines, dates):
    """Calculate midpoints and orthogonal headings for given dates.

    Calculates the midpoints using the TLE>ground_track script, then gives a
    close point for a headings calculation to return the perpendicular headings
    for footprint calculations.
    """
    midpoint_dates = dates[:-1] + (dates[1:] - dates[:-1]) / 2

    # Get small time offsets, then tile through the midpoint times
    offsets = np.array([np.timedelta64(0, 's'),
                        pd.Timedelta(milliseconds=10).to_timedelta64()])
    expanded_dates = pd.DatetimeIndex(np.repeat(midpoint_dates.values, 2)
                                      + np.tile(offsets, len(midpoint_dates)),
                                      tz="UTC")
    midpoints = predict_groundtrack(tle_lines, expanded_dates)

    # Reshape and put all pairs together as a list
    midpoints_rs = midpoints.reshape((-1, 2, 2))
    midpoint_pairs = [[tuple(subarr[0]), tuple(subarr[1])]
                      for subarr in midpoints_rs]
    headings = np.array([calculate_headings(start_point, end_point)
                         for start_point, end_point in midpoint_pairs])

    # Organize output
    midpoints = midpoints_rs[:, 0, :]
    heading_right, heading_left = calculate_perpendicular_headings(headings)
    return midpoints, heading_right, heading_left


def predict_footprint(tle_lines, dates, swath=50):
    """
    Calculate polygon corners around ground track with footprint.

    Defaults to the SPEXone swath.

    Parameters
    ----------
    tle_lines : list of str
        Two lines of TLE data.
    dates : list of DatetimeIndex
        List of dates for prediction.
    swath : int, default 50
        Viewing footprint of satellite, in kilometers.
    """
    # Get groundtrack points for middle of footprint polygons
    predicted_positions = predict_groundtrack(tle_lines, dates)

    # Get points between groundtrack positions as well as headings
    track_points, head_cw, head_ccw = get_midpoint_headings(tle_lines, dates)

    # Put together center point and boundaries
    polygon1 = []
    for idx, begin_point in enumerate(track_points[:-1]):
        # To clarify: pred_pos[idx-1] > begin_point > pred_pos[idx] > end_point
        end_point = track_points[idx + 1]
        head_cw_begin = head_cw[idx - 1]
        head_ccw_begin = head_ccw[idx - 1]
        head_cw_end = head_cw[idx]
        head_ccw_end = head_ccw[idx]

        # Calculate the boundary points
        if not hasattr(swath, '__len__'):
            dist1 = distance(kilometers=swath)
            dist2 = distance(kilometers=swath)
        else:
            dist1 = distance(kilometers=swath[0])
            dist2 = distance(kilometers=swath[1])
        
        point1 = dist1.destination(
            (begin_point[0], begin_point[1]), head_ccw_begin)
        point2 = dist2.destination(
            (begin_point[0], begin_point[1]), head_cw_begin)
        point3 = dist2.destination(
            (end_point[0], end_point[1]), head_cw_end)
        point4 = dist1.destination(
            (end_point[0], end_point[1]), head_ccw_end)

        # Append the four points as a list of tuples
        polygon1.append([
            (point1.latitude, point1.longitude),
            (point2.latitude, point2.longitude),
            (point3.latitude, point3.longitude),
            (point4.latitude, point4.longitude)
        ])
    return predicted_positions[1:-1], track_points, polygon1


def create_kml(dates, predicted_positions, track_points, boundary_points,
               filename="../static/kml/satellite_orbit.kml",poly_color='red',line_color='black'):
    """
    Create a KML document based on timestamps, groundtrack, and polygon bounds.

    TODO: Figure out the bug with crossing the Antimeridian.
    """
    # Get solar zeniths to skip nighttime data
    solar_zeniths = calc_solar_zeniths(
        predicted_positions[:, 0], predicted_positions[:, 1], dates[1:-1])

    # Open KML and set up folders
    kml = simplekml.Kml()
    multilin = kml.newmultigeometry()
    multipoly = kml.newmultigeometry()
    lolabels = kml.newfolder(name="Timepoints")

    # Set styles
    polygon_style = Style()
    polygon_style.polystyle.color = simplekml.Color.changealphaint(
        150, getattr(simplekml.Color,poly_color))
    polygon_style.linestyle.color = simplekml.Color.black
    polygon_style.linestyle.width = 1

    line_style = Style()
    line_style.linestyle.color = getattr(simplekml.Color,line_color)
    line_style.linestyle.width = 4

    point_style = Style()
    point_style.iconstyle.icon.href = ""
    point_style.iconstyle.hotspot = simplekml.HotSpot(x=50, xunits="fraction")
    point_style.labelstyle.scale = 1.5

    for idx, predicted_position in enumerate(predicted_positions):
        if solar_zeniths[idx] > 90:  # Skip nighttime
            continue

        # Add the LineString for the satellite orbit
        if abs(track_points[idx, 1] - track_points[idx+1, 1]) < 90:
            sat_line = multilin.newlinestring(
                name="Satellite Ground Track",
                coords=[np.flipud(track_points[idx]),
                        np.flipud(predicted_positions[idx]),
                        np.flipud(track_points[idx+1])])
            sat_line.style = line_style

        # Add the Polygon for the boundary box
        lons_poly = [pt[1] for pt in boundary_points[idx]]
        if max(lons_poly) - min(lons_poly) < 90:
            sat_polygon = multipoly.newpolygon(
                name="Footprint",
                outerboundaryis=([(pt[1], pt[0])
                                  for pt in boundary_points[idx]]
                                 + [(boundary_points[idx][0][1],
                                     boundary_points[idx][0][0])]))
            sat_polygon.style = polygon_style

        # Add the Point for the Sat position with datetime label
        sat_point = lolabels.newpoint(
            name=dates[idx+1].strftime('%Y-%m-%d %H:%M:%S') + ' UTC',
            coords=[(predicted_position[1], predicted_position[0])])
        sat_point.style = point_style

    kml.save(filename)


def main(satellite="EARTHCARE", num_days=1,start_date=[2024,7,22],number_of_loops=70,path='./'):
    """Primary driver for standalone version."""
    # Fetch latest TLE for PACE
    tle_lines = fetch_latest_tle(sat=satellite)

    # Generate dates for prediction (every 1 minutes for the next 3 days)
    for i in range(number_of_loops):
        dt = datetime(start_date[0],start_date[1],start_date[2])+timedelta(days=i)
        dates = build_timestamps(start_datetime=dt,
                                 time_resolution=1,
                                 time_length=num_days)

        # Calculate the satellite positions and footprint points
        predicted_positions, track_points, boundary_points = predict_footprint(
            tle_lines, dates, swath=satToSwath[satellite])

        # Create the KML file
        create_kml(dates, predicted_positions, track_points, boundary_points,
                   "{path}{satellite}_{y:04}{m:02}{d:02}.kml".format(satellite=satellite,y=dt.year,m=dt.month,d=dt.day,path=path),
                   poly_color=satToColor[satellite]['poly'],line_color=satToColor[satellite]['line'])
        print("Making kml file for: {path}{satellite}_{y:04}{m:02}{d:02}.kml".format(satellite=satellite,y=dt.year,m=dt.month,d=dt.day,path=path))

def automated(path='./'):
    """Version for automated running and generation for PACE and EARTHCARE"""
    date = [datetime.now().year,datetime.now().month,datetime.now().day]
    main(satellite="PACE",start_date=date,number_of_loops=5,num_days=1,path=path)
    main(satellite="EARTHCARE",start_date=date,number_of_loops=5,num_days=1,path=path)
    

if __name__ == "__main__":
    main()
