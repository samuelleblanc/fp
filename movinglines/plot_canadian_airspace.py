
# KML namespaces (covers common variants)
NS = {
    "kml": "http://www.opengis.net/kml/2.2",
    "gx":  "http://www.google.com/kml/ext/2.2",
}

def _coords_to_lonlat(text):
    """Parse a <coordinates> string into a closed list of (lon, lat)."""
    if not text:
        return []
    pts = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            lon = float(parts[0]); lat = float(parts[1])
            pts.append((lon, lat))
    # close ring if needed
    if len(pts) >= 2 and pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts

def _polygon_from_elem(poly_elem):
    """Build a Shapely Polygon from a <Polygon> element (outer + holes)."""
    from shapely.geometry import Polygon
    outer_el = poly_elem.find(".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
    if outer_el is None:
        return None
    outer = _coords_to_lonlat(outer_el.text)
    if len(outer) < 4:
        return None  # need at least 3 distinct points + closure
    holes = []
    for hole_el in poly_elem.findall(".//kml:innerBoundaryIs/kml:LinearRing/kml:coordinates", NS):
        ring = _coords_to_lonlat(hole_el.text)
        if len(ring) >= 4:
            holes.append(ring)
    try:
        return Polygon(outer, holes=holes if holes else None)
    except Exception:
        # invalid/self-intersecting -> try to “fix”
        try:
            return Polygon(outer).buffer(0)
        except Exception:
            return None

def _geoms_under(elem):
    """Yield Shapely Polygon/MultiPolygon for Polygons and MultiGeometries under elem."""
    from shapely.geometry import Polygon, MultiPolygon
    # Plain polygons
    for p in elem.findall(".//kml:Polygon", NS):
        g = _polygon_from_elem(p)
        if g and not g.is_empty:
            yield g
    # MultiGeometry: collect its polygons as a MultiPolygon
    for mg in elem.findall(".//kml:MultiGeometry", NS):
        polys = []
        for p in mg.findall(".//kml:Polygon", NS):
            g = _polygon_from_elem(p)
            if g and not g.is_empty:
                polys.append(g)
        if polys:
            yield MultiPolygon(polys) if len(polys) > 1 else polys[0]

def load_kml_from_string(kml_content, return_names=True, dissolve_per_placemark=False):
    """
    Parse a KML string into a list of (name, geometry) pairs (Shapely).
    If return_names=False, returns just geometries.
    If dissolve_per_placemark=True, unary-union polygons per placemark.
    """
    # handle bytes/str
    from shapely.ops import unary_union
    import xml.etree.ElementTree as ET

    root = ET.fromstring(kml_content if isinstance(kml_content, (str, bytes)) else str(kml_content))

    results = []
    # Iterate placemarks to keep names/attributes aligned
    for pm in root.findall(".//kml:Placemark", NS):
        name_el = pm.find("./kml:name", NS)
        name = name_el.text.strip() if (name_el is not None and name_el.text) else None

        geoms = list(_gems for _gems in _geoms_under(pm))
        if not geoms:
            continue

        if dissolve_per_placemark and len(geoms) > 1:
            geom = unary_union(geoms)
            geoms = [geom]

        for g in geoms:
            results.append((name, g) if return_names else g)

    # Fallback: if no placemarks, gather any polygons in the doc
    if not results:
        geoms = list(_geoms_under(root))
        if return_names:
            results = [(None, g) for g in geoms]
        else:
            results = geoms
    return results
	
def plot_filled_kml(kml_file, ax,color='tab:pink',addlabels=False):
    'function to plot the insides of the kml file'
    import zipfile
    import os
    from cartopy.feature import ShapelyFeature
    import cartopy.crs as ccrs
    
    print('...opening KML/KMZ: {}'.format(os.path.abspath(kml_file)))
    
    # Extract the contents of KMZ file if provided
    if kml_file.endswith('.kmz'):
        with zipfile.ZipFile(kml_file, 'r') as zfile:
            # Find all KML files within the KMZ archive
            kml_files = [f for f in zfile.namelist() if f.lower().endswith('.kml')]
            if not kml_files:
                raise ValueError('No KML file found in the KMZ archive.')
            # Loop through each KML file
            for kml_file in kml_files:
                with zfile.open(kml_file) as kfile:
                    kml_content = kfile.read()
    else:
        with open(kml_file, 'r') as kfile:
            kml_content = kfile.read()
            
    pairs = load_kml_from_string(kml_content, return_names=True, dissolve_per_placemark=False)
    print(f'... Plotting {len(pairs)} from KML')
    
    plots = []
    labels = []
    for name, geom in pairs:
        if not any(v in name for v in ['CYR','CYD']): #only plot danger and restricted, not the advisory
            continue
        feat = ShapelyFeature([geom], ccrs.PlateCarree(),
                              facecolor=color, edgecolor=color,alpha=0.2, lw=1.5)
        pl_tm = ax.add_feature(feat, zorder=5)
        plots.append(pl_tm)
        if addlabels:
            if name and geom.geom_type in ("Polygon", "MultiPolygon"):
                c = geom.representative_point()
                tx_tm = ax.text(c.x, c.y, name, transform=ccrs.PlateCarree(), fontsize=8,color=color,alpha=0.2)
            labels.append(tx_tm)
    
    return plots+labels
