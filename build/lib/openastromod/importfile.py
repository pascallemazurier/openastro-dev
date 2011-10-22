#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    This file is part of openastro.org.

    OpenAstro.org is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Foobar is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OpenAstro.org.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import with_statement

from xml.dom.minidom import parseString

from codecs import EncodedFile

def _getText(nodelist):
	"""Internal function to return text from nodes
	"""
	rc = ""
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc = rc + node.data
	return rc

def getOAC(filename):
	f=open(filename)	
	dom = parseString(f.read())
	f.close()
	
	valid=['name','datetime','location','altitude','latitude','longitude','countrycode',
			'timezone','geonameid','extra']
	output=[]
	for a in dom.getElementsByTagName("openastrochart"):
		output.append({})
		for i in range(len(valid)):
			output[-1][valid[i]]=_getText(a.getElementsByTagName(valid[i])[0].childNodes)
			
	#close dom
	dom.unlink()
	#return results
	return output

def getOroboros(filename):
	f=open(filename)
	dom = parseString(f.read())
	f.close()
	output=[]
	for a in dom.getElementsByTagName("ASTROLOGY"):
		output.append({})
		output[-1]['name']=_getText(a.getElementsByTagName('NAME')[0].childNodes)
		output[-1]['datetime']=_getText(a.getElementsByTagName('DATETIME')[0].childNodes)
		output[-1]['location']=_getText(a.getElementsByTagName('LOCATION')[0].childNodes)
		output[-1]['altitude']=a.getElementsByTagName('LOCATION')[0].attributes['altitude'].value
		output[-1]['latitude']=a.getElementsByTagName('LOCATION')[0].attributes['latitude'].value
		output[-1]['longitude']=a.getElementsByTagName('LOCATION')[0].attributes['longitude'].value
		output[-1]['countryname']=_getText(a.getElementsByTagName('COUNTRY')[0].childNodes)
		output[-1]['zoneinfo']=a.getElementsByTagName('COUNTRY')[0].attributes['zoneinfo'].value
	dom.unlink()
	return output

def getSkylendar(filename):
	f=open(filename)
	dom = parseString(f.read())
	f.close()
	output=[]
	for a in dom.getElementsByTagName("DATASET"):
		output.append({})
		output[-1]['name']=_getText(a.getElementsByTagName('NAME')[0].childNodes)
		output[-1]['year']=a.getElementsByTagName('DATE')[0].attributes['Year'].value
		output[-1]['month']=a.getElementsByTagName('DATE')[0].attributes['Month'].value
		output[-1]['day']=a.getElementsByTagName('DATE')[0].attributes['Day'].value
		
		tz=a.getElementsByTagName('DATE')[0].attributes['Timezone'].value.split(':')
		if float(tz[0]) < 0:
			output[-1]['timezone']=float(tz[0])+(float(tz[1]/60.0)/-1)
		else:
			output[-1]['timezone']=float(tz[0])+float(tz[1]/60.0)

		output[-1]['daylight']=a.getElementsByTagName('DATE')[0].attributes['Daylight'].value
		hm=a.getElementsByTagName('DATE')[0].attributes['Hm'].value
		output[-1]['hour']=hm.split(':')[0]
		output[-1]['minute']=hm.split(':')[1]
		output[-1]['location']=_getText(a.getElementsByTagName('PLACE')[0].childNodes)
		
		lat=a.getElementsByTagName('PLACE')[0].attributes['Latitude'].value.split(':')
		if float(lat[0]) < 0:
			output[-1]['latitude'] = float(lat[0])+(float(lat[1]/60.0)/-1)
		else:
			output[-1]['latitude'] = float(lat[0])+float(lat[1]/60.0)
			
		lon=a.getElementsByTagName('PLACE')[0].attributes['Longitude'].value.split(':')
		if float(lon[0]) < 0:
			output[-1]['longitude'] = float(lon[0])+(float(lon[1]/60.0)/-1)
		else:
			output[-1]['longitude'] = float(lon[0])+float(lon[1]/60.0)
					
		output[-1]['zoneinfofile']=a.getElementsByTagName('COUNTRY')[0].attributes['ZoneInfoFile'].value
		output[-1]['countryname']=_getText(a.getElementsByTagName('COUNTRY')[0].childNodes)
		
		dom.unlink()
	return output
	
def getAstrolog32(filename):
	"""
	examples:
@0102  ; Astrolog chart info.
/qb 6 23 1972  3:00:00 ST -1:00   5:24:00E 43:18:00N
/zi "Zinedine Zidane" "Marseille"	
@0102  ; Astrolog32 chart info.

; Date is in American format: month day year.

/qb 10 27 1980 10:20:00 ST -1:00  14:39'00E 50:11'00N
/zi "Honzik" "Brandys nad Labem"	
	"""
	d={}
	h=open(filename)
	f=EncodedFile(h,"utf-8","latin-1")
	for line in f.readlines():
		if line[0:3] == "/qb":
			s0=line.strip().split(' ')
			s=[]
			for j in range(len(s0)):
				if s0[j]!='':
					s.append(s0[j])
			d['month']=s[1]
			d['day']=s[2]
			d['year']=s[3]
			d['hour'],d['minute'],d['second']=0,0,0
			for x in range(len(s[4].split(':'))):
				if x == 0:
					d['hour'] = s[4].split(':')[0]
				if x == 1:
					d['minute'] = s[4].split(':')[1]
				if x == 2:
					d['second'] = s[4].split(':')[2]

			#timezone
			tz=s[6].split(':')
			d['timezone']=float(tz[0])+float(tz[1])/60.0
			if float(tz[0]) < 0:
				d['timezone']=d['timezone']/-1.0
			#longitude
			lon=s[7].split(':')
			lon.append(lon[-1][-1])
			lon[-2]=lon[-2][0:2]
			d['longitude']=float(lon[0])+(float(lon[1])/60.0)
			if len(lon) > 3:
				d['longitude']+=float(lon[2])/3600.0
			if lon[-1] == 'W':
				d['longitude'] = d['longitude']/-1.0
			#latitude
			lon=s[8].split(':')
			lon.append(lon[-1][-1])
			lon[-2]=lon[-2][0:2]
			d['latitude']=float(lon[0])+(float(lon[1])/60.0)
			if len(lon) > 3:
				d['latitude']+=float(lon[2])/3600.0
			if lon[-1] == 'S':
				d['latitude'] = d['latitude']/-1.0			
			
		if line[0:3] == "/zi":
			s0=line.strip().split('"')
			s=[]
			for j in range(len(s0)):
				if s0[j] != '' and s0[j] != ' ':
					s.append(s0[j])
			d['name']=s[1]
			d['location']=s[2]
	f.close()
	return [d]

