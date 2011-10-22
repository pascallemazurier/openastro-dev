#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This file is part of openastro.org.

    OpenAstro.org is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenAstro.org is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OpenAstro.org.  If not, see <http://www.gnu.org/licenses/>.
"""
import os.path, sys
#swiss ephemeris files directory
swissDir = '/usr/share/swisseph:/usr/local/share/swisseph'
#local swiss ephemeris files directory
home=os.path.expanduser("~")
oa=os.path.join(home, '.openastro.org')
swissLocalDir=os.path.join(oa, 'swiss_ephemeris')

#swiss ephemeris path
ephe_path=swissDir+':'+swissLocalDir

import swisseph as swe

__all__ = [ "getdignities" ]

def getdignities(lon, isday, terms):
    '''
    Gets a list of essential dignities and debilities

    It requires a longitude position, a boolean flag indicating
    whether this is for a daytime position, and a string indicating
    which terms to use (either "ETERMS" or "PTERMS" for Egyptian
    terms or Ptolemy terms respectively).

    usage:
        digs = getdignities( sunpos, isday, whichterms)

    returns a tuple containing 9 values which are as follows:
        ruler
        exaltation
        triplicity ruler 1  (day ruler if day chart, night ruler otherwise)
        triplicity ruler 2  (night ruler if day chart, day ruler otherwise)
        triplicity participating ruler
        terms
        decan
        detriment
        fall

    example:   dig = getdignities( 234.27, False, "ETERMS")
    '''

    temp = 0
    pos = list()
    rul = list()

    # egyptian terms
    eterms = (
        ((0,5,swe.JUPITER), (6,11,swe.VENUS), (12, 19, swe.MERCURY),
            (20,24,swe.MARS), (25,29,swe.SATURN)),
        ((0,7,swe.VENUS), (8,13,swe.MERCURY), (14,21,swe.JUPITER),
            (22,26,swe.SATURN), (27,29,swe.MARS)),
        ((0,5,swe.MERCURY), (6,11,swe.JUPITER), (12,16,swe.VENUS),
            (17,23,swe.MARS), (24,29,swe.SATURN)),
        ((0,6,swe.MARS), (7,12,swe.VENUS), (13,18,swe.MERCURY),
            (19,25,swe.JUPITER), (26,29,swe.SATURN)),
        ((0,5,swe.JUPITER), (6,10,swe.VENUS), (11,17,swe.SATURN),
            (18,23,swe.MERCURY), (24,29,swe.MARS)),
        ((0,6,swe.MERCURY), (7,16,swe.VENUS), (17,20,swe.JUPITER),
            (21,27,swe.MARS), (28,29,swe.SATURN)),
        ((0,5,swe.SATURN), (6,13,swe.MERCURY), (14,20,swe.JUPITER),
            (21,27,swe.VENUS), (28,29,swe.MARS)),
        ((0,6,swe.MARS), (7,10,swe.VENUS), (11,18,swe.MERCURY),
            (19,23,swe.JUPITER), (24,29,swe.SATURN)),
        ((0,11,swe.JUPITER), (12,16,swe.VENUS), (17,20,swe.MERCURY),
            (21,25,swe.SATURN), (26,29,swe.MARS)),
        ((0,6,swe.MERCURY), (7,13,swe.JUPITER), (14,21,swe.VENUS),
            (22,25,swe.SATURN), (26,29,swe.MARS)),
        ((0,6,swe.MERCURY), (7,12,swe.VENUS), (13,19,swe.JUPITER),
            (20,24,swe.MARS), (25,29,swe.SATURN)),
        ((0,11,swe.VENUS), (12,15,swe.JUPITER), (16,18,swe.MERCURY),
            (19,27,swe.MARS), (28,29,swe.SATURN)) )

    # ptolemy terms
    pterms = (
        ((0,5,swe.JUPITER), (6,13, swe.VENUS), (14,20,swe.MERCURY),
            (21,25,swe.MARS), (26,29,swe.SATURN)),
        ((0,7,swe.VENUS), (8,14,swe.MERCURY), (15,21,swe.JUPITER),
            (22,23,swe.SATURN), (24,29,swe.MARS)),
        ((0,6,swe.MERCURY), (7,12,swe.JUPITER), (13,19,swe.VENUS),
            (20,25,swe.MARS), (26,29,swe.SATURN)),
        ((0,5,swe.MARS), (6,12,swe.JUPITER), (13,19,swe.MERCURY),
            (20,26,swe.VENUS), (27,29,swe.SATURN)),
        ((0,5,swe.JUPITER), (6,12,swe.MERCURY), (13,18,swe.SATURN),
            (19,24,swe.VENUS), (25,29,swe.MARS)),
        ((0,6,swe.MERCURY), (6,12,swe.VENUS), (13,17,swe.JUPITER),
            (18,23,swe.SATURN), (24,29,swe.MARS)),
        ((0,5,swe.SATURN), (6,10,swe.VENUS), (11,15,swe.MERCURY),
            (16,23,swe.JUPITER), (24,29,swe.MARS)),
        ((0,5,swe.MARS), (6,12,swe.VENUS), (13,20,swe.JUPITER),
            (21,26,swe.MERCURY), (27,29,swe.SATURN)),
        ((0,7,swe.JUPITER), (8,13,swe.VENUS), (14,18,swe.MERCURY),
            (19,24,swe.SATURN), (25,29,swe.MARS)),
        ((0,5,swe.VENUS), (6,11,swe.MERCURY), (12,18,swe.JUPITER),
            (19,24,swe.SATURN), (25,29,swe.MARS)),
        ((0,5,swe.SATURN), (6,11,swe.MERCURY), (12,19,swe.VENUS),
            (20,24,swe.JUPITER), (25,29,swe.MARS)),
        ((0,7,swe.VENUS), (8,13,swe.JUPITER), (14,19,swe.MERCURY),
            (20,24,swe.MARS), (25,29,swe.SATURN)) )


    ### convert longitude to sign, degree, minute, second
    # sign
    pos.append(int(lon / 30))
    # degree
    pos.append(int(lon - (pos[0] * 30)))
    # minute
    pos.append(int((lon - ((pos[0] * 30) + pos[1])) * 60))
    # second
    pos.append(
        int((lon - ((pos[0] * 30) + pos[1] + (pos[2]/60.0))) * 3600))

    ### get ruler
    rul.append([swe.MARS, swe.VENUS, swe.MERCURY,
        swe.MOON, swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS,
        swe.JUPITER, swe.SATURN, swe.SATURN, swe.JUPITER][pos[0]])

    ### get exaltation
    rul.append([swe.SUN, swe.MOON, -1, swe.JUPITER, -1, swe.MERCURY,
    swe.SATURN, -1, -1, swe.MARS, -1, swe.VENUS][pos[0]])

    ### get triplicity rulers
    temp = list()
    # get day
    temp.append([swe.SUN, swe.VENUS, swe.SATURN, swe.VENUS,
        swe.SUN, swe.VENUS, swe.SATURN, swe.VENUS, swe.SUN,
        swe.VENUS, swe.SATURN, swe.VENUS][pos[0]])
    # get night
    temp.append([swe.JUPITER, swe.MOON, swe.MERCURY, swe.MARS,
        swe.JUPITER, swe.MOON, swe.MERCURY, swe.MARS, swe.JUPITER,
        swe.MOON, swe.MERCURY, swe.MARS][pos[0]])
    # get participating
    temp.append([swe.SATURN, swe.MARS, swe.JUPITER, swe.MOON,
        swe.SATURN, swe.MARS, swe.JUPITER, swe.MOON, swe.SATURN,
        swe.MARS, swe.JUPITER, swe.MOON][pos[0]])
    # add triplicities
    if isday:
        rul.append(temp[0])
        rul.append(temp[1])
    else:
        rul.append(temp[1])
        rul.append(temp[0])
    rul.append(temp[2])

    ### get terms... defaults to ptolemy if eterms not specified
    if terms == "termse":
        for i in eterms[pos[0]]:
            if i[0] <= pos[1] <= i[1]:
                rul.append(i[2])
                break
    else:
        for i in pterms[pos[0]]:
            if i[0] <= pos[1] <= i[1]:
                rul.append(i[2])
                break

    ### get decan
    rul.append([(swe.MARS, swe.SUN, swe.VENUS),
        (swe.MERCURY, swe.MOON, swe.SATURN),
        (swe.JUPITER, swe.MARS, swe.SUN),
        (swe.VENUS, swe.MERCURY, swe.MOON),
        (swe.SATURN, swe.JUPITER, swe.MARS),
        (swe.SUN, swe.VENUS, swe.MERCURY),
        (swe.MOON, swe.SATURN, swe.JUPITER),
        (swe.MARS, swe.SUN, swe.VENUS),
        (swe.MERCURY, swe.MOON, swe.SATURN),
        (swe.JUPITER, swe.MARS, swe.SUN),
        (swe.VENUS, swe.MERCURY, swe.MOON),
        (swe.SATURN, swe.JUPITER, swe.MARS)][pos[0]][int(pos[1] / 10)])

    ### get detriment
    rul.append([swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN,
        swe.SATURN, swe.JUPITER, swe.MARS, swe.VENUS, swe.MERCURY,
        swe.MOON, swe.SUN, swe.MERCURY][pos[0]])

    ### get fall
    rul.append([swe.SATURN, -1, -1, swe.MARS, -1, swe.VENUS,
        swe.SUN, swe.MOON, -1, swe.JUPITER, -1, swe.MERCURY][pos[0]])

    # return a tuple of dignities
    return tuple(rul)