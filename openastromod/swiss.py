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
import os.path, sys, datetime
#swiss ephemeris files directory
swissDir = '/usr/share/swisseph:/usr/local/share/swisseph'
#local swiss ephemeris files directory
home=os.path.expanduser("~")
oa=os.path.join(home, '.openastro.org')
swissLocalDir=os.path.join(oa, 'swiss_ephemeris')

#swiss ephemeris path
ephe_path=swissDir+':'+swissLocalDir

import swisseph as swe

class ephData:
	def __init__(self,year,month,day,hour,geolon,geolat,altitude,planets,zodiac,openastrocfg,houses_override=None):
		#ephemeris path (default "/usr/share/swisseph:/usr/local/share/swisseph")
		swe.set_ephe_path(ephe_path)
		
		#basic location		
		self.jul_day_UT=swe.julday(year,month,day,hour)
		self.geo_loc = swe.set_topo(geolon,geolat,altitude)

		#output variables
		self.planets_sign = range(len(planets))
		self.planets_degree = range(len(planets))
		self.planets_degree_ut = range(len(planets))
		self.planets_info_string = range(len(planets))
		self.planets_retrograde = range(len(planets))
		
		#iflag
		"""
		#define SEFLG_JPLEPH         1L     // use JPL ephemeris
		#define SEFLG_SWIEPH         2L     // use SWISSEPH ephemeris, default
		#define SEFLG_MOSEPH         4L     // use Moshier ephemeris
		#define SEFLG_HELCTR         8L     // return heliocentric position
		#define SEFLG_TRUEPOS        16L     // return true positions, not apparent
		#define SEFLG_J2000          32L     // no precession, i.e. give J2000 equinox
		#define SEFLG_NONUT          64L     // no nutation, i.e. mean equinox of date
		#define SEFLG_SPEED3         128L     // speed from 3 positions (do not use it, SEFLG_SPEED is // faster and preciser.)
		#define SEFLG_SPEED          256L     // high precision speed (analyt. comp.)
		#define SEFLG_NOGDEFL        512L     // turn off gravitational deflection
		#define SEFLG_NOABERR        1024L     // turn off 'annual' aberration of light
		#define SEFLG_EQUATORIAL     2048L     // equatorial positions are wanted
		#define SEFLG_XYZ            4096L     // cartesian, not polar, coordinates
		#define SEFLG_RADIANS        8192L     // coordinates in radians, not degrees
		#define SEFLG_BARYCTR        16384L     // barycentric positions
		#define SEFLG_TOPOCTR      (32*1024L)     // topocentric positions
		#define SEFLG_SIDEREAL     (64*1024L)     // sidereal positions 		
		"""
		#check for apparent geocentric (default), true geocentric, topocentric or heliocentric
		iflag=swe.FLG_SWIEPH+swe.FLG_SPEED
		if(openastrocfg['postype']=="truegeo"):
			iflag += swe.FLG_TRUEPOS
		elif(openastrocfg['postype']=="topo"):
			iflag += swe.FLG_TOPOCTR
		elif(openastrocfg['postype']=="helio"):
			iflag += swe.FLG_HELCTR

		#sidereal
		if(openastrocfg['zodiactype']=="sidereal"):
			iflag += swe.FLG_SIDEREAL
			mode="SIDM_"+openastrocfg['siderealmode']
			swe.set_sid_mode(getattr(swe,mode.encode("ascii")))

		#compute a planet (longitude,latitude,distance,long.speed,lat.speed,speed)
		for i in range(23):
			ret_flag = swe.calc_ut(self.jul_day_UT,i,iflag)
			for x in range(len(zodiac)):
				deg_low=float(x*30)
				deg_high=float((x+1)*30)
				if ret_flag[0] >= deg_low:
					if ret_flag[0] <= deg_high:
						self.planets_sign[i]=x
						self.planets_degree[i] = ret_flag[0] - deg_low
						self.planets_degree_ut[i] = ret_flag[0]
						#if latitude speed is negative, there is retrograde
						if ret_flag[3] < 0:						
							self.planets_retrograde[i] = True
						else:
							self.planets_retrograde[i] = False

							
		#available house systems:
		"""
		hsys= ‘P’     Placidus
				‘K’     Koch
				‘O’     Porphyrius
				‘R’     Regiomontanus
				‘C’     Campanus
				‘A’ or ‘E’     Equal (cusp 1 is Ascendant)
				‘V’     Vehlow equal (Asc. in middle of house 1)
				‘X’     axial rotation system
				‘H’     azimuthal or horizontal system
				‘T’     Polich/Page (“topocentric” system)
				‘B’     Alcabitus
				‘G’     Gauquelin sectors
				‘M’     Morinus
		"""
		#houses calculation (hsys=P for Placidus)
		#check for polar circle latitude < -66 > 66
		if houses_override:
			self.jul_day_UT = swe.julday(houses_override[0],houses_override[1],houses_override[2],houses_override[3])
			
		if geolat > 66.0:
			geolat = 66.0
			print "polar circle override for houses, using 66 degrees"
		elif geolat < -66.0:
			geolat = -66.0
			print "polar circle override for houses, using -66 degrees"
		#sidereal houses
		if(openastrocfg['zodiactype']=="sidereal"):
			sh = swe.houses_ex(self.jul_day_UT,geolat,geolon,openastrocfg['houses_system'].encode("ascii"),swe.FLG_SIDEREAL)
		else:
			sh = swe.houses(self.jul_day_UT,geolat,geolon,openastrocfg['houses_system'].encode("ascii"))
		self.houses_degree_ut = list(sh[0])
		self.houses_degree = range(len(self.houses_degree_ut))
		self.houses_sign = range(len(self.houses_degree_ut))
		for i in range(12):
			for x in range(len(zodiac)):
				deg_low=float(x*30)
				deg_high=float((x+1)*30)
				if self.houses_degree_ut[i] >= deg_low:
					if self.houses_degree_ut[i] <= deg_high:
						self.houses_sign[i]=x
						self.houses_degree[i] = self.houses_degree_ut[i] - deg_low
		



		#compute additional points and angles
		#list index 23 is asc, 24 is Mc, 25 is Dsc, 26 is Ic
		self.planets_degree_ut[23] = self.houses_degree_ut[0]
		self.planets_degree_ut[24] = self.houses_degree_ut[9]
		self.planets_degree_ut[25] = self.houses_degree_ut[6]
		self.planets_degree_ut[26] = self.houses_degree_ut[3]	
		#arabic parts
		sun,moon,asc = self.planets_degree_ut[0],self.planets_degree_ut[1],self.planets_degree_ut[23]
		dsc,venus = self.planets_degree_ut[25],self.planets_degree_ut[3]			
		#list index 27 is day pars
		self.planets_degree_ut[27] = asc + (moon - sun)
		#list index 28 is night pars
		self.planets_degree_ut[28] = asc + (sun - moon)
		#list index 29 is South Node
		self.planets_degree_ut[29] = self.planets_degree_ut[10] - 180.0
		#list index 30 is marriage pars
		self.planets_degree_ut[30] = (asc+dsc)-venus
		#if planet degrees is greater than 360 substract 360 or below 0 add 360
		for i in range(23,31):
			if self.planets_degree_ut[i] > 360.0:
				self.planets_degree_ut[i] = self.planets_degree_ut[i] - 360.0
			elif self.planets_degree_ut[i] < 0.0:
				self.planets_degree_ut[i] = self.planets_degree_ut[i] + 360.0
			#get zodiac sign
			for x in range(12):
				deg_low=float(x*30.0)
				deg_high=float((x+1.0)*30.0)
				if self.planets_degree_ut[i] >= deg_low:
					if self.planets_degree_ut[i] <= deg_high:
						self.planets_sign[i]=x
						self.planets_degree[i] = self.planets_degree_ut[i] - deg_low
						self.planets_retrograde[i] = False

		
		
		#close swiss ephemeris
		swe.close()

def years_diff(y1, m1, d1, h1 , y2, m2, d2, h2):
		swe.set_ephe_path(ephe_path)
		jd1 = swe.julday(y1,m1,d1,h1)
		jd2 = swe.julday(y2,m2,d2,h2)
		jd = jd1 + swe._years_diff(jd1, jd2)
		#jd = jd1 + ( (jd2-jd1) / 365.248193724 )
		y, mth, d, h, m, s = swe._revjul(jd, swe.GREG_CAL)
		return datetime.datetime(y,mth,d,h,m,s)
