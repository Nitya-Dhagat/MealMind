# src/utils.py
from datetime import datetime
import numpy as np

# time slot mapping (hour ranges; end exclusive)
TIME_SLOTS = {
    'breakfast': (4, 10),   # 04:00 - 09:59
    'lunch': (10, 15),      # 10:00 - 14:59
    'evening': (15, 20),    # 15:00 - 19:59
    'night': (20, 4)        # 20:00 - 03:59 (wraps midnight)
}

def parse_time_to_slot(timestr: str) -> str:
    """
    Parse a time string `HH:MM` or `HH:MM:SS` into a time slot.
    Returns one of: 'breakfast','lunch','evening','night' or 'unknown'.
    """
    if not isinstance(timestr, str):
        return 'unknown'
    timestr = timestr.strip()
    if timestr == '' or timestr.lower() in ['nan', 'none']:
        return 'unknown'
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(timestr, fmt).time()
            hour = t.hour
            for slot, (start, end) in TIME_SLOTS.items():
                if start <= end:
                    if start <= hour < end:
                        return slot
                else:  # wraps midnight (e.g., 20 -> 4)
                    if hour >= start or hour < end:
                        return slot
            return 'unknown'
        except ValueError:
            continue
    return 'unknown'

def haversine_km(lat1, lon1, lat2, lon2):
    """
    Haversine distance in kilometers between two points or arrays.
    Accepts scalars or numpy arrays.
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    earth_radius_km = 6371.0088
    return earth_radius_km * c
