#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" convert lat/long to timezone, offset using the zoneinfo database

see http://www.twinsun.com/tz/tz-link.htm ,
    http://en.wikipedia.org/wiki/Zoneinfo
"""

import re, struct, math
from datetime import datetime
from dateutil.tz import tzfile

def nearest_tz(lat, lon, zones):
    """
    >>> nearest_tz(39.2975, -94.7139, timezones())[2]
    'America/Indiana/Vincennes'
    
    >>> nearest_tz(39.2975, -94.7139, timezones(exclude=["Indiana"]))[2]
    'America/Chicago'
    
    """
    def d(tzrec):
        return distance(lat, lon, tzrec[1][0], tzrec[1][1])
    return optimize(zones, d)

def optimize(seq, metric):
    best = None
    m = None

    for candidate in seq:
        x = metric(candidate)
        if best is None or x < m:
            m = x
            best = candidate
    return best

def distance(lat_1, long_1, lat_2, long_2):
    # thanks http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/393241
    # Submitter: Kevin Ryan (other recipes)
    # Last Updated: 2006/04/25 
    lat_1, long_1, lat_2, long_2 = [ v * math.pi / 180.0
                                     for v in lat_1, long_1, lat_2, long_2]
    dlong = long_2 - long_1
    dlat = lat_2 - lat_1
    a = (math.sin(dlat / 2))**2 + math.cos(lat_1) * math.cos(lat_2) \
        * (math.sin(dlong / 2))**2
    return 2 * math.asin(min(1, math.sqrt(a)))
        
def timezones(zonetab="/usr/share/zoneinfo/zone.tab",
              exclude=[]):
    """iterate over timezones in zone.tab; yield (country, (lat, lon), name)

    @param zonetab: filename of zone.tab file
    @param exclude: exclude timezones with these strings in the name,
                    e.g. convexity exceptions like Indiana
    """
    for line in file(zonetab):
        if line.startswith("#"): continue
        values = line.split()
        if len(values) >= 3:
            country, coords, tz = values[:3]
            for s in exclude:
                if s in tz:
                    break
            else:
                yield country, latlong(coords), tz


def stdtime(tz, year, month, day, hour, min, sec ,
	    zoneinfo="/usr/share/zoneinfo"
	    ):
    """Use /usr/share/zoneinfo to interpret a time in a timezone.
    
    >>> stdtime("America/Chicago", "2007-04-02T21:53:27")
    '2007-04-02T21:53:27-05:00'
    """
    return datetime(year, month, day, hour, min, sec,
                    tzinfo=tzfile("%s/%s" % (zoneinfo, tz))
                    )
    


def latlong(coords):
    """decode ISO 6709. ugh.
    
    >>> latlong("-1247+04514")
    (-12.783333333333333, 45.233333333333334)

    >>> latlong("-690022+0393524")
    (-69.00611111111111, 39.590000000000003)
    """
    m = re.search(r'([^\d])(\d+)([^\d])(\d+)', coords)
    if not m:
        raise ValueError, coords
    return coord(m.group(1), m.group(2)), coord(m.group(3), m.group(4))

def coord(sign, digits):
    """
    >>> coord("-", "1247")
    -12.783333333333333
    >>> coord("+", "04514")
    45.233333333333334
    >>> coord("-", "690022")
    -69.00611111111111
    >>> coord("+", "0393524")
    39.590000000000003
    """

    if len(digits) == 4:
        d, m, s = int(digits[:2]), int(digits[2:]), 0
    elif len(digits) == 5:
        d, m, s = int(digits[:3]), int(digits[3:]), 0
    elif len(digits) == 6:
        d, m, s = int(digits[:2]), int(digits[2:4]), int(digits[4:])
    elif len(digits) == 7:
        d, m, s = int(digits[:3]), int(digits[3:5]), int(digits[5:])
    else:
        raise RuntimeError, "not implemented", digits

    if sign == '+': kludge = 'N'
    else: kludge = 'S'

    return dms(kludge, d, m, s)

def dms(o, d, m, s):
    """
    >>> abs(dms(u'N', 30, 11, u'40.3') - 30.194527777777779) <.001
    True
    """
    return (o in ('N', 'E') and 1 or -1) * (d + \
	(m + float(s)/60)/60)
