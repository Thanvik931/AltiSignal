"""
H3 utility functions supporting both h3-py v3 and v4 APIs.
"""
import h3


def latlng_to_cell(lat: float, lng: float, res: int = 8) -> str:
    """
    Convert (latitude, longitude) coordinates to an H3 hex cell index string.
    """
    if hasattr(h3, "latlng_to_cell"):
        return str(h3.latlng_to_cell(lat, lng, res))
    elif hasattr(h3, "geo_to_h3"):
        return str(h3.geo_to_h3(lat, lng, res))
    raise AttributeError("h3 module does not have latlng_to_cell or geo_to_h3")


def cell_to_latlng(cell: str) -> tuple[float, float]:
    """
    Convert an H3 hex cell index string to a (latitude, longitude) tuple of floats.
    """
    if hasattr(h3, "cell_to_latlng"):
        coords = h3.cell_to_latlng(cell)
        return float(coords[0]), float(coords[1])
    elif hasattr(h3, "h3_to_geo"):
        coords = h3.h3_to_geo(cell)
        return float(coords[0]), float(coords[1])
    raise AttributeError("h3 module does not have cell_to_latlng or h3_to_geo")
