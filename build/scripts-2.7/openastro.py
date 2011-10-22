#!/usr/bin/python2
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

#basics
import math, sys, os.path, datetime, socket, gettext, codecs, webbrowser

#copyfile
from shutil import copyfile

#pysqlite
import sqlite3
sqlite3.dbapi2.register_adapter(str, lambda s:s.decode('utf-8'))

#template processing
from string import Template

#minidom parser
from xml.dom.minidom import parseString

#GTK, cairo to display svg
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import rsvg

#internal openastro modules
from openastromod import zonetab, geoname, importfile, dignities, timeoutsocket, swiss as ephemeris

#debug
LOCAL=False
DEBUG=False
VERSION='1.1.24'

#directories
DATADIR=os.path.join(sys.prefix,'share','openastro.org')
TMPDIR='/tmp'

#Translations
LANGUAGES_LABEL={
			"ar":"الْعَرَبيّة",
			"pt_BR":"Português brasileiro",
			"bg":"български език",
#			"ca":"català",
			"cs":"čeština",
			"da":"dansk",
			"nl":"Nederlands",
			"en":"English",
			"fi":"suomi",
			"fr":"Français",
			"de":"Deutsch",
			"nds":"Plattdüütsch",
			"el":"ελληνικά",
			"hu":"magyar nyelv",
			"it":"Italiano",
			"nb":"Bokmål",
			"pl":"język polski",
#			"rom":"rromani ćhib",
			"ru":"Русский",
			"es":"Español",
			"sv":"svenska"
		}


if LOCAL:
	TDomain = './locale'
else:
	TDomain = os.path.join(DATADIR,'locale')

LANGUAGES=LANGUAGES_LABEL.keys()
TRANSLATION={}
for i in range(len(LANGUAGES)):
	try:
		TRANSLATION[LANGUAGES[i]] = gettext.translation("openastro",TDomain,languages=[LANGUAGES[i]])
	except IOError:
		print "IOError! Invalid languages specified (%s) in %s" %(LANGUAGES[i],TDomain)
		TRANSLATION[LANGUAGES[i]] = gettext.translation("openastro",TDomain,languages=['en'])
		
try:
	TRANSLATION["default"] = gettext.translation("openastro",TDomain)
except IOError:
	print "OpenAstro.org has not yet been translated in your language! Could not load translation..."
	TRANSLATION["default"] = gettext.translation("openastro",TDomain,languages=['en'])


#config class
class openAstroCfg:
	
	def __init__(self):
		self.version = VERSION
		dprint("-------------------------------")
		dprint('  OpenAstro.org '+str(self.version))
		dprint("-------------------------------")
		self.homedir = os.path.expanduser("~")
		self.astrodir = os.path.join(self.homedir, '.openastro.org')
		#working directory
		if LOCAL:
			cwd = './'
		else:
			cwd = DATADIR
		#geonames database
		self.geonamesdb = os.path.join(cwd, 'geonames.sql' )
		#icons
		icons = os.path.join(cwd,'icons')
		self.iconWindow = os.path.join(icons, 'openastro.svg')
		self.iconAspects = os.path.join(icons, 'aspects')
		#basic files
		self.tempfilename = os.path.join(TMPDIR,"openAstroChart.svg")
		self.tempfilenameprint = os.path.join(TMPDIR,"openAstroChartPrint.svg")
		self.tempfilenametable = os.path.join(TMPDIR,"openAstroChartTable.svg")
		self.tempfilenametableprint = os.path.join(TMPDIR,"openAstroChartTablePrint.svg")
		self.xml_ui = os.path.join(cwd, 'openastro-ui.xml')
		self.xml_svg = os.path.join(cwd, 'openastro-svg.xml')
		self.xml_svg_table = os.path.join(cwd, 'openastro-svg-table.xml')			
		#check for astrodir
		if os.path.isdir(self.astrodir) == False:
			os.mkdir(self.astrodir)
		#check for swiss local dir
		self.swissLocalDir = os.path.join(self.astrodir, 'swiss_ephemeris')
		if os.path.isdir(self.swissLocalDir) == False:
			os.mkdir(self.swissLocalDir)
		#sqlite databases		
		self.astrodb = os.path.join(self.astrodir, 'astrodb.sql')
		self.peopledb = os.path.join(self.astrodir, 'peopledb.sql')
		self.famousdb = os.path.join(cwd, 'famous.sql' )
		return
	
	def checkSwissEphemeris(self,num):	
		#00 = -01-600
		#06 = 600 - 1200
		#12 = 1200 - 1800
		#18 = 1800 - 2400
		#24 = 2400 - 3000
		seas='ftp://ftp.astro.com/pub/swisseph/ephe/seas_12.se1'
		semo='ftp://ftp.astro.com/pub/swisseph/ephe/semo_12.se1'
		sepl='ftp://ftp.astro.com/pub/swisseph/ephe/sepl_12.se1'

#Sqlite database
class openAstroSqlite:
	def __init__(self):
		self.dbcheck=False
		self.dbpurge="IGNORE"
		
		#--dbcheck puts dbcheck to true
		if "--dbcheck" in sys.argv:
			self.dbcheck=True
			dprint("  Database Check Enabled!")
			dprint("-------------------------------")

		#--purge purges database
		if "--purge" in sys.argv:
			self.dbcheck=True
			self.dbpurge="REPLACE"
			dprint("  Database Check Enabled!")
			dprint("  Database Purge Enabled!")
			dprint("-------------------------------")
			
		self.open()
		#get table names from sqlite_master for astrodb
		sql='SELECT name FROM sqlite_master'
		self.cursor.execute(sql)
		list=self.cursor.fetchall()
		self.tables={}
		for i in range(len(list)):
				self.tables[list[i][0]]=1
				
		#get table names from sqlite_master for peopledb
		sql='SELECT name FROM sqlite_master'
		self.pcursor.execute(sql)
		list=self.pcursor.fetchall()
		self.ptables={}
		for i in range(len(list)):
				self.ptables[list[i][0]]=1

		#check for event_natal table in peopledb
		self.ptable_event_natal = {
			"id":"INTEGER PRIMARY KEY",
			"name":"VARCHAR(50)",
			"year":"VARCHAR(4)",
			"month":"VARCHAR(2)",
			"day":"VARCHAR(2)",
			"hour":"VARCHAR(50)",
			"geolon":"VARCHAR(50)",
			"geolat":"VARCHAR(50)",
			"altitude":"VARCHAR(50)",
			"location":"VARCHAR(150)",
			"timezone":"VARCHAR(50)",
			"notes":"VARCHAR(500)",
			"image":"VARCHAR(250)",
			"countrycode":"VARCHAR(2)",
			"geonameid":"INTEGER",
			"timezonestr":"VARCHAR(100)",
			"extra":"VARCHAR(500)"
			}
		if self.ptables.has_key('event_natal') == False:		
			sql='CREATE TABLE IF NOT EXISTS event_natal (id INTEGER PRIMARY KEY,name VARCHAR(50)\
				 ,year VARCHAR(4),month VARCHAR(2), day VARCHAR(2), hour VARCHAR(50), geolon VARCHAR(50)\
			 	,geolat VARCHAR(50), altitude VARCHAR(50), location VARCHAR(150), timezone VARCHAR(50)\
			 	,notes VARCHAR(500), image VARCHAR(250), countrycode VARCHAR(2), geonameid INTEGER\
			 	,timezonestr VARCHAR(100), extra VARCHAR(250))'
			self.pcursor.execute(sql)
			dprint('creating sqlite table event_natal in peopledb')
		
		#check for astrocfg table in astrodb
		if self.tables.has_key('astrocfg') == False:
			#0=cfg_name, 1=cfg_value
			sql='CREATE TABLE IF NOT EXISTS astrocfg (name VARCHAR(150) UNIQUE,value VARCHAR(150))'
			self.cursor.execute(sql)
			self.dbcheck=True
			dprint('creating sqlite table astrocfg in astrodb')

		#check for astrocfg version
		sql='INSERT OR IGNORE INTO astrocfg (name,value) VALUES(?,?)'
		self.cursor.execute(sql,("version",cfg.version))
		#get astrocfg dict
		sql='SELECT value FROM astrocfg WHERE name="version"'
		self.cursor.execute(sql)
		self.astrocfg = {}
		self.astrocfg["version"]=self.cursor.fetchone()[0]

		#check for updated version 
		if self.astrocfg['version'] != str(cfg.version):
			dprint('version mismatch(%s != %s), checking table structure' % (self.astrocfg['version'],cfg.version))
			#insert current version and set dbcheck to true
			self.dbcheck = True
			sql='INSERT OR REPLACE INTO astrocfg VALUES("version","'+str(cfg.version)+'")'
			self.cursor.execute(sql)

		#default astrocfg keys (if dbcheck)
		if self.dbcheck:
			dprint('dbcheck astrodb.astrocfg')
			default = {
							"version":str(cfg.version),
							"use_geonames.org":"0",
							"houses_system":"P",
							"language":"default",
							"postype":"geo",
							"chartview":"traditional",
							"zodiactype":"tropical",
							"siderealmode":"FAGAN_BRADLEY"
						 }
			for k, v in default.iteritems():
				sql='INSERT OR %s INTO astrocfg (name,value) VALUES(?,?)' % (self.dbpurge)
				self.cursor.execute(sql,(k,v))
				
		#get astrocfg dict
		sql='SELECT * FROM astrocfg'
		self.cursor.execute(sql)
		self.astrocfg = {}
		for row in self.cursor:
			self.astrocfg[row['name']]=row['value']	

		#install language
		self.setLanguage(self.astrocfg['language'])
		self.lang_label=LANGUAGES_LABEL


		#fix inconsitencies between in people's database
		if self.dbcheck:
			sql='PRAGMA table_info(event_natal)'
			self.pcursor.execute(sql)
			list=self.pcursor.fetchall()
			vacuum = False
			cnames=[]
			for i in range(len(list)):
				cnames.append(list[i][1])
			for key,val in self.ptable_event_natal.iteritems():
				if key not in cnames:
					sql = 'ALTER TABLE event_natal ADD %s %s'%(key,val)
					dprint("dbcheck peopledb.event_natal adding %s %s"%(key,val))					
					self.pcursor.execute(sql)
					vacuum = True
			if vacuum:
				sql = "VACUUM"
				self.pcursor.execute(sql)
				dprint('dbcheck peopledb.event_natal: updating table definitions!')

				
		#check for history table in astrodb
		if self.tables.has_key('history') == False:
			#0=id,1=name,2=year,3=month,4=day,5=hour,6=geolon,7=geolat,8=alt,9=location,10=tz
			sql='CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY,name VARCHAR(50)\
				 ,year VARCHAR(50),month VARCHAR(50), day VARCHAR(50), hour VARCHAR(50), geolon VARCHAR(50)\
			 	,geolat VARCHAR(50), altitude VARCHAR(50), location VARCHAR(150), timezone VARCHAR(50)\
			 	,notes VARCHAR(500), image VARCHAR(250), countrycode VARCHAR(2), geonameid INTEGER, extra VARCHAR(250))'
			self.cursor.execute(sql)
			dprint('creating sqlite table history in astrodb')

		#fix inconsitencies between 0.6x and 0.7x in history table
		if self.dbcheck:
			sql='PRAGMA table_info(history)'
			self.cursor.execute(sql)
			list=self.cursor.fetchall()
			cnames=[]
			for i in range(len(list)):
				cnames.append(list[i][1])
			vacuum = False
			if "notes" not in cnames:
				sql = 'ALTER TABLE history ADD notes VARCHAR(500)'
				self.cursor.execute(sql)
				vacuum = True
			if "image" not in cnames:
				sql = 'ALTER TABLE history ADD image VARCHAR(250)'
				self.cursor.execute(sql)
				vacuum = True				
			if "countrycode" not in cnames:
				sql = 'ALTER TABLE history ADD countrycode VARCHAR(2)'
				self.cursor.execute(sql)
				vacuum = True
			if "geonameid" not in cnames:
				sql = 'ALTER TABLE history ADD geonameid INTEGER'
				self.cursor.execute(sql)
				vacuum = True
			if "extra" not in cnames:
				sql = 'ALTER TABLE history ADD extra VARCHAR(250)'
				self.cursor.execute(sql)
				vacuum = True		
			if vacuum:
				sql = "VACUUM"
				self.cursor.execute(sql)
				dprint('dbcheck: updating history table definitions!')
		
		#check for settings_aspect table in astrodb
		if self.tables.has_key('settings_aspect') == False:
			sql='CREATE TABLE IF NOT EXISTS settings_aspect (degree INTEGER UNIQUE, name VARCHAR(50)\
				 ,color VARCHAR(50),visible INTEGER, visible_grid INTEGER\
				 ,is_major INTEGER, is_minor INTEGER, orb VARCHAR(5))'
			self.cursor.execute(sql)
			self.dbcheck=True
			dprint('creating sqlite table settings_aspect in astrodb')
		
		#if update, check if everything is in order
		if self.dbcheck:
			sql='PRAGMA table_info(settings_aspect)'
			self.cursor.execute(sql)
			list=self.cursor.fetchall()
			cnames=[]
			for i in range(len(list)):
				cnames.append(list[i][1])
			vacuum = False
			if "visible" not in cnames:
				sql = 'ALTER TABLE settings_aspect ADD visible INTEGER'
				self.cursor.execute(sql)
				vacuum = True
			if "visible_grid" not in cnames:
				sql = 'ALTER TABLE settings_aspect ADD visible_grid INTEGER'
				self.cursor.execute(sql)
				vacuum = True
			if "is_major" not in cnames:
				sql = 'ALTER TABLE settings_aspect ADD is_major INTEGER'
				self.cursor.execute(sql)
				vacuum = True
			if "is_minor" not in cnames:
				sql = 'ALTER TABLE settings_aspect ADD is_minor INTEGER'
				self.cursor.execute(sql)
				vacuum = True
			if "orb" not in cnames:
				sql = 'ALTER TABLE settings_aspect ADD orb VARCHAR(5)'
				self.cursor.execute(sql)
				vacuum = True				
			if vacuum:
				sql = "VACUUM"
				self.cursor.execute(sql)
		
		#default values for settings_aspect (if dbcheck)
		if self.dbcheck:
			dprint('dbcheck astrodb.settings_aspect')		
			degree = [ 0 , 30 , 45 , 60 , 72 , 90 , 120 , 135 , 144 , 150 , 180 ]
			name = [ _('conjunction') , _('semi-sextile') , _('semi-square') , _('sextile') , _('quintile') , _('square') , _('trine') , _('sesquiquadrate') , _('biquintile') , _('quincunx') , _('opposition') ]
			color = [ '#5757e2' ,	'#810757' , 			'#b14e58' ,	 '#d59e28' , '#1f99b3' ,'#dc0000' , '#36d100' , '#985a10' , 		  '#7a9810' , 	'#fff600' ,		 '#510060' ]
			visible =      [ 1 , 0 , 0 , 1 , 1 , 1 , 1 , 0 , 1 , 1 , 1 ]
			visible_grid = [ 1 , 0 , 0 , 1 , 1 , 1 , 1 , 0 , 1 , 1 , 1 ]
			is_major =     [ 1 , 0 , 0 , 1 , 0 , 1 , 1 , 0 , 0 , 0 , 1 ]
			is_minor = 	   [ 0 , 1 , 1 , 0 , 1 , 0 , 0 , 1 , 1 , 0 , 0 ]
			orb =    		[ 10, 3 , 3 , 6 , 2 , 8 , 8 , 3 , 2 , 3 , 10]
			#insert values
			for i in range(len(degree)):	
				sql='INSERT OR %s INTO settings_aspect \
				(degree, name, color, visible, visible_grid, is_major, is_minor, orb)\
				VALUES(%s,"%s","%s",%s,%s,%s,%s,"%s")' % ( self.dbpurge,degree[i],name[i],color[i],visible[i],
				visible_grid[i],is_major[i],is_minor[i],orb[i] )
				self.cursor.execute(sql)
	
		#check for colors table in astrodb
		if self.tables.has_key('color_codes') == False:
			sql='CREATE TABLE IF NOT EXISTS color_codes (name VARCHAR(50) UNIQUE\
				 ,code VARCHAR(50))'
			self.cursor.execute(sql)
			self.dbcheck=True
			dprint('creating sqlite table color_codes in astrodb')				

		#default values for colors (if dbcheck)
		self.defaultColors = {
			"zodiac_bg_0":"#482900",
			"zodiac_bg_1":"#6b3d00",
			"zodiac_bg_2":"#5995e7",
			"zodiac_bg_3":"#2b4972",
			"zodiac_bg_4":"#c54100",
			"zodiac_bg_5":"#2b286f",
			"zodiac_bg_6":"#69acf1",
			"zodiac_bg_7":"#ffd237",
			"zodiac_bg_8":"#ff7200",
			"zodiac_bg_9":"#863c00",
			"zodiac_bg_10":"#4f0377",
			"zodiac_bg_11":"#6cbfff",
			"zodiac_icon_0":"#482900",
			"zodiac_icon_1":"#6b3d00",
			"zodiac_icon_2":"#5995e7",
			"zodiac_icon_3":"#2b4972",
			"zodiac_icon_4":"#c54100",
			"zodiac_icon_5":"#2b286f",
			"zodiac_icon_6":"#69acf1",
			"zodiac_icon_7":"#ffd237",
			"zodiac_icon_8":"#ff7200",
			"zodiac_icon_9":"#863c00",
			"zodiac_icon_10":"#4f0377",
			"zodiac_icon_11":"#6cbfff",
			"zodiac_radix_ring_0":"#ff0000",	
			"zodiac_radix_ring_1":"#ff0000",
			"zodiac_radix_ring_2":"#ff0000",	
			"zodiac_transit_ring_0":"#ff0000",
			"zodiac_transit_ring_1":"#ff0000",	
			"zodiac_transit_ring_2":"#0000ff",	
			"zodiac_transit_ring_3":"#0000ff",
			"houses_radix_line":"#ff0000",
			"houses_transit_line":"#0000ff",
			"aspect_0":"#5757e2",
			"aspect_30":"#810757",
			"aspect_45":"#b14e58",
			"aspect_60":"#d59e28",
			"aspect_72":"#1f99b3",
			"aspect_90":"#dc0000",
			"aspect_120":"#36d100",
			"aspect_135":"#985a10",
			"aspect_144":"#7a9810",
			"aspect_150":"#fff600",
			"aspect_180":"#510060",
			"planet_0":"#984b00",
			"planet_1":"#150052",
			"planet_2":"#520800",
			"planet_3":"#400052",
			"planet_4":"#540000",
			"planet_5":"#47133d",
			"planet_6":"#124500",
			"planet_7":"#6f0766",
			"planet_8":"#06537f",
			"planet_9":"#713f04",
			"planet_10":"#4c1541",
			"planet_11":"#4c1541",
			"planet_12":"#331820",
			"planet_13":"#585858",
			"planet_14":"#000000",
			"planet_15":"#666f06",
			"planet_16":"#000000",
			"planet_17":"#000000",
			"planet_18":"#000000",
			"planet_19":"#000000",
			"planet_20":"#000000",
			"planet_21":"#000000",
			"planet_22":"#000000",
			"planet_23":"#ff7e00",
			"planet_24":"#FF0000",
			"planet_25":"#0000FF",
			"planet_26":"#000000",
			"planet_27":"#000000",
			"planet_28":"#000000",
			"planet_29":"#000000",
			"planet_30":"#000000"
		}
		if self.dbcheck:
			dprint('dbcheck astrodb.color_codes')
			#insert values
			for k,v in self.defaultColors.iteritems():	
				sql='INSERT OR %s INTO color_codes \
				(name, code)\
				VALUES("%s","%s")' % ( self.dbpurge , k, v )
				self.cursor.execute(sql)

		#check for label table in astrodb
		if self.tables.has_key('label') == False:
			sql='CREATE TABLE IF NOT EXISTS label (name VARCHAR(150) UNIQUE\
				 ,value VARCHAR(200))'
			self.cursor.execute(sql)
			self.dbcheck=True
			dprint('creating sqlite table label in astrodb')				

		#default values for label (if dbcheck)
		self.defaultLabel = {
			"cusp":_("Cusp"),
			"longitude":_("Longitude"),
			"latitude":_("Latitude"),
			"north":_("North"),
			"east":_("East"),
			"south":_("South"),
			"west":_("West"),
			"apparent_geocentric":_("Apparent Geocentric"),
			"true_geocentric":_("True Geocentric"),
			"topocentric":_("Topocentric"),
			"heliocentric":_("Heliocentric"),
			"fire":_("Fire"),
			"earth":_("Earth"),
			"air":_("Air"),
			"water":_("Water"),
			"radix":_("Radix"),
			"transit":_("Transit"),
			"synastry":_("Synastry"),
			"composite":_("Composite"),
			"combine":_("Combine"),
			"solar":_("Solar"),
			"secondary_progressions":_("Secondary Progressions")
		}
		if self.dbcheck:
			dprint('dbcheck astrodb.label')
			#insert values
			for k,v in self.defaultLabel.iteritems():	
				sql='INSERT OR %s INTO label \
				(name, value)\
				VALUES("%s","%s")' % ( self.dbpurge , k, v )
				self.cursor.execute(sql)
		
		#check for settings_planet table in astrodb
		self.table_settings_planet={
				"id":"INTEGER UNIQUE",
				"name":"VARCHAR(50)",
				"color":"VARCHAR(50)",
				"visible":"INTEGER",
				"element_points":"INTEGER",
				"zodiac_relation":"VARCHAR(50)",
				"label":"VARCHAR(50)",
				"label_short":"VARCHAR(20)",
				"visible_aspect_line":"INTEGER",
				"visible_aspect_grid":"INTEGER"
				}
		if self.tables.has_key('settings_planet') == False:
			sql='CREATE TABLE IF NOT EXISTS settings_planet (id INTEGER UNIQUE, name VARCHAR(50)\
				,color VARCHAR(50),visible INTEGER, element_points INTEGER, zodiac_relation VARCHAR(50)\
			 	,label VARCHAR(50), label_short VARCHAR(20), visible_aspect_line INTEGER\
			 	,visible_aspect_grid INTEGER)'
			self.cursor.execute(sql)
			self.dbcheck=True
			dprint('creating sqlite table settings_planet in astrodb')
		

		#default values for settings_planet (if dbcheck)
		if self.dbcheck:
			dprint('dbcheck astrodb.settings_planet')	
			self.value_settings_planet={}	
			self.value_settings_planet['name'] = [
			'sun','moon','mercury','venus','mars','jupiter','saturn',
			'uranus','neptune','pluto','mean node','true node','mean apogee','osc. apogee',
			'earth','chiron','pholus','ceres','pallas','juno','vesta',
			'intp. apogee','intp. perigee','Asc','Mc','Dsc','Ic','day pars',
			'night pars','south node', 'marriage pars']
			orb = [
			#sun
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#moon
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#mercury
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#venus
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#mars
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#jupiter
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#saturn
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#uranus
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#neptunus
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}',
			#pluto
			'{0:10,180:10,90:10,120:10,60:6,30:3,150:3,45:3,135:3,72:1,144:1}'
			]
			self.value_settings_planet['label'] = [
			_('Sun'),_('Moon'),_('Mercury'),_('Venus'),_('Mars'),_('Jupiter'),_('Saturn'),
			_('Uranus'),_('Neptune'),_('Pluto'),_('North Node'),'?',_('Lilith'),_('Osc. Lilith'),
			_('Earth'),_('Chiron'),_('Pholus'),_('Ceres'),_('Pallas'),_('Juno'),_('Vesta'),
			'intp. apogee','intp. perigee',_('Asc'),_('Mc'),_('Dsc'),_('Ic'),_('Day Pars'),
			_('Night Pars'),_('South Node'),_('Marriage Pars')]
			self.value_settings_planet['label_short'] = [
			'sun','moon','mercury','venus','mars','jupiter','saturn',
			'uranus','neptune','pluto','Node','?','Lilith','?',
			'earth','chiron','pholus','ceres','pallas','juno','vesta',
			'intp. apogee','intp. perigee','Asc','Mc','Dsc','Ic','DP',
			'NP','SNode','marriage']
			self.value_settings_planet['color'] = [
			'#984b00','#150052','#520800','#400052','#540000','#47133d','#124500',
			'#6f0766','#06537f','#713f04','#4c1541','#4c1541','#33182','#000000',
			'#000000','#666f06','#000000','#000000','#000000','#000000','#000000',
			'#000000','#000000','orange','#FF0000','#0000FF','#000000','#000000',
			'#000000','#000000','#000000']
			self.value_settings_planet['visible'] = [
			1,1,1,1,1,1,1,
			1,1,1,1,0,1,0,
			0,1,0,0,0,0,0,
			0,0,1,1,0,0,1,
			1,0,0]
			self.value_settings_planet['visible_aspect_line'] = [
			1,1,1,1,1,1,1,
			1,1,1,1,0,1,0,
			0,1,0,0,0,0,0,
			0,0,1,1,0,0,1,
			1,0,0]
			self.value_settings_planet['visible_aspect_grid'] = [
			1,1,1,1,1,1,1,
			1,1,1,1,0,1,0,
			0,1,0,0,0,0,0,
			0,0,1,1,0,0,1,
			1,0,0]
			self.value_settings_planet['element_points'] = [
			40,40,15,15,15,10,10,
			10,10,10,20,0,0,0,
			0,5,0,0,0,0,0,
			0,0,40,20,0,0,0,
			0,0,0]
			#zodiac relation gives 10 extra points in element calculation
			self.value_settings_planet['zodiac_relation'] = [
			'4','3','2,5','1,6','0','9','8',
			'10','11','7','-1','-1','-1','-1',
			'-1','-1','-1','-1','-1','-1','-1',
			'-1','-1','-1','-1','-1','-1','-1',
			'-1','-1','-1']

			#if update, check if everything is in order with settings_planet
			sql='PRAGMA table_info(settings_planet)'
			self.cursor.execute(sql)
			list=self.cursor.fetchall()
			vacuum = False
			cnames=[]
			for i in range(len(list)):
				cnames.append(list[i][1])
			for key,val in self.table_settings_planet.iteritems():
				if key not in cnames:
					sql = 'ALTER TABLE settings_planet ADD %s %s'%(key,val)
					dprint("dbcheck astrodb.settings_planet adding %s %s"%(key,val))					
					self.cursor.execute(sql)
					#update values for col
					self.cursor.execute("SELECT id FROM settings_planet ORDER BY id DESC LIMIT 1")
					c = self.cursor.fetchone()[0]+1
					for rowid in range(c):
						sql = 'UPDATE settings_planet SET %s=? WHERE id=?' %(key)
						self.cursor.execute(sql,(self.value_settings_planet[key][rowid],rowid))
					vacuum = True
			if vacuum:
				sql = "VACUUM"
				self.cursor.execute(sql)

			#insert values for planets that don't exists
			for i in range(len(self.value_settings_planet['name'])):
				sql='INSERT OR %s INTO settings_planet VALUES(?,?,?,?,?,?,?,?,?,?)'%(self.dbpurge)
				values=(i,
						self.value_settings_planet['name'][i],
						self.value_settings_planet['color'][i],
						self.value_settings_planet['visible'][i],
						self.value_settings_planet['element_points'][i],
						self.value_settings_planet['zodiac_relation'][i],
						self.value_settings_planet['label'][i],
						self.value_settings_planet['label_short'][i],
						self.value_settings_planet['visible_aspect_line'][i],
						self.value_settings_planet['visible_aspect_grid'][i]
						)
				self.cursor.execute(sql,values)

		#commit initial changes
		self.updateHistory()
		self.link.commit()
		self.plink.commit()
		self.close()

	def setLanguage(self, lang=None):
		if lang==None or lang=="default":			
			TRANSLATION["default"].install()
			dprint("installing default language")
		else:
			TRANSLATION[lang].install()
			dprint("installing language (%s)"%(lang))
		return

	def addHistory(self):
		self.open()
		sql = 'INSERT INTO history \
			(id,name,year,month,day,hour,geolon,geolat,altitude,location,timezone,countrycode) VALUES \
			(null,?,?,?,?,?,?,?,?,?,?,?)'
		tuple = (openAstro.name,openAstro.year,openAstro.month,openAstro.day,openAstro.hour,
			openAstro.geolon,openAstro.geolat,openAstro.altitude,openAstro.location,
			openAstro.timezone,openAstro.countrycode)
		self.cursor.execute(sql,tuple)
		self.link.commit()
		self.updateHistory()
		self.close()
	
	def getAstrocfg(self,key):
		self.open()
		sql='SELECT value FROM astrocfg WHERE name="%s"' % key
		self.cursor.execute(sql)
		one=self.cursor.fetchone()
		self.close()
		if one == None:
			return None
		else:
			return one[0]
	
	def setAstrocfg(self,key,val):
		sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES (?,?)'
		self.query([sql],[(key,val)])
		self.astrocfg[key]=val
		return

	def getColors(self):
		self.open()
		sql='SELECT * FROM color_codes'
		self.cursor.execute(sql)
		list=self.cursor.fetchall()
		out={}
		for i in range(len(list)):
			out[list[i][0]] = list[i][1]
		self.close()
		return out

	def getLabel(self):
		self.open()
		sql='SELECT * FROM label'
		self.cursor.execute(sql)
		list=self.cursor.fetchall()
		out={}
		for i in range(len(list)):
			out[list[i][0]] = list[i][1]
		self.close()
		return out	
	
	def getDatabase(self):
		self.open()

		sql = 'SELECT * FROM event_natal ORDER BY id ASC'
		self.pcursor.execute(sql)
		dict = []
		for row in self.pcursor:
			s={}			
			for key,val in self.ptable_event_natal.iteritems():
				if row[key] == None:
					s[key]=""
				else:
					s[key]=row[key]
			dict.append(s)
		self.close()
		return dict
		

	def getDatabaseFamous(self,limit="2000",search=None):
		self.flink = sqlite3.connect(cfg.famousdb)
		self.flink.row_factory = sqlite3.Row
		self.fcursor = self.flink.cursor()
		
		if search:
			sql='SELECT * FROM famous WHERE year>? AND \
			(lastname LIKE ? OR firstname LIKE ? OR name LIKE ?)\
			 LIMIT %s'%(limit)
			self.fcursor.execute(sql,(1800,search,search,search))	
		else:
			sql='SELECT * FROM famous WHERE year>? LIMIT %s'%(limit)
			self.fcursor.execute(sql,(1800,))
		
		oldDB=self.fcursor.fetchall()
		
		self.fcursor.close()
		self.flink.close()

		#process database
		newDB = []
		for a in range(len(oldDB)):
			#minus years
			if oldDB[a][12] == '571/': #Muhammad
				year = 571		
			elif oldDB[a][12] <= 0:
				year = 1
			else:
				year = oldDB[a][12]
		
			month = oldDB[a][13]
			day = oldDB[a][14]
			hour = oldDB[a][15]
			h,m,s = openAstro.decHour(hour)
			
			#aware datetime object
			dt = zonetab.stdtime(oldDB[a][20],year,month,day,h,m,s)
			#naive utc datetime object
			dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()
			#timezone
			timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
			year = dt_utc.year
			month = dt_utc.month
			day = dt_utc.day
			hour = openAstro.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		
			newDB.append({
						"id":oldDB[a][0], #id INTEGER
						"name":str(a+1)+". "+oldDB[a][3]+" "+oldDB[a][4], #name
						"year":year, #year
						"month":month, #month
						"day":day, #day
						"hour":hour, #hour
						"geolon":oldDB[a][18], #geolon
						"geolat":oldDB[a][17], #geolat
						"altitude":"25", #altitude
						"location":oldDB[a][16], #location
						"timezone":timezone, #timezone
						"notes":"",#notes
						"image":"",#image
						"countrycode":oldDB[a][8], #countrycode
						"geonameid":oldDB[a][19], #geonameid
						"timezonestr":oldDB[a][20], #timezonestr
						"extra":"" #extra
						}) 

		return newDB	
		
	def getSettingsPlanet(self):
		self.open()
		sql = 'SELECT * FROM settings_planet ORDER BY id ASC'
		self.cursor.execute(sql)
		dict = []
		for row in self.cursor:
			s={}			
			for key,val in self.table_settings_planet.iteritems():
				s[key]=row[key]
			dict.append(s)
		self.close()
		return dict
		
	def getSettingsAspect(self):
		self.open()
		sql = 'SELECT * FROM settings_aspect ORDER BY degree ASC'
		self.cursor.execute(sql)
		dict = []
		for row in self.cursor:
			#degree, name, color, visible, visible_grid, is_major, is_minor, orb
			dict.append({'degree':row['degree'],'name':row['name'],'color':row['color']
			,'visible':row['visible'],'visible_grid':row['visible_grid']			
			,'is_major':row['is_major'],'is_minor':row['is_minor'],'orb':row['orb']})
		self.close()
		return dict
	
	def getSettingsLocation(self):
		#look if location is known
		if self.astrocfg.has_key('home_location') == False or self.astrocfg.has_key('home_timezonestr') == False:
			self.open()			
			sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES("home_location","")'
			self.cursor.execute(sql)
			sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES("home_geolat","")'
			self.cursor.execute(sql)
			sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES("home_geolon","")'
			self.cursor.execute(sql)
			sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES("home_countrycode","")'
			self.cursor.execute(sql)
			sql='INSERT OR REPLACE INTO astrocfg (name,value) VALUES("home_timezonestr","")'
			self.cursor.execute(sql)			
			self.link.commit()
			self.close
			return '','','','',''
		else:
			return self.astrocfg['home_location'],self.astrocfg['home_geolat'],self.astrocfg['home_geolon'],self.astrocfg['home_countrycode'],self.astrocfg['home_timezonestr']
		
	def setSettingsLocation(self, lat, lon, loc, cc, tzstr):
		self.open()
		sql = 'UPDATE astrocfg SET value="%s" WHERE name="home_location"' % loc
		self.cursor.execute(sql)
		sql = 'UPDATE astrocfg SET value="%s" WHERE name="home_geolat"' % lat
		self.cursor.execute(sql)
		sql = 'UPDATE astrocfg SET value="%s" WHERE name="home_geolon"' % lon
		self.cursor.execute(sql)
		sql = 'UPDATE astrocfg SET value="%s" WHERE name="home_countrycode"' % cc
		self.cursor.execute(sql)
		sql = 'UPDATE astrocfg SET value="%s" WHERE name="home_timezonestr"' % tzstr
		self.cursor.execute(sql)
		self.link.commit()
		self.close()
		
	def updateHistory(self):
		sql='SELECT * FROM history'
		self.cursor.execute(sql)
		self.history = self.cursor.fetchall()
		#check if limit is exceeded
		limit=10
		if len(self.history) > limit:
			sql = "DELETE FROM history WHERE id < '"+str(self.history[len(self.history)-limit][0])+"'"
			self.cursor.execute(sql)
			self.link.commit()
			#update self.history
			sql = 'SELECT * FROM history'
			self.cursor.execute(sql)
			self.history = self.cursor.fetchall()
		return	
	
	"""
	
	Function to import zet8 databases

	"""	
	
	def importZet8(self, target_db, data):
	
		target_con = sqlite3.connect(target_db)
		target_con.row_factory = sqlite3.Row
		target_cur = target_con.cursor()
		
		#get target names
		target_names={}
		sql='SELECT name FROM event_natal'
		target_cur.execute(sql)
		for row in target_cur:
			target_names[row['name']]=1
		for k,v in target_names.iteritems():		
			for i in range(1,10):
				if target_names.has_key('%s (#%s)' % (k,i)):
					target_names[k] += 1
					
		#read input write target
		for row in data:
			
			if target_names.has_key(row['name']):
				name_suffix = ' (#%s)' % target_names[row['name']]
				target_names[row['name']] += 1
			else:
				name_suffix = ''
			
			gname = self.gnearest( float(row['latitude']),float(row['longitude']) )	
			
			sql = 'INSERT INTO event_natal (id,name,year,month,day,hour,geolon,geolat,altitude,\
				location,timezone,notes,image,countrycode,geonameid,timezonestr,extra) VALUES \
				(null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
			tuple = (row['name']+name_suffix,row['year'],row['month'],row['day'],row['hour'],row['longitude'],
				row['latitude'],25,row['location'],row['timezone'],"",
				"",gname['geonameid'],gname['timezonestr'],"")
			target_cur.execute(sql,tuple)
			
		#Finished, close connection
		target_con.commit()
		target_cur.close()
		target_con.close()
						
		return
	
	"""
	
	Function to merge two databases containing entries for persons
	databaseMerge(target_db,input_db)
	
	database format:
	'CREATE TABLE IF NOT EXISTS event_natal (id INTEGER PRIMARY KEY,name VARCHAR(50)\
				 ,year VARCHAR(50),month VARCHAR(50), day VARCHAR(50), hour VARCHAR(50), geolon VARCHAR(50)\
			 	,geolat VARCHAR(50), altitude VARCHAR(50), location VARCHAR(150), timezone VARCHAR(50)\
			 	,notes VARCHAR(500), image VARCHAR(250))'
	"""	
	def databaseMerge(self,target_db,input_db):
		dprint('db.databaseMerge: %s << %s'%(target_db,input_db))
		target_con = sqlite3.connect(target_db)
		target_con.row_factory = sqlite3.Row
		target_cur = target_con.cursor()
		input_con = sqlite3.connect(input_db)
		input_con.row_factory = sqlite3.Row
		input_cur = input_con.cursor()
		#get target names
		target_names={}
		sql='SELECT name FROM event_natal'
		target_cur.execute(sql)
		for row in target_cur:
			target_names[row['name']]=1
		for k,v in target_names.iteritems():		
			for i in range(1,10):
				if target_names.has_key('%s (#%s)' % (k,i)):
					target_names[k] += 1

		#read input write target
		sql='SELECT * FROM event_natal'
		input_cur.execute(sql)
		for row in input_cur:
			if target_names.has_key(row['name']):
				name_suffix = ' (#%s)' % target_names[row['name']]
				target_names[row['name']] += 1
			else:
				name_suffix = ''
			sql = 'INSERT INTO event_natal (id,name,year,month,day,hour,geolon,geolat,altitude,\
				location,timezone,notes,image,countrycode,geonameid,timezonestr,extra) VALUES \
				(null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
			tuple = (row['name']+name_suffix,row['year'],row['month'],row['day'],row['hour'],row['geolon'],
				row['geolat'],row['altitude'],row['location'],row['timezone'],row['notes'],
				row['image'],row['countrycode'],row['geonameid'],row['timezonestr'],row['extra'])
			target_cur.execute(sql,tuple)
		
		#Finished, close connection
		target_con.commit()
		target_cur.close()
		target_con.close()
		input_cur.close()
		input_con.close()
		return
	
	"""
	
	Basic Query Functions for common databases
	
	"""
	def query(self, sql, tuple=None):
		l=sqlite3.connect(cfg.astrodb)
		c=l.cursor()
		for i in range(len(sql)):
			if tuple == None:
				c.execute(sql[i])
			else:
				c.execute(sql[i],tuple[i])
		l.commit()
		c.close()
		l.close()		
		
	def pquery(self, sql, tuple=None):
		l=sqlite3.connect(cfg.peopledb)
		c=l.cursor()
		for i in range(len(sql)):
			if tuple == None:
				c.execute(sql[i])
			else:
				c.execute(sql[i],tuple[i])
		l.commit()
		c.close()
		l.close()	
	
	def gnearest(self, lat=None, lon=None):
		#check for none
		if lat==None or lon==None:
			return {'country':None,'admin1':None,'geonameid':None,'continent':None,'timezonestr':None}
		#get closest value to lat lon
		dprint('gnearest: using %s,%s' %(lat,lon))
		diff = {}
		sql = 'SELECT id,latitude,longitude FROM geonames\
 WHERE latitude >= %s AND latitude <= %s AND longitude >= %s AND longitude <= %s' % (lat-0.5,lat+0.5,lon-0.5,lon+0.5)
 		self.gquery(sql)
 		for row in self.gcursor:
 			diff[zonetab.distance( lat , lon , row['latitude'] , row['longitude'])]=row['id']
 		self.gclose()
 		keys=diff.keys()
 		keys.sort()
 		
 		dict={}
 		if keys == []:
 			dict = {'country':None,'admin1':None,'geonameid':None,'continent':None,'timezonestr':None}
 			dprint('gnearest: no town found within 66km range!')
 		else:
 			sql = 'SELECT * FROM geonames WHERE id=%s LIMIT 1' % (diff[keys[0]])
 			self.gquery(sql)
 			geoname = self.gcursor.fetchone()
 			self.gclose()
 			dict['country']=geoname['country']
 			dict['admin1']=geoname['admin1']
 			dict['geonameid']=geoname['geonameid']
 			dict['timezonestr']=geoname['timezone']
 			sql = 'SELECT * FROM countryinfo WHERE isoalpha2="%s" LIMIT 1' % (geoname['country'])
			self.gquery(sql) 			
 			countryinfo = self.gcursor.fetchone()
 			dict['continent']=countryinfo['continent']
 			self.gclose()
 			dprint('gnearest: found town %s at %s,%s,%s' % (geoname['name'],geoname['latitude'],
 				geoname['longitude'],geoname['timezone']))
 		return dict
	
	def gquery(self, sql, tuple=None):
		self.glink = sqlite3.connect(cfg.geonamesdb)
		self.glink.row_factory = sqlite3.Row
		self.gcursor = self.glink.cursor()
		if tuple:
			self.gcursor.execute(sql,tuple)
		else:
			self.gcursor.execute(sql)
	
	def gclose(self):
		self.glink.commit()
		self.gcursor.close()
		self.glink.close()
		
	def open(self):
		self.link = sqlite3.connect(cfg.astrodb)
		self.link.row_factory = sqlite3.Row
		self.cursor = self.link.cursor()

		self.plink = sqlite3.connect(cfg.peopledb)
		self.plink.row_factory = sqlite3.Row
		self.pcursor = self.plink.cursor()
			
	def close(self):
		self.cursor.close()
		self.pcursor.close()
		self.link.close()
		self.plink.close()

#calculation and svg drawing class
class openAstroInstance:

	def __init__(self):
		
		#screen size
		displayManager = gtk.gdk.display_manager_get()
		display = displayManager.get_default_display()
		screen = display.get_default_screen()
		self.screen_width = screen.get_width()
		self.screen_height = screen.get_height()

		#get label configuration
		self.label = db.getLabel()

		#check for home
		self.home_location,self.home_geolat,self.home_geolon,self.home_countrycode,self.home_timezonestr = db.getSettingsLocation()		
		if self.home_location == '' or self.home_geolat == '' or self.home_geolon == '':
			dprint('Unknown home location, asking for new')
			self.ask_for_home = True
			self.home_location='Amsterdam'
			self.home_geolon=6.219530
			self.home_geolat=52.120710
			self.home_countrycode='NL'
			self.home_timezonestr='Europe/Amsterdam'
		else:	
			self.ask_for_home = False
			dprint('known home location: %s %s %s' % (self.home_location, self.home_geolat, self.home_geolon))
			
		#default location
		self.location=self.home_location
		self.geolat=float(self.home_geolat)
		self.geolon=float(self.home_geolon)
		self.countrycode=self.home_countrycode
		self.timezonestr=self.home_timezonestr
		
		#current datetime
		now = datetime.datetime.now()
		#aware datetime object
		dt = zonetab.stdtime(self.timezonestr, now.year, now.month, now.day, now.hour, now.minute, now.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()

		#Default
		self.name=_("Here and Now")
		self.charttype=self.label["radix"]
		self.year=dt_utc.year
		self.month=dt_utc.month
		self.day=dt_utc.day
		self.hour=self.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		self.timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
		self.altitude=25
		self.geonameid=None
		
		#Make locals
		self.utcToLocal()
		
		#configuration
		#ZOOM 1 = 100%
		self.zoom=1
		self.type="Radix"
		
		#Default dpi for svg
		rsvg.set_default_dpi(400)

		#12 zodiacs
		self.zodiac = ['aries','taurus','gemini','cancer','leo','virgo','libra','scorpio','sagittarius','capricorn','aquarius','pisces']
		self.zodiac_short = ['Ari','Tau','Gem','Cnc','Leo','Vir','Lib','Sco','Sgr','Cap','Aqr','Psc']
		self.zodiac_color = ['#482900','#6b3d00','#5995e7','#2b4972','#c54100','#2b286f','#69acf1','#ffd237','#ff7200','#863c00','#4f0377','#6cbfff']
		self.zodiac_element = ['fire','earth','air','water','fire','earth','air','water','fire','earth','air','water']

		#get color configuration
		self.colors = db.getColors()
		
		return
		
	def utcToLocal(self):
		#make local time variables from global UTC
		h, m, s = self.decHour(self.hour)
		utc = datetime.datetime(self.year, self.month, self.day, h, m, s)
		tz = datetime.timedelta(seconds=float(self.timezone)*float(3600))
		loc = utc + tz
		self.year_loc = loc.year
		self.month_loc = loc.month
		self.day_loc = loc.day
		self.hour_loc = loc.hour
		self.minute_loc = loc.minute
		self.second_loc = loc.second
		#print some info
		dprint('utcToLocal: '+str(utc)+' => '+str(loc)+self.decTzStr(self.timezone))
	
	def localToSolar(self, newyear):
		solaryearsecs = 31556925.51 # 365 days, 5 hours, 48 minutes, 45.51 seconds
		dprint("localToSolar: from %s to %s" %(self.year,newyear))
		h,m,s = self.decHour(self.hour)
		dt_original = datetime.datetime(self.year,self.month,self.day,h,m,s)
		dt_new = datetime.datetime(newyear,self.month,self.day,h,m,s)
		dprint("localToSolar: first sun %s" % (self.planets_degree_ut[0]) )
		mdata = ephemeris.ephData(newyear,self.month,self.day,self.hour,self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)
		dprint("localToSolar: second sun %s" % (mdata.planets_degree_ut[0]) )
		sundiff = self.planets_degree_ut[0] - mdata.planets_degree_ut[0]
		dprint("localToSolar: sundiff %s" %(sundiff))
		sundelta = ( sundiff / 360.0 ) * solaryearsecs
		dprint("localToSolar: sundelta %s" % (sundelta))
		dt_delta = datetime.timedelta(seconds=int(sundelta))
		dt_new = dt_new + dt_delta
		mdata = ephemeris.ephData(dt_new.year,dt_new.month,dt_new.day,self.decHourJoin(dt_new.hour,dt_new.minute,dt_new.second),self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)
		dprint("localToSolar: new sun %s" % (mdata.planets_degree_ut[0]))
		
		#get precise
		step = 0.000011408 # 1 seconds in degrees
		sundiff = self.planets_degree_ut[0] - mdata.planets_degree_ut[0]
		sundelta = sundiff / step
		dt_delta = datetime.timedelta(seconds=int(sundelta))
		dt_new = dt_new + dt_delta
		mdata = ephemeris.ephData(dt_new.year,dt_new.month,dt_new.day,self.decHourJoin(dt_new.hour,dt_new.minute,dt_new.second),self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)
		dprint("localToSolar: new sun #2 %s" % (mdata.planets_degree_ut[0]))

		step = 0.000000011408 # 1 milli seconds in degrees
		sundiff = self.planets_degree_ut[0] - mdata.planets_degree_ut[0]
		sundelta = sundiff / step
		dt_delta = datetime.timedelta(milliseconds=int(sundelta))
		dt_new = dt_new + dt_delta
		mdata = ephemeris.ephData(dt_new.year,dt_new.month,dt_new.day,self.decHourJoin(dt_new.hour,dt_new.minute,dt_new.second),self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)
		dprint("localToSolar: new sun #3 %s" % (mdata.planets_degree_ut[0]))	
		
		self.s_year = dt_new.year
		self.s_month = dt_new.month
		self.s_day = dt_new.day
		self.s_hour = self.decHourJoin(dt_new.hour,dt_new.minute,dt_new.second)
		self.s_geolon = self.geolon
		self.s_geolat = self.geolat
		self.s_altitude = self.altitude
		self.type = "Solar"
		openAstro.charttype="%s (%s-%02d-%02d %02d:%02d:%02d UTC)" % (openAstro.label["solar"],self.s_year,self.s_month,self.s_day,dt_new.hour,dt_new.minute,dt_new.second)
		openAstro.transit=False	
		return
		
	def localToSecondaryProgression(self,dt):
		
		#remove timezone
		dt_utc = dt - datetime.timedelta(seconds=float(self.timezone)*float(3600))
		h,m,s = self.decHour(self.hour)
		dt_new = ephemeris.years_diff(self.year,self.month,self.day,self.hour,
			dt_utc.year,dt_utc.month,dt_utc.day,self.decHourJoin(dt_utc.hour,
			dt_utc.minute,dt_utc.second))
	
		self.sp_year = dt_new.year
		self.sp_month = dt_new.month
		self.sp_day = dt_new.day
		self.sp_hour = self.decHourJoin(dt_new.hour,dt_new.minute,dt_new.second)
		self.sp_geolon = self.geolon
		self.sp_geolat = self.geolat
		self.sp_altitude = self.altitude
		self.houses_override = [dt_new.year,dt_new.month,dt_new.day,self.hour]

		dprint("localToSecondaryProgression: got UTC %s-%s-%s %s:%s:%s"%(
			dt_new.year,dt_new.month,dt_new.day,dt_new.hour,dt_new.minute,dt_new.second))
			
		self.type = "SecondaryProgression"
		openAstro.charttype="%s (%s-%02d-%02d %02d:%02d)" % (openAstro.label["secondary_progressions"],dt.year,dt.month,dt.day,dt.hour,dt.minute)
		openAstro.transit=False
		return
	
	def makeSVG( self , printing=None ):
		#empty element points
		self.fire=0.0
		self.earth=0.0
		self.air=0.0
		self.water=0.0
			
		#get database planet settings	
		self.planets = db.getSettingsPlanet()
		
		#get database aspect settings
		self.aspects = db.getSettingsAspect()
		
		#Combine module data
		if self.type == "Combine":
			#make calculations
			module_data = ephemeris.ephData(self.c_year,self.c_month,self.c_day,self.c_hour,self.c_geolon,self.c_geolat,self.c_altitude,self.planets,self.zodiac,db.astrocfg)
		
		#Solar module data
		if self.type == "Solar":
			module_data = ephemeris.ephData(self.s_year,self.s_month,self.s_day,self.s_hour,self.s_geolon,self.s_geolat,self.s_altitude,self.planets,self.zodiac,db.astrocfg)
		
		elif self.type == "SecondaryProgression":
			module_data = ephemeris.ephData(self.sp_year,self.sp_month,self.sp_day,self.sp_hour,self.sp_geolon,self.sp_geolat,self.sp_altitude,self.planets,self.zodiac,db.astrocfg,houses_override=self.houses_override)				
			
		elif self.type == "Transit" or self.type == "Composite":
			module_data = ephemeris.ephData(self.year,self.month,self.day,self.hour,self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)
			t_module_data = ephemeris.ephData(self.t_year,self.t_month,self.t_day,self.t_hour,self.t_geolon,self.t_geolat,self.t_altitude,self.planets,self.zodiac,db.astrocfg)
		
		else:
			#make calculations
			module_data = ephemeris.ephData(self.year,self.month,self.day,self.hour,self.geolon,self.geolat,self.altitude,self.planets,self.zodiac,db.astrocfg)

		#Transit module data
		if self.type == "Transit" or self.type == "Composite":
			#grab transiting module data
			self.t_planets_sign = t_module_data.planets_sign
			self.t_planets_degree = t_module_data.planets_degree
			self.t_planets_degree_ut = t_module_data.planets_degree_ut
			self.t_planets_retrograde = t_module_data.planets_retrograde
			self.t_houses_degree = t_module_data.houses_degree
			self.t_houses_sign = t_module_data.houses_sign
			self.t_houses_degree_ut = t_module_data.houses_degree_ut
			
		#grab normal module data
		self.planets_sign = module_data.planets_sign
		self.planets_degree = module_data.planets_degree
		self.planets_degree_ut = module_data.planets_degree_ut
		self.planets_retrograde = module_data.planets_retrograde
		self.houses_degree = module_data.houses_degree
		self.houses_sign = module_data.houses_sign
		self.houses_degree_ut = module_data.houses_degree_ut		
		
		#make composite averages
		if self.type == "Composite":
			#new houses
			asc = self.houses_degree_ut[0]
			t_asc = self.t_houses_degree_ut[0]
			for i in range(12):
				#difference in distances measured from ASC
				diff = self.houses_degree_ut[i] - asc
				if diff < 0:
					diff = diff + 360.0
				t_diff = self.t_houses_degree_ut[i] - t_asc
				if t_diff < 0:
					t_diff = t_diff + 360.0	
				newdiff = (diff + t_diff) / 2.0
				
				#new ascendant
				if asc > t_asc:
					diff = asc - t_asc
					if diff > 180:
						diff = 360.0 - diff
						nasc = asc + (diff / 2.0)
					else:
						nasc = t_asc + (diff / 2.0)
				else:
					diff = t_asc - asc
					if diff > 180:
						diff = 360.0 - diff
						nasc = t_asc + (diff / 2.0)
					else:
						nasc = asc + (diff / 2.0)
				
				#new house degrees
				self.houses_degree_ut[i] = nasc + newdiff
				if self.houses_degree_ut[i] > 360:
					self.houses_degree_ut[i] = self.houses_degree_ut[i] - 360.0	
					
				#new house sign				
				for x in range(len(self.zodiac)):
					deg_low=float(x*30)
					deg_high=float((x+1)*30)
					if self.houses_degree_ut[i] >= deg_low:
						if self.houses_degree_ut[i] <= deg_high:
							self.houses_sign[i]=x
							self.houses_degree[i] = self.houses_degree_ut[i] - deg_low

			#new planets
			for i in range(23):
				#difference in degrees
				p1 = self.planets_degree_ut[i]
				p2 = self.t_planets_degree_ut[i]
				if p1 > p2:
					diff = p1 - p2
					if diff > 180:
						diff = 360.0 - diff
						self.planets_degree_ut[i] = (diff / 2.0) + p1
					else:
						self.planets_degree_ut[i] = (diff / 2.0) + p2
				else:
					diff = p2 - p1
					if diff > 180:
						diff = 360.0 - diff
						self.planets_degree_ut[i] = (diff / 2.0) + p2
					else:
						self.planets_degree_ut[i] = (diff / 2.0) + p1
				
				if self.planets_degree_ut[i] > 360:
					self.planets_degree_ut[i] = self.planets_degree_ut[i] - 360.0
			
			#list index 23 is asc, 24 is Mc, 25 is Dsc, 26 is Ic
			self.planets_degree_ut[23] = self.houses_degree_ut[0]
			self.planets_degree_ut[24] = self.houses_degree_ut[9]
			self.planets_degree_ut[25] = self.houses_degree_ut[6]
			self.planets_degree_ut[26] = self.houses_degree_ut[3]
								
			#new planet signs
			for i in range(27):
				for x in range(len(self.zodiac)):
					deg_low=float(x*30)
					deg_high=float((x+1)*30)
					if self.planets_degree_ut[i] >= deg_low:
						if self.planets_degree_ut[i] <= deg_high:
							self.planets_sign[i]=x
							self.planets_degree[i] = self.planets_degree_ut[i] - deg_low
							self.planets_retrograde[i] = False
			
		
		#width and height from screen
		ratio = float(self.screen_width) / float(self.screen_height)
		if ratio < 1.3: #1280x1024
			wm_off = 130
		else: # 1024x768, 800x600, 1280x800, 1680x1050
			wm_off = 100
			
		#check for printer
		if printing == None:
			svgHeight=self.screen_height-wm_off
			svgWidth=self.screen_width-5.0
			#svgHeight=self.screen_height-wm_off
			#svgWidth=(770.0*svgHeight)/540.0
			#svgWidth=float(self.screen_width)-25.0
			rotate = "0"
			translate = "0"
			viewbox = '0 0 772.2 546.0' #297mm * 2.6 + 210mm * 2.6
		else:
			sizeX=546.0
			sizeY=772.2
			svgWidth = printing['width']
			svgHeight = printing['height']
			rotate = "90"
			viewbox = '0 0 %s %s'  % (printing['width'],printing['height'])
			translateX= sizeX + ((printing['width'] - sizeX) * 0.5 )
			translateY= ( printing['height'] - sizeY ) * 0.5
			translate = "%s,%s" % ( translateX , translateY )
			
		
		#template dictionary		
		td = dict()
		r=240
		if(db.astrocfg['chartview']=="european"):
			self.c1=56
			self.c2=92
			self.c3=112
		else:				
			self.c1=0
			self.c2=36
			self.c3=120
		
		#transit
		if self.type == "Transit":
			td['transitRing']=self.transitRing( r )
			td['degreeRing']=self.degreeTransitRing( r )
			#circles
			td['c1'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-36) + '"'
			td['c1style'] = 'fill: none; stroke: %s; stroke-width: 1px; stroke-opacity:.4;'%(self.colors['zodiac_transit_ring_2'])
			td['c2'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-72) + '"'
			td['c2style'] = 'fill: #fff; fill-opacity:.4; stroke: %s; stroke-opacity:.4; stroke-width: 1px'%(self.colors['zodiac_transit_ring_1'])
			td['c3'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-160) + '"'
			td['c3style'] = 'fill: #fff; fill-opacity:.8; stroke: %s; stroke-width: 1px'%(self.colors['zodiac_transit_ring_0'])
			td['makeAspects'] = self.makeAspectsTransit( r , (r-160))
			td['makeAspectGrid'] = self.makeAspectTransitGrid( r )
			td['makePatterns'] = ''
		else:
			td['transitRing']=""
			td['degreeRing']=self.degreeRing( r )
			#circles
			td['c1'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-self.c1) + '"'
			td['c1style'] = 'fill: none; stroke: %s; stroke-width: 1px; '%(self.colors['zodiac_radix_ring_2'])
			td['c2'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-self.c2) + '"'
			td['c2style'] = 'fill: #fff; fill-opacity:.2; stroke: %s; stroke-opacity:.4; stroke-width: 1px'%(self.colors['zodiac_radix_ring_1'])
			td['c3'] = 'cx="' + str(r) + '" cy="' + str(r) + '" r="' + str(r-self.c3) + '"'
			td['c3style'] = 'fill: #fff; fill-opacity:.8; stroke: %s; stroke-width: 1px'%(self.colors['zodiac_radix_ring_0'])
			td['makeAspects'] = self.makeAspects( r , (r-self.c3))
			td['makeAspectGrid'] = self.makeAspectGrid( r )
			td['makePatterns'] = self.makePatterns()

		td['circleX']=str(0)
		td['circleY']=str(0)
		td['svgWidth']=str(svgWidth)
		td['svgHeight']=str(svgHeight)
		td['viewbox']=viewbox
		td['stringTitle']=self.name
		td['stringName']=self.charttype
		
		#bottom left
		siderealmode_chartview={
				"FAGAN_BRADLEY":_("Fagan Bradley"),
				"LAHIRI":_("Lahiri"),
				"DELUCE":_("Deluce"),
				"RAMAN":_("Ramanb"),
				"USHASHASHI":_("Ushashashi"),
				"KRISHNAMURTI":_("Krishnamurti"),
				"DJWHAL_KHUL":_("Djwhal Khul"),
				"YUKTESHWAR":_("Yukteshwar"),
				"JN_BHASIN":_("Jn Bhasin"),
				"BABYL_KUGLER1":_("Babyl Kugler 1"),
				"BABYL_KUGLER2":_("Babyl Kugler 2"),
				"BABYL_KUGLER3":_("Babyl Kugler 3"),
				"BABYL_HUBER":_("Babyl Huber"),
				"BABYL_ETPSC":_("Babyl Etpsc"),
				"ALDEBARAN_15TAU":_("Aldebaran 15Tau"),
				"HIPPARCHOS":_("Hipparchos"),
				"SASSANIAN":_("Sassanian"),
				"J2000":_("J2000"),
				"J1900":_("J1900"),
				"B1950":_("B1950")
				}

		if db.astrocfg['zodiactype'] == 'sidereal':
			td['bottomLeft1']=_("Sidereal")
			td['bottomLeft2']=siderealmode_chartview[db.astrocfg['siderealmode']]
		else:
			td['bottomLeft1']=_("Tropical")
			td['bottomLeft2'] = ''
		
		td['bottomLeft3'] = ''
		td['bottomLeft4'] = ''

		#stringlocation
		if len(self.location) > 35:
			split=self.location.split(",")
			if len(split) > 1:
				td['stringLocation']=split[0]+", "+split[-1]
				if len(td['stringLocation']) > 35:
					td['stringLocation'] = td['stringLocation'][:35]+"..."
			else:
				td['stringLocation']=self.location[:35]+"..."
		else:
			td['stringLocation']=self.location
		td['stringDateTime']=str(self.year_loc)+'-%(#1)02d-%(#2)02d %(#3)02d:%(#4)02d:%(#5)02d' % {'#1':self.month_loc,'#2':self.day_loc,'#3':self.hour_loc,'#4':self.minute_loc,'#5':self.second_loc} + self.decTzStr(self.timezone)
		td['stringLat']="%s: %s" %(self.label['latitude'],self.lat2str(self.geolat))
		td['stringLon']="%s: %s" %(self.label['longitude'],self.lon2str(self.geolon))
		postype={"geo":self.label["apparent_geocentric"],"truegeo":self.label["true_geocentric"],
				"topo":self.label["topocentric"],"helio":self.label["heliocentric"]}
		td['stringPosition']=postype[db.astrocfg['postype']]
		
		#planets_color_X
		for i in range(len(self.planets)):
			td['planets_color_%s'%(i)]=self.colors["planet_%s"%(i)]
		
		#zodiac_color_X
		for i in range(12):
			td['zodiac_color_%s'%(i)]=self.colors["zodiac_icon_%s" %(i)]
		
		#orb_color_X
		for i in range(len(self.aspects)):
			td['orb_color_%s'%(self.aspects[i]['degree'])]=self.colors["aspect_%s" %(self.aspects[i]['degree'])]
		
		#config
		td['cfgZoom']=str(self.zoom)
		td['cfgRotate']=rotate
		td['cfgTranslate']=translate
		
		#functions
		td['makeZodiac'] = self.makeZodiac( r )
		td['makeHouses'] = self.makeHouses( r )
		td['makePlanets'] = self.makePlanets( r )
		td['makeElements'] = self.makeElements( r )
		td['makePlanetGrid'] = self.makePlanetGrid()
		td['makeHousesGrid'] = self.makeHousesGrid()
				
		#read template
		f=open(cfg.xml_svg)
		template=Template(f.read()).substitute(td)
		f.close()
		
		#write template
		if printing:
			f=open(cfg.tempfilenameprint,"w")
			dprint("Printing SVG: lat="+str(self.geolat)+' lon='+str(self.geolon)+' loc='+self.location)
		else:
			f=open(cfg.tempfilename,"w")
			dprint("Creating SVG: lat="+str(self.geolat)+' lon='+str(self.geolon)+' loc='+self.location)
		
		f.write(template)
		f.close()

		#return filename
		return cfg.tempfilename

	#draw transit ring
	def transitRing( self , r ):
		out = '<circle cx="%s" cy="%s" r="%s" style="fill: none; stroke: #fff; stroke-width: 36px; stroke-opacity: .4;"/>' % (r,r,r-18)
		out += '<circle cx="%s" cy="%s" r="%s" style="fill: none; stroke: %s; stroke-width: 1px; stroke-opacity: .6;"/>' % (r,r,r,self.colors['zodiac_transit_ring_3'])
		return out	
	
	#draw degree ring
	def degreeRing( self , r ):
		out=''
		for i in range(72):
			offset = float(i*5) - self.houses_degree_ut[6]
			if offset < 0:
				offset = offset + 360.0
			elif offset > 360:
				offset = offset - 360.0
			x1 = self.sliceToX( 0 , r-self.c1 , offset ) + self.c1
			y1 = self.sliceToY( 0 , r-self.c1 , offset ) + self.c1
			x2 = self.sliceToX( 0 , r+2-self.c1 , offset ) - 2 + self.c1
			y2 = self.sliceToY( 0 , r+2-self.c1 , offset ) - 2 + self.c1
			out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: 1px; stroke-opacity:.9;"/>\n' % (
				x1,y1,x2,y2 )
		return out
		
	def degreeTransitRing( self , r ):
		out=''
		for i in range(72):
			offset = float(i*5) - self.houses_degree_ut[6]
			if offset < 0:
				offset = offset + 360.0
			elif offset > 360:
				offset = offset - 360.0
			x1 = self.sliceToX( 0 , r , offset )
			y1 = self.sliceToY( 0 , r , offset )
			x2 = self.sliceToX( 0 , r+2 , offset ) - 2
			y2 = self.sliceToY( 0 , r+2 , offset ) - 2
			out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #F00; stroke-width: 1px; stroke-opacity:.9;"/>\n' % (
				x1,y1,x2,y2 )
		return out
	
	#floating latitude an longitude to string
	def lat2str( self, coord ):
		sign=self.label["north"]
		if coord < 0.0:
			sign=self.label["south"]
			coord = abs(coord)
		deg = int(coord)
		min = int( (float(coord) - deg) * 60 )
		sec = int( round( float( ( (float(coord) - deg) * 60 ) - min) * 60.0 ) )
		return "%s°%s'%s\" %s" % (deg,min,sec,sign)
		
	def lon2str( self, coord ):
		sign=self.label["east"]
		if coord < 0.0:
			sign=self.label["west"]
			coord = abs(coord)
		deg = int(coord)
		min = int( (float(coord) - deg) * 60 )
		sec = int( round( float( ( (float(coord) - deg) * 60 ) - min) * 60.0 ) )
		return "%s°%s'%s\" %s" % (deg,min,sec,sign)
	
	#decimal hour to minutes and seconds
	def decHour( self , input ):
		hours=int(input)
		mands=(input-hours)*60.0
		mands=round(mands,5)
		minutes=int(mands)
		seconds=int(round((mands-minutes)*60))
		return [hours,minutes,seconds]
		
	#join hour, minutes, seconds, timezone integere to hour float
	def decHourJoin( self , inH , inM , inS ):
		dh = float(inH)
		dm = float(inM)/60
		ds = float(inS)/3600
		output = dh + dm + ds
		return output
		
	#decimal timezone string
	def decTzStr( self, tz ):
		if tz > 0:
			h = int(tz)
			m = int((float(tz)-float(h))*float(60))
			return " [+%(#1)02d:%(#2)02d]" % {'#1':h,'#2':m}
		else:
			h = int(tz)
			m = int((float(tz)-float(h))*float(60))/-1
			return " [-%(#1)02d:%(#2)02d]" % {'#1':h/-1,'#2':m}

	#degree difference
	def degreeDiff( self , a , b ):
		out=float()
		if a > b:
			out=a-b
		if a < b:
			out=b-a
		if out > 180.0:
			out=360.0-out
		return out

	#decimal to degrees (a°b"c')
	def dec2deg( self , dec , type="3"):
		dec=float(dec)
		a=int(dec)
		a_new=(dec-float(a)) * 60.0
		b_rounded = int(round(a_new))
		b=int(a_new)
		c=int(round((a_new-float(b))*60.0))
		if type=="3":
			out = '%(#1)02d&#176;%(#2)02d&#34;%(#3)02d&#39;' % {'#1':a,'#2':b, '#3':c}
		elif type=="2":
			out = '%(#1)02d&#176;%(#2)02d' % {'#1':a,'#2':b_rounded}
		elif type=="1":
			out = '%(#1)02d&#176;' % {'#1':a}
		return str(out)
	
	#draw svg aspects: ring, aspect ring, degreeA degreeB
	def drawAspect( self , r , ar , degA , degB , color):
			offset = (int(self.houses_degree_ut[6]) / -1) + int(degA)
			x1 = self.sliceToX( 0 , ar , offset ) + (r-ar)
			y1 = self.sliceToY( 0 , ar , offset ) + (r-ar)
			offset = (int(self.houses_degree_ut[6]) / -1) + int(degB)
			x2 = self.sliceToX( 0 , ar , offset ) + (r-ar)
			y2 = self.sliceToY( 0 , ar , offset ) + (r-ar)
			out = '			<line x1="'+str(x1)+'" y1="'+str(y1)+'" x2="'+str(x2)+'" y2="'+str(y2)+'" style="stroke: '+color+'; stroke-width: 1; stroke-opacity: .9;"/>\n'
			return out
	
	def sliceToX( self , slice , r, offset):
		plus = (math.pi * offset) / 180
		radial = ((math.pi/6) * slice) + plus
		return r * (math.cos(radial)+1)
	
	def sliceToY( self , slice , r, offset):
		plus = (math.pi * offset) / 180
		radial = ((math.pi/6) * slice) + plus
		return r * ((math.sin(radial)/-1)+1)
	
	def zodiacSlice( self , num , r , style,  type):
		#pie slices
		if db.astrocfg["houses_system"] == "G":
			offset = 360 - self.houses_degree_ut[18]
		else:
			offset = 360 - self.houses_degree_ut[6]
		#check transit
		if self.type == "Transit":
			dropin=0
		else:
			dropin=self.c1		
		slice = '<path d="M' + str(r) + ',' + str(r) + ' L' + str(dropin + self.sliceToX(num,r-dropin,offset)) + ',' + str( dropin + self.sliceToY(num,r-dropin,offset)) + ' A' + str(r-dropin) + ',' + str(r-dropin) + ' 0 0,0 ' + str(dropin + self.sliceToX(num+1,r-dropin,offset)) + ',' + str(dropin + self.sliceToY(num+1,r-dropin,offset)) + ' z" style="' + style + '"/>'
		#symbols
		offset = offset + 15
		#check transit
		if self.type == "Transit":
			dropin=54
		else:
			dropin=18+self.c1
		sign = '<g transform="translate(-16,-16)"><use x="' + str(dropin + self.sliceToX(num,r-dropin,offset)) + '" y="' + str(dropin + self.sliceToY(num,r-dropin,offset)) + '" xlink:href="#' + type + '" /></g>\n'
		return slice + '\n' + sign
	
	def makeZodiac( self , r ):
		output = ""
		for i in range(len(self.zodiac)):
			output = output + self.zodiacSlice( i , r , "fill:" + self.colors["zodiac_bg_%s"%(i)] + "; fill-opacity: 0.5;" , self.zodiac[i]) + '\n'
		return output
		
	def makeHouses( self , r ):
		path = ""
		if db.astrocfg["houses_system"] == "G":
			xr = 36
		else:
			xr = 12
		for i in range(xr):
			#check transit
			if self.type == "Transit":
				dropin=160
				roff=72
				t_roff=36
			else:
				dropin=self.c3
				roff=self.c1
				
			#offset is negative desc houses_degree_ut[6]
			offset = (int(self.houses_degree_ut[xr/2]) / -1) + int(self.houses_degree_ut[i])
			x1 = self.sliceToX( 0 , (r-dropin) , offset ) + dropin
			y1 = self.sliceToY( 0 , (r-dropin) , offset ) + dropin
			x2 = self.sliceToX( 0 , r-roff , offset ) + roff
			y2 = self.sliceToY( 0 , r-roff , offset ) + roff
			
			if i < (xr-1):		
				text_offset = offset + int(self.degreeDiff( self.houses_degree_ut[(i+1)], self.houses_degree_ut[i] ) / 2 )
			else:
				text_offset = offset + int(self.degreeDiff( self.houses_degree_ut[0], self.houses_degree_ut[(xr-1)] ) / 2 )

			#mc, asc, dsc, ic
			if i == 0:
				linecolor=self.planets[23]['color']
			elif i == 9:
				linecolor=self.planets[24]['color']	
			elif i == 6:
				linecolor=self.planets[25]['color']
			elif i == 3:
				linecolor=self.planets[26]['color']
			else:
				linecolor=self.colors['houses_radix_line']

			#transit houses lines
			if self.type == "Transit":
				#degrees for point zero
				zeropoint = 360 - self.houses_degree_ut[6]
				t_offset = zeropoint + self.t_houses_degree_ut[i]
				if t_offset > 360:
					t_offset = t_offset - 360
				t_x1 = self.sliceToX( 0 , (r-t_roff) , t_offset ) + t_roff
				t_y1 = self.sliceToY( 0 , (r-t_roff) , t_offset ) + t_roff
				t_x2 = self.sliceToX( 0 , r , t_offset )
				t_y2 = self.sliceToY( 0 , r , t_offset )
				if i < 11:		
					t_text_offset = t_offset + int(self.degreeDiff( self.t_houses_degree_ut[(i+1)], self.t_houses_degree_ut[i] ) / 2 )
				else:
					t_text_offset = t_offset + int(self.degreeDiff( self.t_houses_degree_ut[0], self.t_houses_degree_ut[11] ) / 2 )
				#linecolor
				if i is 0 or i is 9 or i is 6 or i is 3:
					t_linecolor=linecolor
				else:
					t_linecolor = self.colors['houses_transit_line']			
				xtext = self.sliceToX( 0 , (r-8) , t_text_offset ) + 8
				ytext = self.sliceToY( 0 , (r-8) , t_text_offset ) + 8
				path = path + '<text style="fill: #00f; fill-opacity: .4; font-size: 14px"><tspan x="'+str(xtext-3)+'" y="'+str(ytext+3)+'">'+str(i+1)+'</tspan></text>\n'
				path = path + '<line x1="'+str(t_x1)+'" y1="'+str(t_y1)+'" x2="'+str(t_x2)+'" y2="'+str(t_y2)+'" style="stroke: '+t_linecolor+'; stroke-width: 2px; stroke-opacity:.3;"/>\n'				
				
			#if transit			
			if self.type == "Transit":
				dropin=84
			elif db.astrocfg["chartview"] == "european":
				dropin=100
			else:		
				dropin=48
				
			xtext = self.sliceToX( 0 , (r-dropin) , text_offset ) + dropin #was 132
			ytext = self.sliceToY( 0 , (r-dropin) , text_offset ) + dropin #was 132
			path = path + '<line x1="'+str(x1)+'" y1="'+str(y1)+'" x2="'+str(x2)+'" y2="'+str(y2)+'" style="stroke: '+linecolor+'; stroke-width: 2px; stroke-dasharray:3,2; stroke-opacity:.4;"/>\n'
			path = path + '<text style="fill: #f00; fill-opacity: .6; font-size: 14px"><tspan x="'+str(xtext-3)+'" y="'+str(ytext+3)+'">'+str(i+1)+'</tspan></text>\n'
						
		return path
	
	def makePlanets( self , r ):
		
		planets_degut={}
		
		diff=range(len(self.planets))
		for i in range(len(self.planets)):
			if self.planets[i]['visible'] == 1:
				#list of planets sorted by degree				
				planets_degut[self.planets_degree_ut[i]]=i
			
			#element: get extra points if planet is in own zodiac
			pz = self.planets[i]['zodiac_relation']
			cz = self.planets_sign[i]
			extrapoints = 0
			if pz != -1:
				for e in range(len(pz.split(','))):
					if int(pz.split(',')[e]) == int(cz):
						extrapoints = 10

			#calculate element points for all planets
			ele = self.zodiac_element[self.planets_sign[i]]			
			if ele == "fire":
				self.fire = self.fire + self.planets[i]['element_points'] + extrapoints
			elif ele == "earth":
				self.earth = self.earth + self.planets[i]['element_points'] + extrapoints
			elif ele == "air":
				self.air = self.air + self.planets[i]['element_points'] + extrapoints
			elif ele == "water":
				self.water = self.water + self.planets[i]['element_points'] + extrapoints
				
		output = ""	
		keys = planets_degut.keys()
		keys.sort()
		switch=0
		
		planets_degrouped = {}
		groups = []
		planets_by_pos = range(len(planets_degut))
		planet_drange = 3.4
		#get groups closely together
		group_open=False
		for e in range(len(keys)):
			i=planets_degut[keys[e]]
			#get distances between planets
			if e == 0:
				prev = self.planets_degree_ut[planets_degut[keys[-1]]]
				next = self.planets_degree_ut[planets_degut[keys[1]]]
			elif e == (len(keys)-1):
				prev = self.planets_degree_ut[planets_degut[keys[e-1]]]
				next = self.planets_degree_ut[planets_degut[keys[0]]]	
			else:
				prev = self.planets_degree_ut[planets_degut[keys[e-1]]]
				next = self.planets_degree_ut[planets_degut[keys[e+1]]]
			diffa=self.degreeDiff(prev,self.planets_degree_ut[i])
			diffb=self.degreeDiff(next,self.planets_degree_ut[i])
			planets_by_pos[e]=[i,diffa,diffb]
			#print "%s %s %s" % (self.planets[i]['label'],diffa,diffb)
			if (diffb < planet_drange):
				if group_open:
					groups[-1].append([e,diffa,diffb,self.planets[planets_degut[keys[e]]]["label"]])
				else:
					group_open=True
					groups.append([])
					groups[-1].append([e,diffa,diffb,self.planets[planets_degut[keys[e]]]["label"]])
			else:
				if group_open:
					groups[-1].append([e,diffa,diffb,self.planets[planets_degut[keys[e]]]["label"]])				
				group_open=False	
		
		def zero(x): return 0
		planets_delta = map(zero,range(len(self.planets)))

		#print groups
		#print planets_by_pos
		for a in range(len(groups)):
			#Two grouped planets			
			if len(groups[a]) == 2:
				next_to_a = groups[a][0][0]-1
				if groups[a][1][0] == (len(planets_by_pos)-1):
					next_to_b = 0
				else:
					next_to_b = groups[a][1][0]+1
				#if both planets have room
				if (groups[a][0][1] > (2*planet_drange))&(groups[a][1][2] > (2*planet_drange)):
					planets_delta[groups[a][0][0]]=-(planet_drange-groups[a][0][2])/2
					planets_delta[groups[a][1][0]]=+(planet_drange-groups[a][0][2])/2
				#if planet a has room
				elif (groups[a][0][1] > (2*planet_drange)):
					planets_delta[groups[a][0][0]]=-planet_drange
				#if planet b has room
				elif (groups[a][1][2] > (2*planet_drange)):
					planets_delta[groups[a][1][0]]=+planet_drange
				
				#if planets next to a and b have room move them
				elif (planets_by_pos[next_to_a][1] > (2.4*planet_drange))&(planets_by_pos[next_to_b][2] > (2.4*planet_drange)):
					planets_delta[(next_to_a)]=(groups[a][0][1]-planet_drange*2)
					planets_delta[groups[a][0][0]]=-planet_drange*.5				
					planets_delta[next_to_b]=-(groups[a][1][2]-planet_drange*2)
					planets_delta[groups[a][1][0]]=+planet_drange*.5	
					
				#if planet next to a has room move them
				elif (planets_by_pos[next_to_a][1] > (2*planet_drange)):
					planets_delta[(next_to_a)]=(groups[a][0][1]-planet_drange*2.5)
					planets_delta[groups[a][0][0]]=-planet_drange*1.2

				#if planet next to b has room move them
				elif (planets_by_pos[next_to_b][2] > (2*planet_drange)):
					planets_delta[next_to_b]=-(groups[a][1][2]-planet_drange*2.5)
					planets_delta[groups[a][1][0]]=+planet_drange*1.2

			#Three grouped planets or more
			xl=len(groups[a])		
			if xl >= 3:
				
				available = groups[a][0][1]
				for f in range(xl):
					available += groups[a][f][2]
				need = (3*planet_drange)+(1.2*(xl-1)*planet_drange)
				leftover = available - need
				xa=groups[a][0][1]
				xb=groups[a][(xl-1)][2]
				
				#center
				if (xa > (need*.5)) & (xb > (need*.5)):
					startA = xa - (need*.5)
				#position relative to next planets
				else:
					startA=(leftover/(xa+xb))*xa
					startB=(leftover/(xa+xb))*xb
			
				if available > need:
					planets_delta[groups[a][0][0]]=startA-groups[a][0][1]+(1.5*planet_drange)
					for f in range(xl-1):
						planets_delta[groups[a][(f+1)][0]]=1.2*planet_drange+planets_delta[groups[a][f][0]]-groups[a][f][2]


		for e in range(len(keys)):
			i=planets_degut[keys[e]]

			#coordinates			
			if self.type == "Transit":
				if 22 < i < 27:
					rplanet = 76
				elif switch == 1:
					rplanet=110
					switch = 0
				else:
					rplanet=130
					switch = 1				
			else:
				#if 22 < i < 27 it is asc,mc,dsc,ic (angles of chart)
				#put on special line (rplanet is range from outer ring)
				amin,bmin,cmin=0,0,0				
				if db.astrocfg["chartview"] == "european":
					amin=74-10
					bmin=94-10
					cmin=40-10
				
				if 22 < i < 27:
					rplanet = 40-cmin
				elif switch == 1:
					rplanet=74-amin
					switch = 0
				else:
					rplanet=94-bmin
					switch = 1			
				
			rtext=45
			if db.astrocfg['houses_system'] == "G":
				offset = (int(self.houses_degree_ut[18]) / -1) + int(self.planets_degree_ut[i])
			else:
				offset = (int(self.houses_degree_ut[6]) / -1) + int(self.planets_degree_ut[i]+planets_delta[e])
				trueoffset = (int(self.houses_degree_ut[6]) / -1) + int(self.planets_degree_ut[i])
			planet_x = self.sliceToX( 0 , (r-rplanet) , offset ) + rplanet
			planet_y = self.sliceToY( 0 , (r-rplanet) , offset ) + rplanet
			if self.type == "Transit":
				scale=0.8
			elif db.astrocfg["chartview"] == "european":
				scale=0.8
				#line1
				x1=self.sliceToX( 0 , (r-self.c3) , trueoffset ) + self.c3
				y1=self.sliceToY( 0 , (r-self.c3) , trueoffset ) + self.c3
				x2=self.sliceToX( 0 , (r-rplanet-30) , trueoffset ) + rplanet + 30
				y2=self.sliceToY( 0 , (r-rplanet-30) , trueoffset ) + rplanet + 30
				color=self.planets[i]["color"]
				output += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke-width:1px;stroke:%s;stroke-opacity:.3;"/>\n' % (x1,y1,x2,y2,color)
				#line2
				x1=self.sliceToX( 0 , (r-rplanet-30) , trueoffset ) + rplanet + 30
				y1=self.sliceToY( 0 , (r-rplanet-30) , trueoffset ) + rplanet + 30
				x2=self.sliceToX( 0 , (r-rplanet-10) , offset ) + rplanet + 10
				y2=self.sliceToY( 0 , (r-rplanet-10) , offset ) + rplanet + 10
				output += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke-width:1px;stroke:%s;stroke-opacity:.5;"/>\n' % (x1,y1,x2,y2,color)
			else:
				scale=1
			#output planet			
			output = output + '<g transform="translate(-'+str(12*scale)+',-'+str(12*scale)+')"><g transform="scale('+str(scale)+')"><use x="' + str(planet_x*(1/scale)) + '" y="' + str(planet_y*(1/scale)) + '" xlink:href="#' + self.planets[i]['name'] + '" /></g></g>\n'
			
		#make transit degut and display planets
		if self.type == "Transit":
			group_offset={}
			t_planets_degut={}
			for i in range(len(self.planets)):
				group_offset[i]=0
				if self.planets[i]['visible'] == 1:
					t_planets_degut[self.t_planets_degree_ut[i]]=i
			t_keys = t_planets_degut.keys()
			t_keys.sort()
			

			#grab closely grouped planets
			groups=[]
			in_group=False
			for e in range(len(t_keys)):
				i_a=t_planets_degut[t_keys[e]]
				if e == (len(t_keys)-1):
					i_b=t_planets_degut[t_keys[0]]
				else:
					i_b=t_planets_degut[t_keys[e+1]]
				
				a=self.t_planets_degree_ut[i_a]
				b=self.t_planets_degree_ut[i_b]
				diff = self.degreeDiff(a,b)
				if diff <= 2.5:
					if in_group:
						groups[-1].append(i_b)
					else:
						groups.append([i_a])
						groups[-1].append(i_b)
						in_group=True
				else:
					in_group=False	
			#loop groups and set degrees display adjustment
			for i in range(len(groups)):
				if len(groups[i]) == 2:
					group_offset[groups[i][0]]=-1.0
					group_offset[groups[i][1]]=1.0
				elif len(groups[i]) == 3:
					group_offset[groups[i][0]]=-1.5
					group_offset[groups[i][1]]=0
					group_offset[groups[i][2]]=1.5
				elif len(groups[i]) == 4:
					group_offset[groups[i][0]]=-2.0
					group_offset[groups[i][1]]=-1.0
					group_offset[groups[i][2]]=1.0
					group_offset[groups[i][3]]=2.0					
			
			switch=0
			for e in range(len(t_keys)):
				i=t_planets_degut[t_keys[e]]
	
				if 22 < i < 27:
					rplanet = 9
				elif switch == 1:
					rplanet=18
					switch = 0
				else:
					rplanet=26
					switch = 1	
				
				zeropoint = 360 - self.houses_degree_ut[6]
				t_offset = zeropoint + self.t_planets_degree_ut[i]
				if t_offset > 360:
					t_offset = t_offset - 360
				planet_x = self.sliceToX( 0 , (r-rplanet) , t_offset ) + rplanet
				planet_y = self.sliceToY( 0 , (r-rplanet) , t_offset ) + rplanet
				output = output + '<g transform="translate(-6,-6)"><g transform="scale(0.5)"><use x="' + str(planet_x*2) + '" y="' + str(planet_y*2) + '" xlink:href="#' + self.planets[i]['name'] + '" /></g></g>\n'
				#transit planet line
				x1 = self.sliceToX( 0 , r+3 , t_offset ) - 3
				y1 = self.sliceToY( 0 , r+3 , t_offset ) - 3
				x2 = self.sliceToX( 0 , r-3 , t_offset ) + 3
				y2 = self.sliceToY( 0 , r-3 , t_offset ) + 3
				output = output + '<line x1="'+str(x1)+'" y1="'+str(y1)+'" x2="'+str(x2)+'" y2="'+str(y2)+'" style="stroke: '+self.planets[i]['color']+'; stroke-width: 1px; stroke-opacity:.8;"/>\n'
				
				#transit planet degree text
				rotate = self.houses_degree_ut[0] - self.t_planets_degree_ut[i]
				textanchor="end"
				t_offset += group_offset[i]
				rtext=-3.0
	
				if -90 > rotate > -270:
					rotate = rotate + 180.0
					textanchor="start"
				if 270 > rotate > 90:
					rotate = rotate - 180.0
					textanchor="start"
	
					
				if textanchor == "end":
					xo=1
				else:
					xo=-1				
				deg_x = self.sliceToX( 0 , (r-rtext) , t_offset + xo ) + rtext
				deg_y = self.sliceToY( 0 , (r-rtext) , t_offset + xo ) + rtext
				degree=int(t_offset)
				output += '<g transform="translate(%s,%s)">' % (deg_x,deg_y)
				output += '<text transform="rotate(%s)" text-anchor="%s' % (rotate,textanchor)
				output += '" style="fill: '+self.planets[i]['color']+'; font-size: 10px;">'+self.dec2deg(self.t_planets_degree[i],type="1")
				output += '</text></g>\n'
			
			#check transit
			if self.type == "Transit":
				dropin=36
			else:
				dropin=0			
			
			#planet line
			x1 = self.sliceToX( 0 , r-(dropin+3) , offset ) + (dropin+3)
			y1 = self.sliceToY( 0 , r-(dropin+3) , offset ) + (dropin+3)
			x2 = self.sliceToX( 0 , (r-(dropin-3)) , offset ) + (dropin-3)
			y2 = self.sliceToY( 0 , (r-(dropin-3)) , offset ) + (dropin-3)
			output = output + '<line x1="'+str(x1)+'" y1="'+str(y1)+'" x2="'+str(x2)+'" y2="'+str(y2)+'" style="stroke: '+self.planets[i]['color']+'; stroke-width: 2px; stroke-opacity:.6;"/>\n'
			
			#check transit
			if self.type == "Transit":
				dropin=160
			else:
				dropin=120
				
			x1 = self.sliceToX( 0 , r-dropin , offset ) + dropin
			y1 = self.sliceToY( 0 , r-dropin , offset ) + dropin
			x2 = self.sliceToX( 0 , (r-(dropin-3)) , offset ) + (dropin-3)
			y2 = self.sliceToY( 0 , (r-(dropin-3)) , offset ) + (dropin-3)
			output = output + '<line x1="'+str(x1)+'" y1="'+str(y1)+'" x2="'+str(x2)+'" y2="'+str(y2)+'" style="stroke: '+self.planets[i]['color']+'; stroke-width: 2px; stroke-opacity:.6;"/>\n'

		return output

	def makePatterns( self ):
		"""
		* Stellium: At least four planets linked together in a series of continuous conjunctions.
    	* Grand trine: Three trine aspects together.
		* Grand cross: Two pairs of opposing planets squared to each other.
		* T-Square: Two planets in opposition squared to a third. 
		* Yod: Two qunicunxes together joined by a sextile. 
		"""
		conj = {} #0
		opp = {} #10
		sq = {} #5
		tr = {} #6
		qc = {} #9
		sext = {} #3
		for i in range(len(self.planets)):
			a=self.planets_degree_ut[i]
			qc[i]={}
			sext[i]={}
			opp[i]={}
			sq[i]={}
			tr[i]={}
			conj[i]={}
			#skip some points
			n = self.planets[i]['name']
			if n == 'earth' or n == 'true node' or n == 'osc. apogee' or n == 'intp. apogee' or n == 'intp. perigee':
				continue
			if n == 'Dsc' or n == 'Ic':
				continue
			for j in range(len(self.planets)):
				#skip some points
				n = self.planets[j]['name']
				if n == 'earth' or n == 'true node' or n == 'osc. apogee' or n == 'intp. apogee' or n == 'intp. perigee':
					continue	
				if n == 'Dsc' or n == 'Ic':
					continue
				b=self.planets_degree_ut[j]
				delta=float(self.degreeDiff(a,b))
				#check for opposition
				xa = float(self.aspects[10]['degree']) - float(self.aspects[10]['orb'])
				xb = float(self.aspects[10]['degree']) + float(self.aspects[10]['orb'])
				if( xa <= delta <= xb ):
					opp[i][j]=True	
				#check for conjunction
				xa = float(self.aspects[0]['degree']) - float(self.aspects[0]['orb'])
				xb = float(self.aspects[0]['degree']) + float(self.aspects[0]['orb'])
				if( xa <= delta <= xb ):
					conj[i][j]=True					
				#check for squares
				xa = float(self.aspects[5]['degree']) - float(self.aspects[5]['orb'])
				xb = float(self.aspects[5]['degree']) + float(self.aspects[5]['orb'])
				if( xa <= delta <= xb ):
					sq[i][j]=True			
				#check for qunicunxes
				xa = float(self.aspects[9]['degree']) - float(self.aspects[9]['orb'])
				xb = float(self.aspects[9]['degree']) + float(self.aspects[9]['orb'])
				if( xa <= delta <= xb ):
					qc[i][j]=True
				#check for sextiles
				xa = float(self.aspects[3]['degree']) - float(self.aspects[3]['orb'])
				xb = float(self.aspects[3]['degree']) + float(self.aspects[3]['orb'])
				if( xa <= delta <= xb ):
					sext[i][j]=True
							
		yot={}
		#check for double qunicunxes
		for k,v in qc.iteritems():
			if len(qc[k]) >= 2:
				#check for sextile
				for l,w in qc[k].iteritems():
					for m,x in qc[k].iteritems():
						if sext[l].has_key(m):
							if l > m:
								yot['%s,%s,%s' % (k,m,l)] = [k,m,l]
							else:
								yot['%s,%s,%s' % (k,l,m)] = [k,l,m]
		tsquare={}
		#check for opposition
		for k,v in opp.iteritems():
			if len(opp[k]) >= 1:
				#check for square
				for l,w in opp[k].iteritems():
						for a,b in sq.iteritems():
							if sq[a].has_key(k) and sq[a].has_key(l):
								#print 'got tsquare %s %s %s' % (a,k,l)
								if k > l:
									tsquare['%s,%s,%s' % (a,l,k)] = '%s => %s, %s' % (
										self.planets[a]['label'],self.planets[l]['label'],self.planets[k]['label'])
								else:
									tsquare['%s,%s,%s' % (a,k,l)] = '%s => %s, %s' % (
										self.planets[a]['label'],self.planets[k]['label'],self.planets[l]['label'])
		stellium={}
		#check for 4 continuous conjunctions	
		for k,v in conj.iteritems():
			if len(conj[k]) >= 1:
				#first conjunction
				for l,m in conj[k].iteritems():
					if len(conj[l]) >= 1:
						for n,o in conj[l].iteritems():
							#skip 1st conj
							if n == k:
								continue
							if len(conj[n]) >= 1:
								#third conjunction
								for p,q in conj[n].iteritems():
									#skip first and second conj
									if p == k or p == n:
										continue
									if len(conj[p]) >= 1:										
										#fourth conjunction
										for r,s in conj[p].iteritems():
											#skip conj 1,2,3
											if r == k or r == n or r == p:
												continue
											
											l=[k,n,p,r]
											l.sort()
											stellium['%s %s %s %s' % (l[0],l[1],l[2],l[3])]='%s %s %s %s' % (
												self.planets[l[0]]['label'],self.planets[l[1]]['label'],
												self.planets[l[2]]['label'],self.planets[l[3]]['label'])
		#print yots
		out='<g transform="translate(-30,380)">'
		if len(yot) >= 1:
			y=0
			for k,v in yot.iteritems():
				out += '<text y="%s" style="fill:#000; font-size: 12px;">%s</text>\n' % (y,_("Yot"))
				
				#first planet symbol
				out += '<g transform="translate(20,%s)">' % (y)
				out += '<use transform="scale(0.4)" x="0" y="-20" xlink:href="#%s" /></g>\n' % (
					self.planets[yot[k][0]]['name'])
				
				#second planet symbol
				out += '<g transform="translate(30,%s)">'  % (y)
				out += '<use transform="scale(0.4)" x="0" y="-20" xlink:href="#%s" /></g>\n' % (
					self.planets[yot[k][1]]['name'])

				#third planet symbol
				out += '<g transform="translate(40,%s)">'  % (y)
				out += '<use transform="scale(0.4)" x="0" y="-20" xlink:href="#%s" /></g>\n' % (
					self.planets[yot[k][2]]['name'])
				
				y=y+14
		#finalize
		out += '</g>'		
		#return out
		return ''
	
	def makeAspects( self , r , ar ):
		out=""
		for i in range(len(self.planets)):
			start=self.planets_degree_ut[i]
			for x in range(i):
				end=self.planets_degree_ut[x]
				diff=float(self.degreeDiff(start,end))
				#loop orbs
				if (self.planets[i]['visible_aspect_line'] == 1) & (self.planets[x]['visible_aspect_line'] == 1):	
					for z in range(len(self.aspects)):
						if	( float(self.aspects[z]['degree']) - float(self.aspects[z]['orb']) ) <= diff <= ( float(self.aspects[z]['degree']) + float(self.aspects[z]['orb']) ):
							#check if we want to display this aspect
							if self.aspects[z]['visible'] == 1:					
								out = out + self.drawAspect( r , ar , self.planets_degree_ut[i] , self.planets_degree_ut[x] , self.colors["aspect_%s" %(self.aspects[z]['degree'])] )
		return out
	
	def makeAspectsTransit( self , r , ar ):
		out = ""
		self.atgrid=[]
		for i in range(len(self.planets)):
			start=self.planets_degree_ut[i]
			for x in range(i+1):
				end=self.t_planets_degree_ut[x]
				diff=float(self.degreeDiff(start,end))
				#loop orbs
				if (self.planets[i]['visible'] == 1) & (self.planets[x]['visible'] == 1):	
					for z in range(len(self.aspects)):
						#check for personal planets and determine orb
						if 0 <= i <= 4 or 0 <= x <= 4:
							orb_before = 1.0
						else:
							orb_before = 2.0
						#check if we want to display this aspect	
						if	( float(self.aspects[z]['degree']) - orb_before ) <= diff <= ( float(self.aspects[z]['degree']) + 1.0 ):
							if self.aspects[z]['visible'] == 1:
								out = out + self.drawAspect( r , ar , self.planets_degree_ut[i] , self.t_planets_degree_ut[x] , self.colors["aspect_%s" %(self.aspects[z]['degree'])] )		
							#aspect grid dictionary
							if self.aspects[z]['visible_grid'] == 1:
								self.atgrid.append({})
								self.atgrid[-1]['p1']=i
								self.atgrid[-1]['p2']=x
								self.atgrid[-1]['aid']=z
								self.atgrid[-1]['diff']=diff
		return out
	
	def makeAspectTransitGrid( self , r ):
		out = '<g transform="translate(500,310)">'
		out += '<text y="-15" x="0" style="fill:#000; font-size: 12px;">%s</text>\n' % (_("Planets in Transit"))
		line = 0
		nl = 0
		for i in range(len(self.atgrid)):
			if i == 12:
				nl = 100
				if len(self.atgrid) > 24:
					line = -1 * ( len(self.atgrid) - 24) * 14
				else:
					line = 0
			out += '<g transform="translate(%s,%s)">' % (nl,line)
			#first planet symbol
			out += '<use transform="scale(0.4)" x="0" y="3" xlink:href="#%s" />\n' % (
				self.planets[self.atgrid[i]['p2']]['name'])
			#aspect symbol
			out += '<use  x="15" y="0" xlink:href="#orb%s" />\n' % (
				self.aspects[self.atgrid[i]['aid']]['degree'])
			#second planet symbol
			out += '<g transform="translate(30,0)">'
			out += '<use transform="scale(0.4)" x="0" y="3" xlink:href="#%s" />\n' % (
				self.planets[self.atgrid[i]['p1']]['name'])
			out += '</g>'
			#difference in degrees
			out += '<text y="8" x="45" style="fill:#000; font-size: 10px;">%s</text>' % (
				self.dec2deg(self.atgrid[i]['diff']) )
			#line
			out += '</g>'
			line = line + 14		
		out += '</g>'
		return out
	
	def makeAspectGrid( self , r ):
		out=""
		style='stroke:#000; stroke-width: 1px; stroke-opacity:.6; fill:none'
		xindent=380
		yindent=468
		box=14
		revr=range(len(self.planets))
		revr.reverse()
		for a in revr:
			if self.planets[a]['visible_aspect_grid'] == 1:
				start=self.planets_degree_ut[a]
				#first planet 
				out = out + '<rect x="'+str(xindent)+'" y="'+str(yindent)+'" width="'+str(box)+'" height="'+str(box)+'" style="'+style+'"/>\n'
				out = out + '<use transform="scale(0.4)" x="'+str((xindent+2)*2.5)+'" y="'+str((yindent+1)*2.5)+'" xlink:href="#'+self.planets[a]['name']+'" />\n'
				xindent = xindent + box
				yindent = yindent - box
				revr2=range(a)
				revr2.reverse()
				xorb=xindent
				yorb=yindent + box
				for b in revr2:
					if self.planets[b]['visible_aspect_grid'] == 1:
						end=self.planets_degree_ut[b]
						diff=self.degreeDiff(start,end)
						out = out + '<rect x="'+str(xorb)+'" y="'+str(yorb)+'" width="'+str(box)+'" height="'+str(box)+'" style="'+style+'"/>\n'
						xorb=xorb+box
						for z in range(len(self.aspects)):
							if	( float(self.aspects[z]['degree']) - float(self.aspects[z]['orb']) ) <= diff <= ( float(self.aspects[z]['degree']) + float(self.aspects[z]['orb']) ) and self.aspects[z]['visible_grid'] == 1:
									out = out + '<use  x="'+str(xorb-box+1)+'" y="'+str(yorb+1)+'" xlink:href="#orb'+str(self.aspects[z]['degree'])+'" />\n'
		return out

	def makeElements( self , r ):
		total = self.fire + self.earth + self.air + self.water
		pf = int(round(100*self.fire/total))
		pe = int(round(100*self.earth/total))
		pa = int(round(100*self.air/total))
		pw = int(round(100*self.water/total))
		out = '<g transform="translate(-30,79)">\n'
		out = out + '<text y="0" style="fill:#ff6600; font-size: 10px;">'+self.label['fire']+'  '+str(pf)+'%</text>\n'
		out = out + '<text y="12" style="fill:#6a2d04; font-size: 10px;">'+self.label['earth']+' '+str(pe)+'%</text>\n'
		out = out + '<text y="24" style="fill:#6f76d1; font-size: 10px;">'+self.label['air']+'   '+str(pa)+'%</text>\n'
		out = out + '<text y="36" style="fill:#630e73; font-size: 10px;">'+self.label['water']+' '+str(pw)+'%</text>\n'		
		out = out + '</g>\n'
		return out
		
	def makePlanetGrid( self ):
		out = '<g transform="translate(510,-40)">'
		#loop over all planets
		li=10
		offset=0
		for i in range(len(self.planets)):
			if i == 27:
				li = 10
				offset = -120
			if self.planets[i]['visible'] == 1:
				#start of line				
				out = out + '<g transform="translate(%s,%s)">' % (offset,li)
				#planet text
				out = out + '<text text-anchor="end" style="fill:#000; font-size: 10px;">'+str(self.planets[i]['label'])+'</text>'
				#planet symbol
				out = out + '<g transform="translate(5,-8)"><use transform="scale(0.4)" xlink:href="#'+self.planets[i]['name']+'" /></g>'								
				#planet degree				
				out = out + '<text text-anchor="start" x="19" style="fill:#000; font-size: 10px;">'+self.dec2deg(self.planets_degree[i])+'</text>'		
				#zodiac
				out = out + '<g transform="translate(60,-8)"><use transform="scale(0.3)" xlink:href="#'+self.zodiac[self.planets_sign[i]]+'" /></g>'				
				#planet retrograde
				if self.planets_retrograde[i]:
					out = out + '<g transform="translate(74,-6)"><use transform="scale(.5)" xlink:href="#retrograde" /></g>'				

				#end of line
				out = out + '</g>\n'
				#offset between lines
				li = li + 14	
		
		out = out + '</g>\n'
		return out
	
	def makeHousesGrid( self ):
		out = '<g transform="translate(610,-40)">'
		li=10
		for i in range(12):
			if i < 9:
				cusp = '&#160;&#160;'+str(i+1)
			else:
				cusp = str(i+1)
			out += '<g transform="translate(0,'+str(li)+')">'
			out += '<text text-anchor="end" x="40" style="fill:#000; font-size: 10px;">%s %s:</text>' % (self.label['cusp'],cusp)			
			out += '<g transform="translate(40,-8)"><use transform="scale(0.3)" xlink:href="#'+self.zodiac[self.houses_sign[i]]+'" /></g>'
			out += '<text x="53" style="fill:#000; font-size: 10px;"> %s</text>' % (self.dec2deg(self.houses_degree[i]))
			out += '</g>\n'
			li = li + 14
		out += '</g>\n'
		return out
	
	"""Export/Import Functions related to openastro.org

	def exportOAC(filename)
	def importOAC(filename)
	def importOroboros(filename)
	
	"""
	
	def exportOAC(self,filename):
		template="""<?xml version='1.0' encoding='UTF-8'?>
<openastrochart>
	<name>$name</name>
	<datetime>$datetime</datetime>
	<location>$location</location>
	<altitude>$altitude</altitude>
	<latitude>$latitude</latitude>
	<longitude>$longitude</longitude>
	<countrycode>$countrycode</countrycode>
	<timezone>$timezone</timezone>
	<geonameid>$geonameid</geonameid>
	<timezonestr>$timezonestr</timezonestr>
	<extra>$extra</extra>
</openastrochart>"""
		h,m,s = self.decHour(openAstro.hour)
		dt=datetime.datetime(openAstro.year,openAstro.month,openAstro.day,h,m,s)
		substitute={}
		substitute['name']=self.name
		substitute['datetime']=dt.strftime("%Y-%m-%d %H:%M:%S")
		substitute['location']=self.location
		substitute['altitude']=self.altitude
		substitute['latitude']=self.geolat
		substitute['longitude']=self.geolon
		substitute['countrycode']=self.countrycode
		substitute['timezone']=self.timezone
		substitute['timezonestr']=self.timezonestr
		substitute['geonameid']=self.geonameid
		substitute['extra']=''
		#write the results to the template
		output=Template(template).substitute(substitute)
		f=open(filename,"w")
		f.write(output)
		f.close()
		dprint("exporting OAC: %s" % filename)
		return
	
	def importOAC(self, filename):
		r=importfile.getOAC(filename)[0]
		dt = datetime.datetime.strptime(r['datetime'],"%Y-%m-%d %H:%M:%S")
		self.name=r['name']
		self.countrycode=r['countrycode']
		self.altitude=int(r['altitude'])
		self.geolat=float(r['latitude'])
		self.geolon=float(r['longitude'])
		self.timezone=float(r['timezone'])
		self.geonameid=r['geonameid']
		if "timezonestr" in r:
			self.timezonestr=r['timezonestr']
		else:
			self.timezonestr=db.gnearest(self.geolat,self.geolon)['timezonestr']
		self.location=r['location']
		self.year=dt.year
		self.month=dt.month
		self.day=dt.day
		self.hour=self.decHourJoin(dt.hour,dt.minute,dt.second)
		#Make locals
		self.utcToLocal()
		#debug print
		dprint('importOAC: %s' % filename)
		return
	
	def importOroboros(self, filename):
		r=importfile.getOroboros(filename)[0]
		#naive local datetime
		naive = datetime.datetime.strptime(r['datetime'],"%Y-%m-%d %H:%M:%S")
		#aware datetime object
		dt = zonetab.stdtime(r['zoneinfo'], naive.year, naive.month, naive.day, naive.hour, naive.minute, naive.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()
		
		#process latitude/longitude
		deg,type,min,sec = r['latitude'].split(":")
		lat = float(deg)+( float(min) / 60.0 )+( float(sec) / 3600.0 )
		if type == "S":
			lat = decimal / -1.0
		deg,type,min,sec = r['longitude'].split(":")
		lon = float(deg)+( float(min) / 60.0 )+( float(sec) / 3600.0 )
		if type == "W":
			lon = decimal / -1.0			
		
		geon = db.gnearest(float(lat),float(lon))
		self.timezonestr=geon['timezonestr']
		self.geonameid=geon['geonameid']		
		self.name=r['name']
		self.countrycode=''
		self.altitude=int(r['altitude'])
		self.geolat=lat
		self.geolon=lon
		self.timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
		self.location='%s, %s' % (r['location'],r['countryname'])
		self.year=dt_utc.year
		self.month=dt_utc.month
		self.day=dt_utc.day
		self.hour=self.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		#Make locals
		self.utcToLocal()
		#debug print
		dprint('importOroboros: UTC: %s file: %s' % (dt_utc,filename))
		return
	
	def importSkylendar(self, filename):
		r = importfile.getSkylendar(filename)[0]
		
		#naive local datetime
		naive = datetime.datetime(int(r['year']),int(r['month']),int(r['day']),int(r['hour']),int(r['minute']))
		#aware datetime object
		dt = zonetab.stdtime(r['zoneinfofile'], naive.year, naive.month, naive.day, naive.hour, naive.minute, naive.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()

		geon = db.gnearest(float(r['latitude']),float(r['longitude']))
		self.timezonestr=geon['timezonestr']
		self.geonameid=geon['geonameid']				
		self.name=r['name']
		self.countrycode=''
		self.altitude=25
		self.geolat=float(r['latitude'])
		self.geolon=float(r['longitude'])
		self.timezone=float(r['timezone'])
		self.location='%s, %s' % (r['location'],r['countryname'])
		self.year=dt_utc.year
		self.month=dt_utc.month
		self.day=dt_utc.day
		self.hour=self.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		#Make locals
		self.utcToLocal()		
		return	

	def importAstrolog32(self, filename):
		r = importfile.getAstrolog32(filename)[0]

		#timezone string
		timezone_str = zonetab.nearest_tz(float(r['latitude']),float(r['longitude']),zonetab.timezones())[2]
		#naive local datetime
		naive = datetime.datetime(int(r['year']),int(r['month']),int(r['day']),int(r['hour']),int(r['minute']),int(r['second']))
		#aware datetime object
		dt = zonetab.stdtime(timezone_str, naive.year, naive.month, naive.day, naive.hour, naive.minute, naive.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()

		geon = db.gnearest(float(r['latitude']),float(r['longitude']))
		self.timezonestr=geon['timezonestr']
		self.geonameid=geon['geonameid']		
		self.name=r['name']
		self.countrycode=''
		self.altitude=25
		self.geolat=float(r['latitude'])
		self.geolon=float(r['longitude'])
		self.timezone=float( (dt.utcoffset().days * 24.0) + (dt.utcoffset().seconds/3600.0) )
		self.location=r['location']
		self.year=dt_utc.year
		self.month=dt_utc.month
		self.day=dt_utc.day
		self.hour=self.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		#Make locals
		self.utcToLocal()		
		return
	
	def importZet8(self, filename):
		h=open(filename)
		f=codecs.EncodedFile(h,"utf-8","latin-1")
		data=[]
		for line in f.readlines():
			s=line.split(";")
			if s[0] == line:
				continue
			
			data.append({})
			data[-1]['name']=s[0].strip()
			day=int( s[1].strip().split('.')[0] )
			month=int( s[1].strip().split('.')[1] )
			year=int( s[1].strip().split('.')[2] )
			hour=int(  s[2].strip().split(':')[0] )
			minute=int( s[2].strip().split(':')[1] )
			if len(s[3].strip()) > 3:
				data[-1]['timezone']=float( s[3].strip().split(":")[0] )
				if data[-1]['timezone'] < 0:
					data[-1]['timezone']-= float( s[3].strip().split(":")[1] ) / 60.0
				else:
					data[-1]['timezone']+= float( s[3].strip().split(":")[1] ) / 60.0
			elif len(s[3].strip()) > 0:
				data[-1]['timezone']=int(s[3].strip())
			else:
				data[-1]['timezone']=0
				
			#substract timezone from date
			dt = datetime.datetime(year,month,day,hour,minute)
			dt = dt - datetime.timedelta(seconds=float(data[-1]['timezone'])*float(3600))
			data[-1]['year'] = dt.year
			data[-1]['month'] = dt.month
			data[-1]['day'] = dt.day
			data[-1]['hour'] =  float(dt.hour) + float(dt.minute/60.0)
			data[-1]['location']=s[4].strip()

			#latitude
			p=s[5].strip()
			if p.find("°") != -1:
				#later version of zet8
				if p.find("S") == -1:
					deg=p.split("°")[0] #\xc2
					min=p[p.find("°")+2:p.find("'")]
					sec=p[p.find("'")+1:p.find('"')]
					data[-1]['latitude']=float(deg)+(float(min)/60.0)
				else:
					deg=p.split("°")[0] #\xc2
					min=p[p.find("°")+2:p.find("'")]
					sec=p[p.find("'")+1:p.find('"')]
					data[-1]['latitude']=( float(deg)+(float(min)/60.0) ) / -1.0				
			else:
				#earlier version of zet8
				if p.find("s") == -1:
					i=p.find("n")
					data[-1]['latitude']=float(p[:i])+(float(p[i+1:])/60.0)
				else:
					i=p.find("s")
					data[-1]['latitude']=( float(p[:i])+(float(p[i+1:])/60.0) ) / -1.0
			#longitude
			p=s[6].strip()
			if p.find("°") != -1:
				#later version of zet8
				if p.find("W") == -1:
					deg=p.split("°")[0] #\xc2
					min=p[p.find("°")+2:p.find("'")]
					sec=p[p.find("'")+1:p.find('"')]
					data[-1]['longitude']=float(deg)+(float(min)/60.0)
				else:
					deg=p.split("°")[0] #\xc2
					min=p[p.find("°")+2:p.find("'")]
					sec=p[p.find("'")+1:p.find('"')]
					data[-1]['longitude']=( float(deg)+(float(min)/60.0) ) / -1.0				
			else:
				#earlier version of zet8
				if p.find("w") == -1:
					i=p.find("e")
					data[-1]['longitude']=float(p[:i])+(float(p[i+1:])/60.0)
				else:
					i=p.find("w")
					data[-1]['longitude']=( float(p[:i])+(float(p[i+1:])/60.0) ) / -1.0
		
		db.importZet8( cfg.peopledb , data )
		dprint('importZet8: database with %s entries: %s' % (len(data),filename))
		f.close()
		return
		
##############
# MAIN CLASS #
##############

#Main GTK Window
class mainWindow:
	def __init__(self):
		#gtktopwindow
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.connect("destroy", lambda w: gtk.main_quit())
		self.window.set_title("OpenAstro.org")
		self.window.set_icon_from_file(cfg.iconWindow)
		self.window.maximize()
		
		self.vbox = gtk.VBox()
		
		#uimanager
		self.uimanager = gtk.UIManager()
		self.ui_mid = self.uimanager.add_ui_from_file(cfg.xml_ui)
		accelgroup = self.uimanager.get_accel_group()
		self.window.add_accel_group(accelgroup)
	
		#actions definitions
		self.actions = [('File', None, _('Chart') ),
								('Quit', gtk.STOCK_QUIT, _("Quit!"), None,'Quit the Program', self.quit_cb),
	                     ('History', None, _('History') ),
	                     ('newChart', gtk.STOCK_NEW, _('New Chart'), None, 'New Chart', self.eventDataNew ),
	                     ('importXML', gtk.STOCK_OPEN, _('Open Chart'), None, 'Open Chart', self.doImport ),								
	                     ('exportXML', gtk.STOCK_SAVE, _('Save Chart'), None, 'Save Chart', self.doExport ),
	                     ('export', gtk.STOCK_SAVE_AS, _('Save as') ),
	                     ('exportPNG', None, _('PNG Image'), None, 'PNG Image', self.doExport ),
	                     ('exportSVG', None, _('SVG Image'), None, 'SVG Image', self.doExport ),
	                     ('exportJPG', None, _('JPG Image'), None, 'JPG Image', self.doExport ),
	                     ('import', None, _('Import') ),
	                     ('importOroboros', None, _('Oroboros (*.xml)'), None, 'Oroboros (*.xml)', self.doImport ),
	                     ('importAstrolog32', None, _('Astrolog (*.dat)'), None, 'Astrolog (*.dat)', self.doImport ),
	                     ('importSkylendar', None, _('Skylendar (*.skif)'), None, 'Skylendar (*.skif)', self.doImport ),
	                     ('importZet8', None, _('Zet8 Dbase (*.zbs)'), None, 'Zet8 Dbase (*.zbs)', self.doImport ),							
								('Print', gtk.STOCK_PRINT, _('Print'), None, 'Print', self.doPrint ),
	                     ('Event', None, _('Event') ),
	                     ('EditEvent', gtk.STOCK_EDIT, _('Edit Event'), None, 'Event Data', self.eventData ),
	                     ('OpenDatabase', gtk.STOCK_HARDDISK, _('Open Database'), None, 'Open Database', self.openDatabase ),
								('QuickOpenDatabase', None, _('Quick Open Database') ),	                     
	                     ('OpenDatabaseFamous', gtk.STOCK_HARDDISK, _('Open Famous People Database'), None, 'Open Database Famous', self.openDatabaseFamous ),
	                     ('Settings', None, _('Settings') ),
	                     ('Special', None, _('Chart Type') ),
	                     ('ZoomRadio', None, _('Zoom') ),
								('Planets', None, _('Planets & Angles'), None, 'Planets & Angles', self.settingsPlanets ),
								('Aspects', None, _('Aspects'), None, 'Aspects', self.settingsAspects ),
								('Colors', None, _('Colors'), None, 'Colors', self.settingsColors ),
								('Labels', None, _('Labels'), None, 'Labels', self.settingsLabel ),
								('Location', gtk.STOCK_HOME, _('Set Home Location'), None, 'Set Location', self.settingsLocation ),
								('Configuration', gtk.STOCK_PREFERENCES, _('Configuration'), None, 'Configuration', self.settingsConfiguration ),
								('Radix', None, _('Radix Chart'), None, 'Transit Chart', self.specialRadix ),
								('Transit', None, _('Transit Chart'), None, 'Transit Chart', self.specialTransit ),
								('Synastry', None, _('Synastry Chart'), None, 'Synastry Chart...', lambda w: self.openDatabaseSelect(_("Select for Synastry"),"Synastry") ),
								('Composite', None, _('Composite Chart'), None, 'Composite Chart...', lambda w: self.openDatabaseSelect(_("Select for Composite"),"Composite") ),
								('Combine', None, _('Combine Chart'), None, 'Combine Chart...', lambda w: self.openDatabaseSelect(_("Select for Combine"),"Combine") ),
								('Solar', None, _('Solar Return'), None, 'Solar Return...', self.specialSolar ),
								('SecondaryProgression', None, _('Secondary Progressions'), None, 'Secondary Progressions...', self.specialSecondaryProgression ),
								('Tables', None, _('Tables') ),
								('MonthlyTimeline', None, _('Monthly Timeline'), None, 'Monthly Timeline', self.tableMonthlyTimeline ),
								('CuspAspects', None, _('Cusp Aspects'), None, 'Cusp Aspects', self.tableCuspAspects ),
								('Extra', None, _('Extra') ),
								('exportDB', None, _('Export Database'), None, 'Export Database', self.extraExportDB ),
								('importDB', None, _('Import Database'), None, 'Import Database', self.extraImportDB ),
								('About', None, _('About') ),
								('AboutInfo', gtk.STOCK_INFO, _('Info'), None, 'Info', self.aboutInfo )  ,                   
	                     ('AboutSupport', gtk.STOCK_HELP, _('Support'), None, 'Support', lambda w: webbrowser.open_new('http://www.openastro.org/?Support') )
	                     ]

		#update UI
		self.updateUI()

		# Create a MenuBar
		menubar = self.uimanager.get_widget('/MenuBar')
		self.vbox.pack_start(menubar, False)
		
		#make first SVG
		self.tempfilename = openAstro.makeSVG()
	
		# Draw svg pixbuf
		self.draw = drawSVG()
		self.draw.setSVG(self.tempfilename)
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.add_with_viewport(self.draw)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.vbox.pack_start(scrolledwindow)
	
		self.window.add(self.vbox)
		self.window.show_all()
		
		#check if we need to ask for location
		if openAstro.ask_for_home:
			self.settingsLocation(self.window)
		
		#check internet connection
		self.checkInternetConnection()
		
		#settingslocationmode off
		self.settingsLocationMode = False

		return

	"""

	'Extra' Menu Items Functions
	
	extraExportDB
	extraImportDB	
		
	"""
	
	def extraExportDB(self, widget):
		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
		chooser.set_current_folder(cfg.homedir)
		chooser.set_current_name('openastro-database.sql')
		filter = gtk.FileFilter()
		filter.set_name(_("OpenAstro.org Databases (*.sql)"))
		filter.add_pattern("*.sql")
		chooser.add_filter(filter)
		response = chooser.run()
		
		if response == gtk.RESPONSE_OK:
			copyfile(cfg.peopledb, chooser.get_filename())

		elif response == gtk.RESPONSE_CANCEL:
					dprint('Dialog closed, no files selected')	
		chooser.destroy()
	
	def extraImportDB(self, widget):
		chooser = gtk.FileChooserDialog(title=_("Please select database to import"),action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		chooser.set_current_folder(cfg.homedir)
		filter = gtk.FileFilter()
		filter.set_name(_("OpenAstro.org Databases (*.sql)"))
		filter.add_pattern("*.sql")
		chooser.add_filter(filter)
		response = chooser.run()
		
		if response == gtk.RESPONSE_OK:
			db.databaseMerge(cfg.peopledb,chooser.get_filename())

		elif response == gtk.RESPONSE_CANCEL:
					dprint('Dialog closed, no files selected')	
		chooser.destroy()			

	"""
	
	Function to check if we have an internet connection
	for geonames.org geocoder

	"""
	def checkInternetConnection(self):
	
		if db.getAstrocfg('use_geonames.org') == "0":
			self.iconn = False
			dprint('iconn: not using geocoding!')
			return
						
		#from openastromod import timeoutsocket
		#timeoutsocket.setDefaultSocketTimeout(2)
		HOST='ws.geonames.org'
		PORT=80
		s = None
		
		try:
			socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM)
		except socket.error, msg:
			self.iconn = False
			dprint('iconn: no connection (getaddrinfo)')
			return		
			
		for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
			af, socktype, proto, canonname, sa = res
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error, msg:
				s = None
				continue
			try:
				s.connect(sa)
			except (socket.error, timeoutsocket.Timeout):
				s.close()
				s = None
				continue
			break
		
		if s is None:
			self.iconn = False
			dprint('iconn: no connection')
		else:
			self.iconn = True
			dprint('iconn: got connection')
			#timeoutsocket.setDefaultSocketTimeout(20)
			s.close()
		return

	def zoom(self, action, current):
		#check for zoom level
		if current.get_name() == 'z80':
			openAstro.zoom=0.8
		elif current.get_name() == 'z150':
			openAstro.zoom=1.5
		elif current.get_name() == 'z200':
			openAstro.zoom=2
		else:
			openAstro.zoom=1

		#redraw svg
		openAstro.makeSVG()
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)
		return

		
	def doExport(self, widget):

		chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
		chooser.set_current_folder(cfg.homedir)
		
		
		filter = gtk.FileFilter()
		if widget.get_name() == 'exportPNG':
			chooser.set_current_name(openAstro.name+'.png')
			filter.set_name(_("PNG Image Files (*.png)"))
			filter.add_mime_type("image/png")
			filter.add_pattern("*.png")
		elif widget.get_name() == 'exportJPG':
			chooser.set_current_name(openAstro.name+'.jpg')
			filter.set_name(_("JPG Image Files (*.jpg)"))
			filter.add_mime_type("image/jpeg")
			filter.add_pattern("*.jpg")
			filter.add_pattern("*.jpeg")
		elif widget.get_name() == 'exportSVG':
			chooser.set_current_name(openAstro.name+'.svg')
			filter.set_name(_("SVG Image Files (*.svg)"))
			filter.add_mime_type("image/svg+xml")
			filter.add_pattern("*.svg")
		elif widget.get_name() == 'exportXML':
			chooser.set_current_name(openAstro.name+'.oac')
			filter.set_name(_("OpenAstro Charts (*.oac)"))
			filter.add_mime_type("text/xml")
			filter.add_pattern("*.oac")			
		chooser.add_filter(filter)	
		
		filter = gtk.FileFilter()
		filter.set_name(_("All files (*)"))
		filter.add_pattern("*")
		chooser.add_filter(filter)
		
		response = chooser.run()
		
		if response == gtk.RESPONSE_OK:
			if widget.get_name() == 'exportSVG':
				copyfile(cfg.tempfilename, chooser.get_filename())
			elif widget.get_name() == 'exportPNG':
				os.system("%s %s %s" % ('convert',cfg.tempfilename,"'"+chooser.get_filename()+"'"))
			elif widget.get_name() == 'exportJPG':
				os.system("%s %s %s" % ('convert',cfg.tempfilename,"'"+chooser.get_filename()+"'"))
			elif widget.get_name() == 'exportXML':
				openAstro.exportOAC(chooser.get_filename())
		elif response == gtk.RESPONSE_CANCEL:
					dprint('Dialog closed, no files selected')
			
		chooser.destroy()
		return
	
	def doImport(self, widget):
	
		chooser = gtk.FileChooserDialog(title=_('Select file to open'),action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		chooser.set_current_folder(cfg.homedir)
		
		filter = gtk.FileFilter()
		if widget.get_name() == 'importXML':
			filter.set_name(_("OpenAstro Charts (*.oac)"))
			#filter.add_mime_type("text/xml")
			filter.add_pattern("*.oac")
		elif widget.get_name() == 'importOroboros':
			filter.set_name(_("Oroboros Charts (*.xml)"))
			#filter.add_mime_type("text/xml")
			filter.add_pattern("*.xml")
		elif widget.get_name() == 'importSkylendar':
			filter.set_name(_("Skylendar Charts (*.skif)"))
			filter.add_pattern("*.skif")
		elif widget.get_name() == 'importAstrolog32':
			filter.set_name(_("Astrolog32 Charts (*.dat)"))
			filter.add_pattern("*.dat")
		elif widget.get_name() == 'importZet8':
			filter.set_name(_("Zet8 Databases (*.zbs)"))
			filter.add_pattern("*.zbs")	
		chooser.add_filter(filter)		
		response = chooser.run()
		
		if response == gtk.RESPONSE_OK:
			if widget.get_name() == 'importXML':
				openAstro.importOAC(chooser.get_filename())
			elif widget.get_name() == 'importOroboros':
				openAstro.importOroboros(chooser.get_filename())
			elif widget.get_name() == 'importSkylendar':
				openAstro.importSkylendar(chooser.get_filename())
			elif widget.get_name() == 'importAstrolog32':
				openAstro.importAstrolog32(chooser.get_filename())
			elif widget.get_name() == 'importZet8':
				openAstro.importZet8(chooser.get_filename())			
			self.updateChart()
		elif response == gtk.RESPONSE_CANCEL:
					dprint('Dialog closed, no files selected')
		chooser.destroy()
		return
	
	def specialRadix(self, widget):
		openAstro.type="Radix"
		openAstro.charttype=openAstro.label["radix"]
		openAstro.transit=False
		openAstro.makeSVG()
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)
			
	def specialTransit(self, widget):
		openAstro.type="Transit"
		openAstro.t_geolon=float(openAstro.home_geolon)
		openAstro.t_geolat=float(openAstro.home_geolat)
		
		now = datetime.datetime.now()
		timezone_str = zonetab.nearest_tz(openAstro.t_geolat,openAstro.t_geolon,zonetab.timezones())[2]
		#aware datetime object
		dt = zonetab.stdtime(timezone_str, now.year, now.month, now.day, now.hour, now.minute, now.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()	
		#transit data
		openAstro.t_year=dt_utc.year
		openAstro.t_month=dt_utc.month
		openAstro.t_day=dt_utc.day
		openAstro.t_hour=openAstro.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		openAstro.t_timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
		openAstro.t_altitude=25

		#make svg with transit
		openAstro.charttype="%s (%s-%02d-%02d %02d:%02d)" % (openAstro.label["transit"],dt.year,dt.month,dt.day,dt.hour,dt.minute)
		openAstro.transit=True
		openAstro.makeSVG()
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)	

	def specialSolar(self, widget):
		# create a new window
		self.win_SS = gtk.Dialog()
		self.win_SS.set_icon_from_file(cfg.iconWindow)
		self.win_SS.set_title(_("Select year for Solar Return"))
		self.win_SS.connect("delete_event", lambda w,e: self.win_SS.destroy())
		self.win_SS.move(150,150)
		self.win_SS.set_border_width(5)
		self.win_SS.set_size_request(300,100)
		
		#create a table
		table = gtk.Table(2, 1, False)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		table.set_border_width(10)

		#options
		table.attach(gtk.Label(_("Select year for Solar Return")), 0, 1, 0, 1, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		entry=gtk.Entry(4)
		entry.set_width_chars(4) 
		entry.set_text(str(datetime.datetime.now().year))
		table.attach(entry, 1, 2, 0, 1, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		
		#make the ui layout with ok button
		self.win_SS.vbox.pack_start(table, True, True, 0)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.specialSolarSubmit, entry)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SS.action_area.pack_start(button, True, True, 0)
		button.grab_default()		

		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SS.destroy())
		self.win_SS.action_area.pack_start(button, True, True, 0)

		self.win_SS.show_all()
		return
	
	def specialSolarSubmit(self, widget, entry):
		intyear = int(entry.get_text())
		openAstro.localToSolar(intyear)
		self.win_SS.destroy()
		self.updateChart()
		return
	
	def specialSecondaryProgression(self, widget):
		# create a new window
		self.win_SSP = gtk.Dialog()
		self.win_SSP.set_icon_from_file(cfg.iconWindow)
		self.win_SSP.set_title(_("Enter Date"))
		self.win_SSP.connect("delete_event", lambda w,e: self.win_SSP.destroy())
		self.win_SSP.move(150,150)
		self.win_SSP.set_border_width(5)
		self.win_SSP.set_size_request(320,180)
		
		#create a table
		table = gtk.Table(1, 4, False)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		table.set_border_width(10)

		#options
		table.attach(gtk.Label(_("Select date for Secondary Progression")+":"), 0, 1, 0, 1, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
		hbox = gtk.HBox(spacing=4)  # pack_start(child, expand=True, fill=True, padding=0)
		entry={}
		
		hbox.pack_start(gtk.Label(_('Year')+": "))	
		entry['Y']=gtk.Entry(4)
		entry['Y'].set_width_chars(4) 
		entry['Y'].set_text(str(datetime.datetime.now().year))
		hbox.pack_start(entry['Y'])
		hbox.pack_start(gtk.Label(_('Month')+": "))	
		entry['M']=gtk.Entry(2)
		entry['M'].set_width_chars(2) 
		entry['M'].set_text('%02d'%(datetime.datetime.now().month))
		hbox.pack_start(entry['M'])
		hbox.pack_start(gtk.Label(_('Day')+": "))	
		entry['D']=gtk.Entry(2)
		entry['D'].set_width_chars(2) 
		entry['D'].set_text(str(datetime.datetime.now().day))
		hbox.pack_start(entry['D'])	
		table.attach(hbox,0,1,1,2, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
		
		hbox = gtk.HBox(spacing=4)
		hbox.pack_start(gtk.Label(_('Hour')+": "))	
		entry['h']=gtk.Entry(2)
		entry['h'].set_width_chars(2) 
		entry['h'].set_text('%02d'%(datetime.datetime.now().hour))
		hbox.pack_start(entry['h'])
		hbox.pack_start(gtk.Label(_('Min')+": "))	
		entry['m']=gtk.Entry(2)
		entry['m'].set_width_chars(2) 
		entry['m'].set_text('%02d'%(datetime.datetime.now().minute))
		hbox.pack_start(entry['m'])
		table.attach(hbox,0,1,2,3, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10, ypadding=10)
		
		#make the ui layout with ok button
		self.win_SSP.vbox.pack_start(table, True, True, 0)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.specialSecondaryProgressionSubmit, entry)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SSP.action_area.pack_start(button, True, True, 0)
		button.grab_default()		

		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SSP.destroy())
		self.win_SSP.action_area.pack_start(button, True, True, 0)

		self.win_SSP.show_all()
		return

	def specialSecondaryProgressionSubmit(self, widget, entry):
		dt	= datetime.datetime(int(entry['Y'].get_text()),int(entry['M'].get_text()),int(entry['D'].get_text()),int(entry['h'].get_text()),int(entry['m'].get_text()))
		openAstro.localToSecondaryProgression(dt)
		self.win_SSP.destroy()
		self.updateChart()
		return
	
	def tableMonthlyTimeline(self, widget):
		dialog = gtk.Dialog(_("Select Month"),
                     self.window,
                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

		dialog.connect("destroy", lambda w: dialog.destroy())
		dialog.set_size_request(200, 200)
		dialog.move(50,50)
		self.tMTentry={}
		dialog.vbox.pack_start(gtk.Label(_('Year')+": "))	
		self.tMTentry['Y']=gtk.Entry(4)
		self.tMTentry['Y'].set_width_chars(4) 
		self.tMTentry['Y'].set_text(str(datetime.datetime.now().year))
		dialog.vbox.pack_start(self.tMTentry['Y'], False, False, 0)
		dialog.vbox.pack_start(gtk.Label(_('Month')+": "))	
		self.tMTentry['M']=gtk.Entry(2)
		self.tMTentry['M'].set_width_chars(2) 
		self.tMTentry['M'].set_text('%02d'%(datetime.datetime.now().month))
		dialog.vbox.pack_start(self.tMTentry['M'], False, False, 0)
		dialog.show_all()
		
		ret = dialog.run()
		if ret == gtk.RESPONSE_ACCEPT:
			dialog.destroy()
			self.tableMonthlyTimelineShow()
		else:
			dialog.destroy()
		return

	def tableMonthlyTimelinePrint(self, pages, pdf, window, name):
		settings = None
		print_op = gtk.PrintOperation()
		print_op.set_unit(gtk.UNIT_PIXEL)
		if settings != None: 
			print_op.set_print_settings(settings)
		print_op.connect("begin_print", self.tableMonthlyTimelinePrintBegin, pages)
		print_op.connect("draw_page", self.tableMonthlyTimelinePrintDraw)

		if pdf:
			chooser = gtk.FileChooserDialog(title=_("Select Export Filename"),action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                  buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
			chooser.set_current_folder(cfg.homedir)
			chooser.set_current_folder(cfg.homedir)
			chooser.set_current_name(name)
			filter = gtk.FileFilter()
			filter.set_name(_("PDF Files (*.pdf)"))
			filter.add_pattern("*.pdf")
			chooser.add_filter(filter)
			response = chooser.run()
			if response == gtk.RESPONSE_OK:
				print_op.set_export_filename(chooser.get_filename())
				chooser.destroy()
				res = print_op.run(gtk.PRINT_OPERATION_ACTION_EXPORT, window)	
			else:
				chooser.destroy()
				print_op.cancel()
				res = None
			
		else:
			res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, window)		

		if res == gtk.PRINT_OPERATION_RESULT_ERROR:
			error_dialog = gtk.MessageDialog(window,gtk.DIALOG_DESTROY_WITH_PARENT,gtk.MESSAGE_ERROR,gtk.BUTTONS_CLOSE,"Error printing:\n")
			error_dialog.connect("response", lambda w,id: w.destroy())
			error_dialog.show()
		elif res == gtk.PRINT_OPERATION_RESULT_APPLY:
			settings = print_op.get_print_settings()


	def tableMonthlyTimelinePrintBegin(self, operation, context, pages):
		operation.set_n_pages(pages)
		operation.set_use_full_page(False)
		ps = gtk.PageSetup()
		ps.set_orientation(gtk.PAGE_ORIENTATION_PORTRAIT)
		ps.set_paper_size(gtk.PaperSize(gtk.PAPER_NAME_A4))
		operation.set_default_page_setup(ps)
	
	def tableMonthlyTimelinePrintDraw(self, operation, context, page_nr):
		cr = context.get_cairo_context()
		#draw svg
		printing={}
		printing['pagenum']=page_nr
		printing['width']=context.get_width()
		printing['height']=context.get_height()
		printing['dpi_x']=context.get_dpi_x()
		printing['dpi_y']=context.get_dpi_y()
		if(self.tabletype == "timeline"):
			self.tableMonthlyTimelineShow(printing)
			#draw svg for printing
			rsvg.set_default_dpi(900)
			svg = rsvg.Handle(cfg.tempfilenametableprint)
			svg.render_cairo(cr)
		elif(self.tabletype == "cuspaspects"):
			self.tableCuspAspects(None,printing)
			#draw svg for printing
			rsvg.set_default_dpi(900)
			svg = rsvg.Handle(cfg.tempfilenametableprint)
			svg.render_cairo(cr)		


	def tableMonthlyTimelineShow(self, printing=None):
		self.tabletype="timeline"
		y = int(self.tMTentry['Y'].get_text())
		m = int(self.tMTentry['M'].get_text())
		tz = datetime.timedelta(seconds=float(openAstro.timezone)*float(3600))
		startdate = datetime.datetime(y,m,1,12) - tz
		q,r = divmod(startdate.month, 12)
		enddate = datetime.datetime(startdate.year+q, r+1, 1,12)
		delta = enddate - startdate
		atgrid={}
		astypes={}
		retrogrid={}
		for d in range(delta.days):
			cdate = startdate + datetime.timedelta(days=d)
			tmoddata = ephemeris.ephData(cdate.year,cdate.month,cdate.day,cdate.hour,
				openAstro.geolon,openAstro.geolat,openAstro.altitude,openAstro.planets,
				openAstro.zodiac,db.astrocfg)
			#planets_sign,planets_degree,planets_degree_ut,planets_retrograde,houses_degree
			#houses_sign,houses_degree_ut

			for i in range(len(openAstro.planets)):
				start=openAstro.planets_degree_ut[i]
				for x in range(i+1):
					end=tmoddata.planets_degree_ut[x]
					diff=float(openAstro.degreeDiff(start,end))
					#skip asc/dsc/mc/ic on tmoddata
					if 23 <= x <= 26:
						continue
					#skip moon on tmoddate
					if x == 1:
						continue
					#loop orbs
					if (openAstro.planets[i]['visible'] == 1) & (openAstro.planets[x]['visible'] == 1):	
						for z in range(len(openAstro.aspects)):
							#only major aspects
							if openAstro.aspects[z]['is_major'] != 1:
								continue
							#check for personal planets and determine orb
							orb_before = 4
							orb_after = 4
							#check if we want to display this aspect	
							if	( float(openAstro.aspects[z]['degree']) - orb_before ) <= diff <= ( float(openAstro.aspects[z]['degree']) + orb_after ):
								orb = diff - openAstro.aspects[z]['degree']
								if orb < 0:
									orb = orb/-1						
								#aspect grid dictionary
								s="%02d%02d%02d"%(i,z,x)
								astypes[s]=(i,x,z)
								
								if s not in retrogrid:
									retrogrid[s]={}
								retrogrid[s][d]=tmoddata.planets_retrograde[x]
									
								if s not in atgrid:
									atgrid[s]={}
								atgrid[s][d]=orb
		#sort
		keys = astypes.keys()
		keys.sort()
		pages = int(math.ceil(len(keys)/65.0))
		
		out = ""
		#make numbers of days in month
		dx=[80]
		skipdays = [9,19]
		for d in range(delta.days):
			if d in skipdays:
				dx.append(dx[-1]+40)
			else:
				dx.append(dx[-1]+20)	
		
		for p in range(pages):
			if p == 0:
				ystart = 10
			else:
				ystart = (1188 * p) + 62
			pagelen = (len(keys)+1)-p*65
			if pagelen > 65:
				pagelen = 66
			ylen = ((len(keys)+1)-p*65)*16	
			for a in range(delta.days):
				out += '<text x="%s" y="%s" style="fill: #000; font-size: 10">%02d</text>\n'%(
					dx[a],ystart,a+1)
				out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
					dx[a]-5,ystart,dx[a]-5,ystart+pagelen*16)	
				#skipdays line
				if a in skipdays:
					out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
						dx[a]-5+20,ystart,dx[a]-5+20,ystart+pagelen*16)						
				

			#last line
			out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
					dx[-1]-5,ystart,dx[-1]-5,ystart+pagelen*16)
					
		#get the number of total aspects
		c = 0
		for m in range(len(keys)):
			i,x,z = astypes[keys[m]]
			c += 1
			pagenum = int(math.ceil(c/65.0))
			pagey = (pagenum - 1) * 200
			y = (c*16) + pagey
			#horizontal lines
			out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
				0,y-1,dx[skipdays[0]]+15,y-1)
			for s in range(len(skipdays)):
				if s is len(skipdays)-1:
					out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
						dx[skipdays[s]+1]-5,y-1,dx[-1],y-1)
				else:
					out += '<line x1="%s" y1="%s" x2="%s" y2="%s" style="stroke: #000; stroke-width: .5; stroke-opacity:1;"/>\n'%(
						dx[skipdays[s]+1]-5,y-1,dx[skipdays[s+1]]+15,y-1)
			#outer planet
			out += '<g transform="translate(0,%s)"><g transform="scale(.5)"><use x="0" y="0" xlink:href="#%s" /></g></g>\n'%(
				y,openAstro.planets[x]['name'])
			#aspect
			out += '<g><use x="20" y="%s" xlink:href="#orb%s" /></g>\n'%(
				y,openAstro.aspects[z]['degree'])			
			#inner planet
			out += '<g transform="translate(40,%s)"><g transform="scale(.5)"><use x="0" y="0" xlink:href="#%s" /></g></g>\n'%(y,
				openAstro.planets[i]['name'])		
			for d in range(delta.days):					
				if d in atgrid[keys[m]]:
					orb = atgrid[keys[m]][d]
					op = .1+(.7-(orb/(4/.7))) #4 is maxorb
					if op > 1:
						op = 1
					strop = str(float(orb))
					out += '<rect x="%s" y="%s" width="20" height="16" style="fill: %s; fill-opacity:%s;" />'%(
						dx[d]-5,y-1,openAstro.colors["aspect_%s" %(openAstro.aspects[z]['degree'])],op)
					#check for retrograde outer planet
					if retrogrid[keys[m]][d]:
						out += '<g transform="translate(%s,%s)"><g transform="scale(.3)">\
							<use x="0" y="0" xlink:href="#retrograde" style="fill:black; fill-opacity:.8;" /></g></g>\n'%(
							dx[d]+10,y+10)							
					out += '<text x="%s" y="%s" style="fill: #000; font-size: 10">%s</text>\n'%(
						dx[d],y+9,strop[:3])
							
				else:
					out += ""

		#template
		td = {}
		for i in range(len(openAstro.planets)):
			td['planets_color_%s'%(i)]=openAstro.colors["planet_%s"%(i)]
		for i in range(12):
			td['zodiac_color_%s'%(i)]=openAstro.colors["zodiac_icon_%s" %(i)]
		for i in range(len(openAstro.aspects)):
			td['orb_color_%s'%(openAstro.aspects[i]['degree'])]=openAstro.colors["aspect_%s" %(openAstro.aspects[i]['degree'])]
		td['stringTitle'] = "%s Timeline for %s"%(
			startdate.strftime("%B %Y"),openAstro.name)
			
		pagesY = (1188 * pages)+10 #ten is buffer between pages
		if printing:
			td['svgWidth'] = printing['width']
			td['svgHeight'] = printing['height']
			td['viewbox'] = "0 %s 840 1188" %( printing['pagenum']*(1188+10) )
		else:
			td['svgWidth'] = 1050
			td['svgHeight'] = (td['svgWidth']/840.0)* pagesY
			td['viewbox'] = "0 0 840 %s" %( pagesY ) 
		

		td['data'] = out
		
		#pages rectangles
		pagesRect,x,y,w,h="",0,0,840,1188
		for p in range(pages):
			if p == 0:
				offset=0
			else:
				offset=10
			pagesRect += '<rect x="%s" y="%s" width="%s" height="%s" style="fill: #ffffff;" />'%(
				x,y+(p*1188)+offset,w,h)
				
		td['pagesRect'] = pagesRect
				
		#read and write template
		f=open(cfg.xml_svg_table)
		template=Template(f.read()).substitute(td)
		f.close()
		if printing:
			f=open(cfg.tempfilenametableprint,"w")
		else:
			f=open(cfg.tempfilenametable,"w")
		f.write(template)
		f.close()
		
		if printing == None:
			self.win_TMT = gtk.Window(gtk.WINDOW_TOPLEVEL)
			self.win_TMT.connect("destroy", lambda w: self.win_TMT.destroy())
			self.win_TMT.set_title("OpenAstro.org Timeline")
			self.win_TMT.set_icon_from_file(cfg.iconWindow)
			self.win_TMT.set_size_request(td['svgWidth']+30, 700)
			self.win_TMT.move(50,50)
			vbox = gtk.VBox()
			hbox = gtk.HBox()
			button = gtk.Button(_('Print'))
			button.connect("clicked", lambda w: self.tableMonthlyTimelinePrint(pages,pdf=False,window=self.win_TMT,name="timeline-%s.pdf"%(openAstro.name)))
			hbox.pack_start(button,False,False)
			button = gtk.Button(_('Save as PDF'))
			button.connect("clicked", lambda w: self.tableMonthlyTimelinePrint(pages,pdf=True,window=self.win_TMT,name="timeline-%s.pdf"%(openAstro.name)))
			hbox.pack_start(button,False,False)
			vbox.pack_start(hbox,False,False)
			draw = drawSVG()
			draw.setSVG(cfg.tempfilenametable)
			scrolledwindow = gtk.ScrolledWindow()
			scrolledwindow.add_with_viewport(draw)
			scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
			vbox.pack_start(scrolledwindow)
		
			self.win_TMT.add(vbox)
			self.win_TMT.show_all()
		return

	def tableCuspAspects(self, widget, printing=None):
		self.tabletype="cuspaspects"
		#data
		out='<g transform="scale(1.5)">'
		xindent=50
		yindent=200
		box=14
		style='stroke:#000; stroke-width: 1px; stroke-opacity:.6; fill:none'
		textstyle="font-size: 11px; color: #000"
		#draw cusps
		for cusp in range(len(openAstro.houses_degree_ut)):
				x = xindent - box
				y = yindent - (box*(cusp+1))
				out += '<text \
						x="%s" \
						y="%s" \
						style="%s">%s</text>\n\
						'%(x-30, y+box-5, textstyle, openAstro.label['cusp']+" "+str(cusp+1))
									
		revr=range(len(openAstro.planets))
		for a in revr:
			if 23 <= a <= 26:
				continue; #skip asc/dsc/mc/ic
			if a == 11 or a == 13 or a == 21 or a == 22:
				continue; #skip ?,?,intp. apogee, intp. perigee
				
			start=openAstro.planets_degree_ut[a]
			#first planet 
			out += '<rect x="%s" \
						y="%s" \
						width="%s" \
						height="%s" \
						style="%s"/>\n' %(xindent,yindent,box,box,style)
			out += '<use transform="scale(0.4)" \
					x="%s" \
					y="%s" \
					xlink:href="#%s" />\n\
					'%((xindent+2)*2.5, (yindent+1)*2.5, openAstro.planets[a]['name'])
		
			yorb=yindent - box
			for b in range(12):
				end=openAstro.houses_degree_ut[b]
				diff=openAstro.degreeDiff(start,end)
				out += '<rect x="%s" \
					y="%s" \
					width="%s" \
					height="%s" \
					style="%s"/>\n\
					'%(xindent,yorb,box,box,style)
				for z in range(len(openAstro.aspects)):
					if	( float(openAstro.aspects[z]['degree']) - float(openAstro.aspects[z]['orb']) ) <= diff <= ( float(openAstro.aspects[z]['degree']) + float(openAstro.aspects[z]['orb']) ) and openAstro.aspects[z]['visible_grid'] == 1:
							out += '<use \
								x="%s" \
								y="%s" \
								xlink:href="#orb%s" />\n\
								'%(xindent,yorb+1,openAstro.aspects[z]['degree'])
				yorb=yorb-box
				
			xindent += box
				
		#add cusp to cusp
		xindent = 50
		yindent = 400
		#draw cusps
		for cusp in range(len(openAstro.houses_degree_ut)):
				x = xindent - box
				y = yindent - (box*(cusp+1))
				out += '<text \
						x="%s" \
						y="%s" \
						style="%s">%s</text>\n\
						'%(x-30, y+box-5, textstyle, openAstro.label['cusp']+" "+str(cusp+1))

		for a in range(12):
			start=openAstro.houses_degree_ut[a]
			#first planet 
			out += '<rect x="%s" \
						y="%s" \
						width="%s" \
						height="%s" \
						style="%s"/>\n' %(xindent,yindent,box,box,style)
			out += '<text \
						x="%s" \
						y="%s" \
						style="%s">%s</text>\n\
						'%((xindent+2), (yindent+box-4), textstyle, ""+str(a+1))
		
			yorb=yindent - box
			for b in range(12):
				end=openAstro.houses_degree_ut[b]
				diff=openAstro.degreeDiff(start,end)
				out += '<rect x="%s" \
					y="%s" \
					width="%s" \
					height="%s" \
					style="%s"/>\n\
					'%(xindent,yorb,box,box,style)
				for z in range(len(openAstro.aspects)):
					if	( float(openAstro.aspects[z]['degree']) - float(openAstro.aspects[z]['orb']) ) <= diff <= ( float(openAstro.aspects[z]['degree']) + float(openAstro.aspects[z]['orb']) ) and openAstro.aspects[z]['visible_grid'] == 1:
							out += '<use \
								x="%s" \
								y="%s" \
								xlink:href="#orb%s" />\n\
								'%(xindent,yorb+1,openAstro.aspects[z]['degree'])
				yorb=yorb-box
				
			xindent += box	
			
		out += "</g>"
			
						
		#template
		td = {}
		for i in range(len(openAstro.planets)):
			td['planets_color_%s'%(i)]=openAstro.colors["planet_%s"%(i)]
		for i in range(12):
			td['zodiac_color_%s'%(i)]=openAstro.colors["zodiac_icon_%s" %(i)]
		for i in range(len(openAstro.aspects)):
			td['orb_color_%s'%(openAstro.aspects[i]['degree'])]=openAstro.colors["aspect_%s" %(openAstro.aspects[i]['degree'])]
		td['stringTitle'] = "Cusp Aspects for %s"%(openAstro.name)
		
		pages=1
		pagesY = (1188 * pages)+10 #ten is buffer between pages
		if printing:
			td['svgWidth'] = printing['width']
			td['svgHeight'] = printing['height']
			td['viewbox'] = "0 %s 840 1188" %( printing['pagenum']*(1188+10) )
		else:
			td['svgWidth'] = 1050
			td['svgHeight'] = (td['svgWidth']/840.0)* pagesY
			td['viewbox'] = "0 0 840 %s" %( pagesY ) 

		td['data'] = out
		td['pagesRect'] = '<rect x="0" y="0" width="840" height="1188" style="fill: #ffffff;" />'
		
		#read and write template
		f=open(cfg.xml_svg_table)
		template=Template(f.read()).substitute(td)
		f.close()
		if printing:
			f=open(cfg.tempfilenametableprint,"w")
		else:
			f=open(cfg.tempfilenametable,"w")
		f.write(template)
		f.close()

		#display svg
		if printing == None:
			self.win_TCA = gtk.Window(gtk.WINDOW_TOPLEVEL)
			self.win_TCA.connect("destroy", lambda w: self.win_TCA.destroy())
			self.win_TCA.set_title("OpenAstro.org Cusp Aspects")
			self.win_TCA.set_icon_from_file(cfg.iconWindow)
			self.win_TCA.set_size_request(td['svgWidth']+30, 700)
			self.win_TCA.move(50,50)
			vbox = gtk.VBox()
			hbox = gtk.HBox()
			button = gtk.Button(_('Print'))
			button.connect("clicked", lambda w: self.tableMonthlyTimelinePrint(pages=1,pdf=False,window=self.win_TCA,name="cusp-aspects-%s.pdf"%(openAstro.name)))
			hbox.pack_start(button,False,False)
			button = gtk.Button(_('Save as PDF'))
			button.connect("clicked", lambda w: self.tableMonthlyTimelinePrint(pages=1,pdf=True,window=self.win_TCA,name="cusp-aspects-%s.pdf"%(openAstro.name)))
			hbox.pack_start(button,False,False)
			vbox.pack_start(hbox,False,False)
			draw = drawSVG()
			draw.setSVG(cfg.tempfilenametable)
			scrolledwindow = gtk.ScrolledWindow()
			scrolledwindow.add_with_viewport(draw)
			scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
			vbox.pack_start(scrolledwindow)
			self.win_TCA.add(vbox)
			self.win_TCA.show_all()		
		return
		
	def aboutInfo(self, widget):
		dialog=gtk.Dialog('Info',self.window,0,(gtk.STOCK_OK, gtk.RESPONSE_DELETE_EVENT))
		dialog.set_icon_from_file(cfg.iconWindow)
		dialog.connect("response", lambda w,e: dialog.destroy())				
		dialog.connect("close", lambda w,e: dialog.destroy())
		about_text = _('OpenAstro.org - Open Source Astrology')+'\n\n'+_('Version')+' '+cfg.version+'\n'+_('Author')+': Pelle van der Scheer'
		dialog.vbox.pack_start(gtk.Label(about_text),True,True,0)
		dialog.show_all()
		return

	def openDatabaseFamous(self, widget):
		self.openDatabase(widget,db.getDatabaseFamous(limit="500"))

	def nameSearch(self, widget):
		self.listmodel.clear()
		self.DB = db.getDatabaseFamous(limit="15",search=self.namesearch.get_text())
		for i in range(len(self.DB)):
			h,m,s = openAstro.decHour(float(self.DB[i]["hour"]))
			dt_utc=datetime.datetime(int(self.DB[i]["year"]),int(self.DB[i]["month"]),int(self.DB[i]["day"]),h,m,s)
			dt = dt_utc + datetime.timedelta(seconds=float(self.DB[i]["timezone"])*float(3600))
			birth_date = str(dt.year)+'-%(#1)02d-%(#2)02d %(#3)02d:%(#4)02d:%(#5)02d' % {'#1':dt.month,'#2':dt.day,'#3':dt.hour,'#4':dt.minute,'#5':dt.second}			
			self.listmodel.append([self.DB[i]["name"],birth_date,self.DB[i]["location"],self.DB[i]["id"]])
		return		

	def nameSearchReset(self, widget):
		self.listmodel.clear()
		self.DB = db.getDatabaseFamous(limit="500")
		for i in range(len(self.DB)):
			h,m,s = openAstro.decHour(float(self.DB[i]["hour"]))
			dt_utc=datetime.datetime(int(self.DB[i]["year"]),int(self.DB[i]["month"]),int(self.DB[i]["day"]),h,m,s)
			dt = dt_utc + datetime.timedelta(seconds=float(self.DB[i]["timezone"])*float(3600))
			birth_date = str(dt.year)+'-%(#1)02d-%(#2)02d %(#3)02d:%(#4)02d:%(#5)02d' % {'#1':dt.month,'#2':dt.day,'#3':dt.hour,'#4':dt.minute,'#5':dt.second}			
			self.listmodel.append([self.DB[i]["name"],birth_date,self.DB[i]["location"],self.DB[i]["id"]])
		return		
			
	def openDatabase(self, widget, extraDB=None):
		self.win_OD = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.win_OD.set_icon_from_file(cfg.iconWindow)
		self.win_OD.set_title(_('Open Database Entry'))
		self.win_OD.set_size_request(600, 450)
		self.win_OD.move(150,150)
		self.win_OD.connect("delete_event", lambda w,e: self.win_OD.destroy())
		#listmodel		
		self.listmodel = gtk.ListStore(str,str,str,int)	
		self.win_OD_treeview = gtk.TreeView(self.listmodel)
		#selection
		self.win_OD_selection = self.win_OD_treeview.get_selection()
		self.win_OD_selection.set_mode(gtk.SELECTION_SINGLE)
		#treeview columns		
		self.win_OD_tvcolumn0 = gtk.TreeViewColumn(_('Name'))
		self.win_OD_tvcolumn1 = gtk.TreeViewColumn(_('Birth Date (Local)'))
		self.win_OD_tvcolumn2 = gtk.TreeViewColumn(_('Location'))
		#add data from event_natal table
		if extraDB != None:
			self.win_OD_treeview.set_enable_search(False)		
			self.DB = extraDB
		else:
			self.win_OD_treeview.set_enable_search(True)		
			self.DB = db.getDatabase()
			
		for i in range(len(self.DB)):
			h,m,s = openAstro.decHour(float(self.DB[i]["hour"]))
			dt_utc=datetime.datetime(int(self.DB[i]["year"]),int(self.DB[i]["month"]),int(self.DB[i]["day"]),h,m,s)
			dt = dt_utc + datetime.timedelta(seconds=float(self.DB[i]["timezone"])*float(3600))
			birth_date = str(dt.year)+'-%(#1)02d-%(#2)02d %(#3)02d:%(#4)02d:%(#5)02d' % {'#1':dt.month,'#2':dt.day,'#3':dt.hour,'#4':dt.minute,'#5':dt.second}			
			self.listmodel.append([self.DB[i]["name"],birth_date,self.DB[i]["location"],self.DB[i]["id"]])

		#add columns to treeview
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn0)
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn1)
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn2)
		#cell renderers
		cell0 = gtk.CellRendererText()
		cell1 = gtk.CellRendererText()
		cell2 = gtk.CellRendererText()
		#add cells to columns
		self.win_OD_tvcolumn0.pack_start(cell0, True)
		self.win_OD_tvcolumn1.pack_start(cell1, True)
		self.win_OD_tvcolumn2.pack_start(cell2, True)
		#set the cell attributes to the listmodel column
		self.win_OD_tvcolumn0.set_attributes(cell0, text=0)
		self.win_OD_tvcolumn1.set_attributes(cell1, text=1)
		self.win_OD_tvcolumn2.set_attributes(cell2, text=2)
		#set treeview options
		self.win_OD_treeview.set_search_column(0)
		self.win_OD_tvcolumn0.set_sort_column_id(0)
		self.win_OD_tvcolumn1.set_sort_column_id(1)
		self.win_OD_tvcolumn2.set_sort_column_id(2)
		#add treeview to scrolledwindow
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.add(self.win_OD_treeview)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		vbox=gtk.VBox()
		vbox.pack_start(scrolledwindow)
		hbox=gtk.HBox(False,4)		
		#buttons
		if extraDB == None:
			button = gtk.Button(stock=gtk.STOCK_CANCEL)
			button.connect("clicked", lambda w: self.win_OD.destroy())
			hbox.pack_end(button,False)	
			button = gtk.Button(stock=gtk.STOCK_EDIT)
			button.connect("clicked", self.openDatabaseEdit)
			hbox.pack_end(button,False)
			button = gtk.Button(stock=gtk.STOCK_DELETE)
			button.connect("clicked", self.openDatabaseDel)
			hbox.pack_end(button,False)
			button = gtk.Button(stock=gtk.STOCK_OPEN)
			button.connect("clicked", self.openDatabaseOpen)
			hbox.pack_end(button,False)	
		else:
			label=gtk.Label(_("Search Name")+":")
			self.namesearch = gtk.Entry()
			self.namesearch.set_max_length(34)
			self.namesearch.set_width_chars(24)
			self.namesearchbutton = gtk.Button(_('Search'))
			self.namesearchbutton.connect("clicked", self.nameSearch)
			self.namesearch.connect("activate", self.nameSearch)
			self.nameresetbutton = gtk.Button(_('Reset'))
			self.nameresetbutton.connect("clicked", self.nameSearchReset)

			hbox.pack_end(self.nameresetbutton,False,False,0)
			hbox.pack_end(self.namesearchbutton,False,False,0)
			hbox.pack_end(self.namesearch,False,False,0)
			hbox.pack_end(label,False,False,0)
			
			button = gtk.Button(stock=gtk.STOCK_OPEN)
			button.connect("clicked", self.openDatabaseOpen)
			hbox.pack_start(button,False)
			button = gtk.Button(stock=gtk.STOCK_CLOSE)
			button.connect("clicked", lambda w: self.win_OD.destroy())
			hbox.pack_start(button,False)			
			
			
		#display window
		self.win_OD_treeview.connect("row-activated", lambda w,e,f: self.openDatabaseOpen(w))
		vbox.pack_start(hbox,False)
		self.win_OD.add(vbox)
		self.win_OD_treeview.set_model(self.listmodel)
		self.win_OD.show_all()
		return
	
	def openDatabaseSelect(self, selectstr, type):
	
		self.win_OD = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.win_OD.set_icon_from_file(cfg.iconWindow)
		self.win_OD.set_title(_('Select Database Entry'))
		self.win_OD.set_size_request(400, 450)
		self.win_OD.move(150,150)
		self.win_OD.connect("delete_event", lambda w,e: self.openDatabaseSelectReject())
		#listmodel		
		listmodel = gtk.ListStore(str,str,str,int)	
		self.win_OD_treeview = gtk.TreeView(listmodel)
		
		#selection
		self.win_OD_selection = self.win_OD_treeview.get_selection()
		self.win_OD_selection.set_mode(gtk.SELECTION_SINGLE)
		#treeview columns		
		self.win_OD_tvcolumn0 = gtk.TreeViewColumn(_('Name'))
		self.win_OD_tvcolumn1 = gtk.TreeViewColumn(_('Birth Date (Local)'))
		self.win_OD_tvcolumn2 = gtk.TreeViewColumn(_('Location'))
		#add data from event_natal table
		self.DB = db.getDatabase()
		for i in range(len(self.DB)):
			h,m,s = openAstro.decHour(float(self.DB[i]["hour"]))
			dt_utc=datetime.datetime(int(self.DB[i]["year"]),int(self.DB[i]["month"]),int(self.DB[i]["day"]),h,m,s)
			dt = dt_utc + datetime.timedelta(seconds=float(self.DB[i]["timezone"])*float(3600))
			birth_date = str(dt.year)+'-%(#1)02d-%(#2)02d %(#3)02d:%(#4)02d:%(#5)02d' % {'#1':dt.month,'#2':dt.day,'#3':dt.hour,'#4':dt.minute,'#5':dt.second}			
			listmodel.append([self.DB[i]["name"],birth_date,self.DB[i]["location"],self.DB[i]["id"]])
		#add columns to treeview
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn0)
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn1)
		self.win_OD_treeview.append_column(self.win_OD_tvcolumn2)
		#cell renderers
		cell0 = gtk.CellRendererText()
		cell1 = gtk.CellRendererText()
		cell2 = gtk.CellRendererText()
		#add cells to columns
		self.win_OD_tvcolumn0.pack_start(cell0, True)
		self.win_OD_tvcolumn1.pack_start(cell1, True)
		self.win_OD_tvcolumn2.pack_start(cell2, True)
		#set the cell attributes to the listmodel column
		self.win_OD_tvcolumn0.set_attributes(cell0, text=0)
		self.win_OD_tvcolumn1.set_attributes(cell1, text=1)
		self.win_OD_tvcolumn2.set_attributes(cell2, text=2)
		#set treeview options
		self.win_OD_treeview.set_search_column(0)
		self.win_OD_tvcolumn0.set_sort_column_id(0)
		self.win_OD_tvcolumn1.set_sort_column_id(1)
		self.win_OD_tvcolumn2.set_sort_column_id(2)
		#add treeview to scrolledwindow
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.add(self.win_OD_treeview)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		vbox=gtk.VBox()
		vbox.pack_start(scrolledwindow)
		hbox=gtk.HBox()		
		#buttons
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.openDatabaseSelectReject())
		hbox.pack_end(button,False)	
		button = gtk.Button(selectstr)
		button.connect("clicked", lambda w: self.openDatabaseSelectReturn(type))
		hbox.pack_end(button,False)		
		#display window
		vbox.pack_start(hbox,False)
		self.win_OD.add(vbox)
		self.win_OD_treeview.set_model(listmodel)
		self.win_OD.show_all()
		return
	
	def openDatabaseSelectReject(self):
		self.win_OD.destroy()
		return
	
	def openDatabaseSelectReturn(self, type):
		model = self.win_OD_selection.get_selected()[0]
		iter = self.win_OD_selection.get_selected()[1]
		for i in range(len(self.DB)):
			if self.DB[i]["id"] == model.get_value(iter,3):
				list = self.DB[i]

		#synastry
		if type == "Synastry":
			openAstro.type="Transit"
			openAstro.t_name=str(list["name"])
			openAstro.t_year=int(list["year"])
			openAstro.t_month=int(list["month"])
			openAstro.t_day=int(list["day"])
			openAstro.t_hour=float(list["hour"])
			openAstro.t_geolon=float(list["geolon"])
			openAstro.t_geolat=float(list["geolat"])
			openAstro.t_altitude=int(list["altitude"])
			openAstro.t_location=str(list["location"])
			openAstro.t_timezone=float(list["timezone"])
			openAstro.charttype="%s (%s)" % (openAstro.label["synastry"],openAstro.t_name)
			openAstro.transit=True
			openAstro.makeSVG()
			
		elif type == "Composite":
			openAstro.type="Composite"
			openAstro.t_name=str(list["name"])
			openAstro.t_year=int(list["year"])
			openAstro.t_month=int(list["month"])
			openAstro.t_day=int(list["day"])
			openAstro.t_hour=float(list["hour"])
			openAstro.t_geolon=float(list["geolon"])
			openAstro.t_geolat=float(list["geolat"])
			openAstro.t_altitude=int(list["altitude"])
			openAstro.t_location=str(list["location"])
			openAstro.t_timezone=float(list["timezone"])
			openAstro.charttype="%s (%s)" % (openAstro.label["composite"],openAstro.t_name)
			openAstro.transit=False
			openAstro.makeSVG()
			
		elif type == "Combine":
			openAstro.type="Combine"
			openAstro.t_name=str(list["name"])
			openAstro.t_year=int(list["year"])
			openAstro.t_month=int(list["month"])
			openAstro.t_day=int(list["day"])
			openAstro.t_hour=float(list["hour"])
			openAstro.t_geolon=float(list["geolon"])
			openAstro.t_geolat=float(list["geolat"])
			openAstro.t_altitude=int(list["altitude"])
			openAstro.t_location=str(list["location"])
			openAstro.t_timezone=float(list["timezone"])
			
			#calculate combine between both utc times
			h,m,s = openAstro.decHour(openAstro.hour)
			dt1 = datetime.datetime(openAstro.year,openAstro.month,openAstro.day,h,m,s)
			h,m,s = openAstro.decHour(openAstro.t_hour)
			dt2 = datetime.datetime(openAstro.t_year,openAstro.t_month,openAstro.t_day,h,m,s)
			
			if dt1 > dt2:
				delta = dt1 - dt2
				hdelta = delta // 2
				combine = dt2 + hdelta
			else:
				delta = dt2 - dt1
				hdelta = delta // 2
				combine = dt1 + hdelta
			
			#take lon,lat middle
			openAstro.c_geolon = (openAstro.geolon + openAstro.t_geolon)/2.0
			openAstro.c_geolat = (openAstro.geolat + openAstro.t_geolat)/2.0
			openAstro.c_altitude = (openAstro.t_altitude + openAstro.altitude)/2.0
			openAstro.c_year = combine.year
			openAstro.c_month = combine.month
			openAstro.c_day = combine.day
			openAstro.c_hour = openAstro.decHourJoin(combine.hour,combine.minute,combine.second)
			
			openAstro.charttype="%s (%s)" % (openAstro.label["combine"],openAstro.t_name)
			openAstro.transit=False

			#set new date for printing in svg
			openAstro.year = openAstro.c_year
			openAstro.month = openAstro.c_month
			openAstro.day = openAstro.c_day
			openAstro.hour = openAstro.c_hour
			openAstro.geolat = openAstro.c_geolat
			openAstro.geolon = openAstro.c_geolon
			openAstro.timezone_str = zonetab.nearest_tz(openAstro.geolat,openAstro.geolon,zonetab.timezones())[2]
			#aware datetime object
			dt = zonetab.stdtime(openAstro.timezone_str, combine.year, combine.month, combine.day, combine.hour, combine.minute, combine.second)
			openAstro.timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
			openAstro.utcToLocal()
			openAstro.makeSVG()
		
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)			
		self.win_OD.destroy()		
	
	def openDatabaseDel(self, widget):
		#get name from selection
		model = self.win_OD_selection.get_selected()[0]
		iter = self.win_OD_selection.get_selected()[1]
		for i in range(len(self.DB)):
			if self.DB[i]["id"] == model.get_value(iter,3):
				self.ODDlist = self.DB[i]
		name = self.ODDlist["name"]
		dialog=gtk.Dialog(_('Question'),self.win_OD,gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		dialog.connect("close", lambda w,e: dialog.destroy())
		dialog.connect("response",self.openDatabaseDelDo)
		dialog.vbox.pack_start(gtk.Label(_('Are you sure you want to delete')+' '+name+'?'),True,True,0)
		dialog.show_all()
		return
	
	def openDatabaseDelDo(self, widget, response_id):
		if response_id == gtk.RESPONSE_ACCEPT:
			#get id from selection
			del_id = self.ODDlist["id"]
			#delete database entry
			sql='DELETE FROM event_natal WHERE id='+str(del_id)
			db.pquery([sql])
			dprint('deleted database entry: '+self.ODDlist["name"])
			widget.destroy()
			self.win_OD.destroy()
			self.openDatabase(self.window)
			self.updateUI()
		else:
			widget.destroy()
			dprint('rejected database deletion')
		return
	
	def openDatabaseOpen(self, widget):
		model = self.win_OD_selection.get_selected()[0]
		iter = self.win_OD_selection.get_selected()[1]
		for i in range(len(self.DB)):
			if self.DB[i]["id"] == model.get_value(iter,3):
				list = self.DB[i]
		openAstro.type="Radix"
		openAstro.charttype=openAstro.label["radix"]
		openAstro.transit=False
		self.updateChartList(widget, list)
		self.win_OD.destroy()
		return
	
	def openDatabaseEdit(self, widget):
		model = self.win_OD_selection.get_selected()[0]
		iter = self.win_OD_selection.get_selected()[1]
		for i in range(len(self.DB)):
			if self.DB[i]["id"] == model.get_value(iter,3):
				self.oDE_list = self.DB[i]
		openAstro.type="Radix"
		openAstro.charttype=openAstro.label["radix"]
		openAstro.transit=False
		self.updateChartList(widget, self.oDE_list)
		self.eventData( widget , edit=True )
		return		

	def openDatabaseEditAsk(self, widget):
		#check for duplicate name without duplicate id
		en = db.getDatabase()
		for i in range(len(en)):
			if en[i]["name"] == self.name.get_text() and self.oDE_list["id"] != en[i]["id"]:
				dialog=gtk.Dialog(_('Duplicate'),self.window2,0,(gtk.STOCK_OK, gtk.RESPONSE_DELETE_EVENT))
				dialog.set_icon_from_file(cfg.iconWindow)			
				dialog.connect("response", lambda w,e: dialog.destroy())				
				dialog.connect("close", lambda w,e: dialog.destroy())
				dialog.vbox.pack_start(gtk.Label(_('There is allready an entry for this name, please choose another')),True,True,0)
				dialog.show_all()				
				return
		#ask for confirmation
		dialog=gtk.Dialog(_('Question'),self.window2,gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		dialog.set_icon_from_file(cfg.iconWindow)
		dialog.connect("close", lambda w,e: dialog.destroy())
		dialog.connect("response",self.openDatabaseEditSave)
		dialog.vbox.pack_start(gtk.Label(_('Are you sure you want to Save?')),True,True,0)
		dialog.show_all()	
		return	
	
	def openDatabaseEditSave(self, widget, response_id):
		if response_id == gtk.RESPONSE_ACCEPT:
			#update chart data
			self.updateChartData()
			#set query to save			
			sql = 'UPDATE event_natal SET name=?,year=?,month=?,day=?,hour=?,\
				geolon=?,geolat=?,altitude=?,location=?,timezone=?,notes=?,\
				image=?,countrycode=?,timezonestr=?,geonameid=? WHERE id=?'
			values = (openAstro.name,openAstro.year,openAstro.month,
				openAstro.day,openAstro.hour,openAstro.geolon,openAstro.geolat,openAstro.altitude,
				openAstro.location,openAstro.timezone,'','',openAstro.countrycode,
				openAstro.timezonestr,openAstro.geonameid,self.oDE_list["id"])
			db.pquery([sql],[values])
			dprint('saved edit to database: '+openAstro.name)
			widget.destroy()
			self.window2.destroy()
			self.win_OD.destroy()
			self.openDatabase( self.window )
			self.updateUI()
		else:
			widget.destroy()
			dprint('rejected save to database')
		return
		
	def doPrint(self, widget):	
		self.print_settings = None
		print_op = gtk.PrintOperation()
		print_op.set_unit(gtk.UNIT_PIXEL)
		if self.print_settings != None: 
			print_op.set_print_settings(self.print_settings)

		print_op.connect("begin_print", self.doPrintBegin)
		print_op.connect("draw_page", self.doPrintDraw)
		print_op.set_export_filename("/tmp/OAOUT.pdf")
		res = print_op.run(gtk.PRINT_OPERATION_ACTION_EXPORT, self.window)
		#res = print_op.run(gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG, self.window)
		
		if res == gtk.PRINT_OPERATION_RESULT_ERROR:
			error_dialog = gtk.MessageDialog(parent,
                                          gtk.DIALOG_DESTROY_WITH_PARENT,
                                          gtk.MESSAGE_ERROR,
      					  gtk.BUTTONS_CLOSE,
      					  "Error printing:\n")
			error_dialog.connect("response", lambda w,id: w.destroy())
			error_dialog.show()
			
		elif res == gtk.PRINT_OPERATION_RESULT_APPLY:
			self.print_settings = print_op.get_print_settings()


			
		#gtkunixprint
		import gtkunixprint
		gup = gtkunixprint.PrintUnixDialog("Printing OpenAstro.org",self.window)
		res = gup.run()
		if res == gtk.RESPONSE_OK:
			#print button
			printer = gup.get_selected_printer()
			settings = gup.get_settings()
			page_setup = gtk.print_run_page_setup_dialog(self.window,gup.get_page_setup(),settings)
			
			#print job
			printjob = gtkunixprint.PrintJob("openastro-pj", printer, settings, page_setup)
			
			surface = printjob.get_surface()
			context = cairo.Context(surface)
			svg = rsvg.Handle(cfg.tempfilenameprint)
			svg.render_cairo(context)
			surface.finish()


			#send file to print job
			def printer_callback(print_job, data, errormsg):
				print "printing job: %s" %(print_job.get_title())
				if errormsg:
					print errormsg
					
			if printer.accepts_pdf():
				#printer accepts PDF
				print "Printing PDF file /tmp/OAOUT.pdf"
				printjob.send(printer_callback)
				#printjob.set_source_file("/tmp/OAOUT.pdf")
			elif printer.accepts_ps():
				#printer accepts PS
				print "PS printing not made yet"
			else:
				#no format support
				print "Printer does not support PDF or PS printing"
			
			gup.destroy()		
			
		elif res == gtk.RESPONSE_APPLY:
			#print preview button
			print "print preview button?"
			gup.destroy()
		else:
			print "cancelled print"
			gup.destroy()
				

	def doPrintBegin(self, operation, context):
		operation.set_n_pages(1)
		operation.set_use_full_page(False)
		ps = gtk.PageSetup()
		ps.set_orientation(gtk.PAGE_ORIENTATION_PORTRAIT)
		ps.set_paper_size_and_default_margins(gtk.PaperSize(gtk.PAPER_NAME_A4))

		if self.print_settings is None:
			settings = gtk.PrintSettings()
		else:
			settings = self.print_settings
			
		#for selecting other paper types than A4
		#ps = gtk.print_run_page_setup_dialog(self.window,None,settings)
		operation.set_default_page_setup(ps)
	
	def doPrintDraw(self, operation, context, page_nr):
		cr = context.get_cairo_context()
		printing={}
		printing['pagenum']=page_nr
		printing['width']=context.get_width()
		printing['height']=context.get_height()
		printing['dpi_x']=context.get_dpi_x()
		printing['dpi_y']=context.get_dpi_y()	
		
		#make printing svg
		openAstro.makeSVG(printing=printing)
		
		#draw svg for printing
		rsvg.set_default_dpi(900)
		svg = rsvg.Handle(cfg.tempfilenameprint)
		svg.render_cairo(cr)
		
	
	"""
	
	Menu item for general configuration
	
	settingsConfiguration
	settingsConfigurationSubmit	
	
	"""
	
	def settingsConfiguration(self, widget):
		# create a new window
		self.win_SC = gtk.Dialog()
		self.win_SC.set_icon_from_file(cfg.iconWindow)
		self.win_SC.set_title(_("General Configuration"))
		self.win_SC.connect("delete_event", lambda w,e: self.win_SC.destroy())
		self.win_SC.move(200,150)
		self.win_SC.set_border_width(5)
		self.win_SC.set_size_request(450,450)
		
		#data dictionary
		data = {}
		
		#create a table
		table = gtk.Table(8, 1, False)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		table.set_border_width(10)
		
		#description

		#options
		table.attach(gtk.Label(_("Use Online Geocoding (ws.geonames.org)")), 0, 1, 0, 1, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		data['use_geonames.org'] = gtk.CheckButton()
		table.attach(data['use_geonames.org'], 0, 1, 1, 2, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		if db.getAstrocfg('use_geonames.org') == "1":
			data['use_geonames.org'].set_active(True)
		
		#house system
		data['houses_system'] = gtk.combo_box_new_text()
		table.attach(gtk.Label(_('Houses System')), 0, 1, 2, 3, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		table.attach(data['houses_system'], 0, 1, 3, 4, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		hsys={
				"P":"Placidus",
				"K":"Koch",
				"O":"Porphyrius",
				"R":"Regiomontanus",
				"C":"Campanus",
				"A":"Equal (Cusp 1 = Asc)",
				"V":"Vehlow Equal (Asc = 1/2 House 1)",
				"W":"Whole",
				"X":"Axial Rotation",
				"H":"Azimuthal or Horizontal System",
				"T":"Polich/Page ('topocentric system')",
				"B":"Alcabitus",
				"G":"Gauquelin sectors",
				"M":"Morinus"
				}		
		self.houses_list=["P","K","O","R","C","A","V","W","X","H","T","B","G","M"]
		active=0
		for n in range(len(self.houses_list)):
			data['houses_system'].append_text(hsys[self.houses_list[n]])
			if db.astrocfg['houses_system'] == self.houses_list[n]:
				active = n
		data['houses_system'].set_active(active)
		
		#position calculation (geo,truegeo,topo,helio)		
		data['postype'] = gtk.combo_box_new_text()
		table.attach(gtk.Label(_('Position Calculation')), 0, 1, 4, 5, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		table.attach(data['postype'], 0, 1, 5, 6, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		postype={
		
				"geo":openAstro.label["apparent_geocentric"]+" "+_("(default)"),
				"truegeo":openAstro.label["true_geocentric"],
				"topo":openAstro.label["topocentric"],
				"helio":openAstro.label["heliocentric"]
				}		
		self.postype_list=["geo","truegeo","topo","helio"]
		active=0
		for n in range(len(self.postype_list)):
			data['postype'].append_text(postype[self.postype_list[n]])
			if db.astrocfg['postype'] == self.postype_list[n]:
				active = n
		data['postype'].set_active(active)

		#chart view (traditional,european)		
		data['chartview'] = gtk.combo_box_new_text()
		table.attach(gtk.Label(_('Chart View')), 0, 1, 6, 7, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		table.attach(data['chartview'], 0, 1, 7, 8, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		chartview={
				"traditional":_("Planets in Zodiac"),
				"european":_("Planets around Zodiac")
				}		
		self.chartview_list=["traditional","european"]
		active=0
		for n in range(len(self.chartview_list)):
			data['chartview'].append_text(chartview[self.chartview_list[n]])
			if db.astrocfg['chartview'] == self.chartview_list[n]:
				active = n
		data['chartview'].set_active(active)


		#zodiac type (tropical, sidereal)	
		data['zodiactype'] = gtk.combo_box_new_text()
		table.attach(gtk.Label(_('Zodiac Type')), 0, 1, 8, 9, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		table.attach(data['zodiactype'], 0, 1, 10, 11, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		chartview={
				"tropical":_("Tropical"),
				"sidereal":_("Sidereal")
				}		
		self.zodiactype_list=["tropical","sidereal"]
		active=0
		for n in range(len(self.zodiactype_list)):
			data['zodiactype'].append_text(chartview[self.zodiactype_list[n]])
			if db.astrocfg['zodiactype'] == self.zodiactype_list[n]:
				active = n
		data['zodiactype'].set_active(active)

		
		#sidereal mode	
		data['siderealmode'] = gtk.combo_box_new_text()
		if db.astrocfg['zodiactype'] != 'sidereal':
			data['siderealmode'].set_sensitive(False)
		def zodiactype_changed(button):
			if self.zodiactype_list[data['zodiactype'].get_active()] != 'sidereal':
				data['siderealmode'].set_sensitive(False)
			else:
				data['siderealmode'].set_sensitive(True)
		data['zodiactype'].connect("changed",zodiactype_changed)
		table.attach(gtk.Label(_('Sidereal Mode')), 0, 1, 12, 13, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)		
		table.attach(data['siderealmode'], 0, 1, 14, 15, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		self.siderealmode_chartview={
				"FAGAN_BRADLEY":_("Fagan Bradley"),
				"LAHIRI":_("Lahiri"),
				"DELUCE":_("Deluce"),
				"RAMAN":_("Ramanb"),
				"USHASHASHI":_("Ushashashi"),
				"KRISHNAMURTI":_("Krishnamurti"),
				"DJWHAL_KHUL":_("Djwhal Khul"),
				"YUKTESHWAR":_("Yukteshwar"),
				"JN_BHASIN":_("Jn Bhasin"),
				"BABYL_KUGLER1":_("Babyl Kugler 1"),
				"BABYL_KUGLER2":_("Babyl Kugler 2"),
				"BABYL_KUGLER3":_("Babyl Kugler 3"),
				"BABYL_HUBER":_("Babyl Huber"),
				"BABYL_ETPSC":_("Babyl Etpsc"),
				"ALDEBARAN_15TAU":_("Aldebaran 15Tau"),
				"HIPPARCHOS":_("Hipparchos"),
				"SASSANIAN":_("Sassanian"),
				"J2000":_("J2000"),
				"J1900":_("J1900"),
				"B1950":_("B1950")
				}		
		self.siderealmode_list=["FAGAN_BRADLEY",
				"LAHIRI",
				"DELUCE",
				"RAMAN",
				"USHASHASHI",
				"KRISHNAMURTI",
				"DJWHAL_KHUL",
				"YUKTESHWAR",
				"JN_BHASIN",
				"BABYL_KUGLER1",
				"BABYL_KUGLER2",
				"BABYL_KUGLER3",
				"BABYL_HUBER",
				"BABYL_ETPSC",
				"ALDEBARAN_15TAU",
				"HIPPARCHOS",
				"SASSANIAN",
				"J2000",
				"J1900",
				"B1950"]
		active=0
		for n in range(len(self.siderealmode_list)):
			data['siderealmode'].append_text(self.siderealmode_chartview[self.siderealmode_list[n]])
			if db.astrocfg['siderealmode'] == self.siderealmode_list[n]:
				active = n
		data['siderealmode'].set_active(active)
		
		#language		
		data['language'] = gtk.combo_box_new_text()
		table.attach(gtk.Label(_('Language')), 0, 1, 16, 17, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		table.attach(data['language'], 0, 1, 18, 19, xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=10)
		
		data['language'].append_text(_("Default"))
		active=0
		for i in range(len(LANGUAGES)):
			data['language'].append_text(db.lang_label[LANGUAGES[i]])
			if db.astrocfg['language'] == LANGUAGES[i]:
				active = i+1
		data['language'].set_active(active)			
		
		#make the ui layout with ok button
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.set_border_width(5)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.win_SC.vbox.pack_start(scrolledwindow, True, True, 0)
		scrolledwindow.add_with_viewport(table)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsConfigurationSubmit, data)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SC.action_area.pack_start(button, True, True, 0)
		button.grab_default()		

		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SC.destroy())
		self.win_SC.action_area.pack_start(button, True, True, 0)

		self.win_SC.show_all()			
		return
	
	def settingsConfigurationSubmit(self, widget, data):
		update=False
		if data['use_geonames.org'].get_active():
			db.setAstrocfg("use_geonames.org","1")
		else:
			db.setAstrocfg("use_geonames.org","0")
		#houses system
		if self.houses_list[data['houses_system'].get_active()] != db.astrocfg['houses_system']:
			update=True
		db.setAstrocfg("houses_system",self.houses_list[data['houses_system'].get_active()])
		#position calculation
		if self.postype_list[data['postype'].get_active()] != db.astrocfg['postype']:
			update=True
		db.setAstrocfg("postype",self.postype_list[data['postype'].get_active()])
		#chart view
		if self.chartview_list[data['chartview'].get_active()] != db.astrocfg['chartview']:
			update=True
		db.setAstrocfg("chartview",self.chartview_list[data['chartview'].get_active()])
		#zodiac type
		if self.zodiactype_list[data['zodiactype'].get_active()] != db.astrocfg['zodiactype']:
			update=True
		db.setAstrocfg("zodiactype",self.zodiactype_list[data['zodiactype'].get_active()])
		#sidereal mode
		if self.siderealmode_list[data['siderealmode'].get_active()] != db.astrocfg['siderealmode']:
			update=True
		db.setAstrocfg("siderealmode",self.siderealmode_list[data['siderealmode'].get_active()])
		#language
		model = data['language'].get_model()
		active = data['language'].get_active()
		if active == 0:
			active_lang = "default"
		else:
			active_lang = LANGUAGES[active-1]
		if active_lang != db.astrocfg['language']:
			update=True
		db.setAstrocfg("language",active_lang)
		
		#set language to be used
		db.setLanguage(active_lang)
		self.updateUI()
		
		#updatechart
		if update:
			self.updateChart()		
		self.win_SC.destroy()
		return

		
	"""
	
	Menu item to set home location:
	
	settingsLocation
	settingsLocationSubmit
	settingsLocationApply
	settingsLocationDestroy
	
	"""

	def settingsLocation(self, widget):
		# check connection to the internet
		self.checkInternetConnection()
		# enable settingslocationmode
		self.settingsLocationMode = True
		# create a new window
		self.win_SL = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.win_SL.set_icon_from_file(cfg.iconWindow)
		self.win_SL.set_title(_("Please Set Your Home Location"))
		self.win_SL.connect("delete_event", lambda w,e: self.settingsLocationDestroy())
		self.win_SL.move(150,150)
		self.win_SL.set_border_width(10)
		
		#create a table
		table = gtk.Table(5, 2, False)
		table.set_col_spacings(15)
		table.set_row_spacings(15)
		self.win_SL.add(table)

		#display of location (non editable)
		table.attach(gtk.Label(_('Location')+':'), 0, 1, 1, 2)
		self.LLoc=gtk.Label(openAstro.home_location)
		table.attach(self.LLoc, 1, 2, 1, 2)
		
		table.attach(gtk.Label(_('Latitude')+':'), 0, 1, 2, 3)
		self.LLat=gtk.Label(openAstro.home_geolat)
		table.attach(self.LLat, 1, 2, 2, 3)

		table.attach(gtk.Label(_('Longitude')+':'), 0, 1, 3, 4)
		self.LLon=gtk.Label(openAstro.home_geolon)
		table.attach(self.LLon, 1, 2, 3, 4)
		
		#use geocoders if we have an internet connection else geonames database
		if self.iconn:
			#entry for location (editable)
			hbox=gtk.HBox()
			label=gtk.Label(_("City")+": ")
			hbox.pack_start(label)
			self.geoLoc = gtk.Entry(100)
			self.geoLoc.set_width_chars(30)
			self.geoLoc.set_text(openAstro.home_location.partition(',')[0])
			hbox.pack_start(self.geoLoc)
			label=gtk.Label(" "+_("Country-code")+": ")
			hbox.pack_start(label)
			self.geoCC = gtk.Entry(2)
			self.geoCC.set_width_chars(2)
			self.geoCC.set_text(openAstro.home_countrycode)
			hbox.pack_start(self.geoCC)	
			table.attach(hbox, 0, 2, 0, 1)
		else:
			hbox=gtk.HBox()
			table.attach(hbox, 0, 2, 0, 1)
			#get nearest home
			self.GEON_nearest = db.gnearest(openAstro.geolat,openAstro.geolon)
			#continents
			self.contbox = gtk.ComboBox()
			self.contstore = gtk.ListStore(str,str)
			cell = gtk.CellRendererText()
			self.contbox.pack_start(cell)
			self.contbox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.contbox)
			self.contbox.set_wrap_width(1)

			sql = 'SELECT * FROM continent ORDER BY name ASC'
			db.gquery(sql)
			continentinfo=[]
			i = 0
			activecont = 3
			for row in db.gcursor:
				if row['code'] == self.GEON_nearest['continent']:
					activecont=i
					self.GEON_nearest['continent']=None
				self.contstore.append([row['name'],row['code']])
				i += 1
			db.gclose()
			self.contbox.set_model(self.contstore)
        
			#countries
			self.countrybox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.countrybox.pack_start(cell)
			self.countrybox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.countrybox)
			self.countrybox.set_wrap_width(1) 
			self.countrybox.connect('changed', self.eventDataChangedCountrybox)

			#provinces
			self.provbox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.provbox.pack_start(cell)
			self.provbox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.provbox)
			self.provbox.set_wrap_width(1) 
			self.provbox.connect('changed', self.eventDataChangedProvbox)

			#cities
			self.citybox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.citybox.pack_start(cell)
			self.citybox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.citybox)
			self.citybox.set_wrap_width(2) 
			self.citybox.connect('changed', self.eventDataChangedCitybox)

			self.contbox.connect('changed', self.eventDataChangedContbox)
			self.contbox.set_active(activecont)		

		#buttonbox
		buttonbox = gtk.HBox(False, 5)
		table.attach(buttonbox, 1, 2, 4, 5)
 
  		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsLocationSubmit)
		button.set_flags(gtk.CAN_DEFAULT)
		buttonbox.pack_start(button,False,False,0)
		button.grab_default()
		
		#Test button
		button = gtk.Button(_('Test'),gtk.STOCK_APPLY)
		button.connect("clicked", self.settingsLocationApply)
		buttonbox.pack_start(button,False,False,0)
		
		#Cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.settingsLocationDestroy())
		buttonbox.pack_start(button,False,False,0)
		
		#show all
		self.win_SL.show_all()
	
	def settingsLocationSubmit(self, widget):
		self.settingsLocationApply(widget)
		if self.geoLocFound:
			self.settingsLocationDestroy()
			return
		else:
			return
	
	def settingsLocationApply(self, widget):
		#check for internet connection to decide geocode/database
		self.geoLocFound = True
		if self.iconn:
			result = geoname.search(self.geoLoc.get_text(),self.geoCC.get_text())
			if result:
				self.geoLocFound = True			
				lat=float(result[0]['lat'])
				lon=float(result[0]['lng'])
				tzstr=result[0]['timezonestr']
				cc=result[0]['countryCode']
				loc='%s, %s' % (result[0]['name'],result[0]['countryName'])
				dprint('settingsLocationApply: %s found; %s %s %s' % (self.geoLoc.get_text(), lat,lon,loc))
			else:
				self.geoLocFound = False
				#revert to defaults
				lat=openAstro.geolat
				lon=openAstro.geolon
				loc=openAstro.location
				cc=openAstro.countrycode
				tzstr=openAstro.timezonestr
				dprint('settingsLocationApply: %s not found, reverting to defaults' % self.geoLoc.get_text() )
				self.geoLoc.set_text('City Not Found, Try Again!')
				return
		else:
			lat = float(self.GEON_lat)
			lon = float(self.GEON_lon)
			loc = self.GEON_loc
			cc = self.GEON_cc
			tzstr = self.GEON_tzstr
		
		#apply settings to database
		db.setSettingsLocation(lat,lon,loc,cc,tzstr)
		openAstro.home_location=loc
		openAstro.home_geolat=lat
		openAstro.home_geolon=lon
		openAstro.home_countrycode=cc
		openAstro.home_timezonestr=tzstr
		openAstro.location=loc
		openAstro.timezonestr=tzstr
		openAstro.geolat=lat
		openAstro.geolon=lon
		openAstro.countrycode=cc
		openAstro.transit=False
		openAstro.name=_("Here and Now")
		openAstro.type="Radix"
		self.LLat.set_text(str(lat))
		self.LLon.set_text(str(lon))
		self.LLoc.set_text(str(loc))
		
		#set defaults for chart creation
		now = datetime.datetime.now()
		dt = zonetab.stdtime(openAstro.timezonestr, now.year, now.month, now.day, now.hour, now.minute, now.second)
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()
		openAstro.name=_("Here and Now")
		openAstro.charttype=openAstro.label["radix"]
		openAstro.year=dt_utc.year
		openAstro.month=dt_utc.month
		openAstro.day=dt_utc.day
		openAstro.hour=openAstro.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		openAstro.timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
		openAstro.altitude=25
		openAstro.utcToLocal()

		self.updateChart()
		dprint('Setting New Home Location: %s %s %s' % (lat,lon,loc) )
		return
		
	def settingsLocationDestroy(self):
		self.settingsLocationMode = False
		self.win_SL.destroy()
		return

	"""
	
	Menu item to set aspect options
	
	settingsAspects
	settingsAspectsSubmit
	
	"""
			
	def settingsAspects(self, widget):
		# create a new window
		self.win_SA = gtk.Dialog()
		self.win_SA.set_icon_from_file(cfg.iconWindow)
		self.win_SA.set_title(_("Aspect Settings"))
		self.win_SA.connect("delete_event", lambda w,e: self.win_SA.destroy())
		self.win_SA.move(150,150)
		self.win_SA.set_border_width(5)
		self.win_SA.set_size_request(550,450)
		
		#create a table
		table = gtk.Table(len(openAstro.aspects)-3, 6, False)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		table.set_border_width(10)
		
		#description
		label = gtk.Label(_("Deg"))
		table.attach(label, 1, 2, 0, 1, xoptions=gtk.FILL, xpadding=10)
		label = gtk.Label(_("Aspect Name"))
		table.attach(label, 2, 3, 0, 1, xoptions=gtk.FILL, xpadding=10)
		label = gtk.Label(_("Visible\nin Circle"))
		table.attach(label, 3, 4, 0, 1, xoptions=gtk.FILL, xpadding=10)
		label = gtk.Label(_("Visible\nin Grid"))
		table.attach(label, 4, 5, 0, 1, xoptions=gtk.FILL, xpadding=10)
		label = gtk.Label(_("Orb"))
		table.attach(label, 5, 6, 0, 1, xoptions=gtk.FILL, xpadding=10)		
		
		data = []
		x=1
		for i in range(len(openAstro.aspects)):
			#0=degree, 1=name, 2=color, 3=is_major, 4=orb
			data.append({})
			data[-1]['icon'] = gtk.Image()
			filename=os.path.join(cfg.iconAspects,str(openAstro.aspects[i]['degree'])+'.svg')
			data[-1]['icon'].set_from_file(filename)
			data[-1]['degree'] = openAstro.aspects[i]['degree']
			data[-1]['degree_str'] = gtk.Label(str(openAstro.aspects[i]['degree']))
			data[-1]['name'] = gtk.Entry()
			data[-1]['name'].set_max_length(25)
			data[-1]['name'].set_width_chars(15)
			data[-1]['name'].set_text(openAstro.aspects[i]['name'])
			table.attach(data[-1]['icon'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(data[-1]['degree_str'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(data[-1]['name'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			data[-1]['visible'] = gtk.CheckButton()
			if openAstro.aspects[i]['visible'] is 1:
				data[-1]['visible'].set_active(True)
			table.attach(data[-1]['visible'], 3, 4, x, x+1, xoptions=gtk.EXPAND, xpadding=2, ypadding=2)
			data[-1]['visible_grid'] = gtk.CheckButton()
			if openAstro.aspects[i]['visible_grid'] is 1:
				data[-1]['visible_grid'].set_active(True)
			table.attach(data[-1]['visible_grid'], 4, 5, x, x+1, xoptions=gtk.EXPAND, xpadding=2, ypadding=2)
			data[-1]['orb'] = gtk.Entry(4)
			data[-1]['orb'].set_width_chars(4)
			data[-1]['orb'].set_text(str(openAstro.aspects[i]['orb']))
			table.attach(data[-1]['orb'], 5, 6, x, x+1, xoptions=gtk.FILL, xpadding=10)					
			x=x+1
		
		#make the ui layout with ok button
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.set_border_width(5)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.win_SA.vbox.pack_start(scrolledwindow, True, True, 0)
		scrolledwindow.add_with_viewport(table)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsAspectsSubmit, data)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SA.action_area.pack_start(button, True, True, 0)
		button.grab_default()		

		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SA.destroy())
		self.win_SA.action_area.pack_start(button, True, True, 0)

		self.win_SA.show_all()		
		return
	
	def settingsAspectsSubmit(self, widget, data):
		query=[]
		for i in range(len(data)):
		
			if data[i]['visible'].get_active():
				active = 1
			else:
				active = 0
				
			if data[i]['visible_grid'].get_active():
				active_grid = 1
			else:
				active_grid = 0
			
			orb = float(data[i]['orb'].get_text().replace(',','.'))
			if orb == int(orb):
				orb = int(orb)
			
			sql = 'UPDATE settings_aspect SET '
			sql += 'name = "%s", visible = %s' % (data[i]['name'].get_text(),active)
			sql += ', visible_grid = %s, orb = "%s"' % (active_grid,orb)
			sql += ' WHERE degree = '+str(data[i]['degree'])
			query.append(sql)

		#query
		db.query(query)
		#update chart
		self.updateChart()
		#destroy window
		self.win_SA.destroy()
	
	"""
	
	Menu item to edit options for planets
	
	settingsPlanets
	settingsPlanetsSubmit	
	
	"""	
		
	def settingsPlanets(self, obj):
		# create a new window
		self.win_SP = gtk.Dialog()
		self.win_SP.set_icon_from_file(cfg.iconWindow)
		self.win_SP.set_title(_("Planets & Angles Settings"))
		self.win_SP.connect("delete_event", lambda w,e: self.win_SP.destroy())
		self.win_SP.move(150,150)
		self.win_SP.set_border_width(5)
		self.win_SP.set_size_request(470,450)
		
		#create a table
		table = gtk.Table(len(openAstro.planets)-3, 4, False)
		table.set_border_width(10)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		
		#description
		table.set_row_spacing(0,8)
		label = gtk.Label(_("Planet Label"))
		table.attach(label, 0, 1, 0, 1)
		label = gtk.Label(_("Symbol"))
		table.attach(label, 1, 2, 0, 1, xoptions=gtk.SHRINK, xpadding=10)
		label = gtk.Label(_("Aspect Line"))
		table.attach(label, 2, 3, 0, 1, xoptions=gtk.SHRINK, xpadding=10)
		label = gtk.Label(_("Aspect Grid"))
		table.attach(label, 3, 4, 0, 1, xoptions=gtk.SHRINK, xpadding=10)
						
		data = []
		x=1
		for i in range(len(openAstro.planets)):
			#planets to skip: 11=true node, 13=osc. apogee, 14=earth, 21=intp. apogee, 22=intp. perigee
			#angles: 23=Asc, 24=Mc, 25=Ds, 26=Ic
			#points: 27=pars fortuna
			if i is 11 or i is 13 or i is 14 or i is 21 or i is 22:
				continue
			#start of the angles			
			if i is 23 or i is 27:
				table.set_row_spacing(x-1,20)
				table.set_row_spacing(x,8)
				if i is 27:
					label = gtk.Label(_("Point Label"))
				else:
					label = gtk.Label(_("Angle Label"))	
				table.attach(label, 0, 1, x, x+1, xoptions=gtk.SHRINK, xpadding=10)
				label = gtk.Label(_("Symbol"))
				table.attach(label, 1, 2, x, x+1, xoptions=gtk.SHRINK, xpadding=10)
				label = gtk.Label(_("Aspect Line"))
				table.attach(label, 2, 3, x, x+1, xoptions=gtk.SHRINK, xpadding=10)
				label = gtk.Label(_("Aspect Grid"))
				table.attach(label, 3, 4, x, x+1, xoptions=gtk.SHRINK, xpadding=10)				
				x=x+1
			data.append({})
			data[-1]['id'] = openAstro.planets[i]['id']
			data[-1]['label'] = gtk.Entry()
			data[-1]['label'].set_max_length(25)
			data[-1]['label'].set_width_chars(15)
			data[-1]['label'].set_text(openAstro.planets[i]['label'])
			#data[-1]['label'].set_alignment(xalign=0.0, yalign=0.5)
			table.attach(data[-1]['label'], 0, 1, x, x+1, xoptions=gtk.SHRINK, xpadding=10)
			data[-1]['visible'] = gtk.CheckButton()
			if openAstro.planets[i]['visible'] is 1:
				data[-1]['visible'].set_active(True)
			table.attach(data[-1]['visible'], 1, 2, x, x+1, xoptions=gtk.SHRINK, xpadding=2, ypadding=2)
			
			data[-1]['visible_aspect_line'] = gtk.CheckButton()
			if openAstro.planets[i]['visible_aspect_line'] is 1:
				data[-1]['visible_aspect_line'].set_active(True)
			table.attach(data[-1]['visible_aspect_line'], 2, 3, x, x+1, xoptions=gtk.SHRINK, xpadding=2, ypadding=2)	
			
			data[-1]['visible_aspect_grid'] = gtk.CheckButton()
			if openAstro.planets[i]['visible_aspect_grid'] is 1:
				data[-1]['visible_aspect_grid'].set_active(True)
			table.attach(data[-1]['visible_aspect_grid'], 3, 4, x, x+1, xoptions=gtk.SHRINK, xpadding=2, ypadding=2)	
			x=x+1
		
		#make the ui layout with ok button
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.set_border_width(5)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.win_SP.vbox.pack_start(scrolledwindow, True, True, 0)
		scrolledwindow.add_with_viewport(table)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsPlanetsSubmit, data)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SP.action_area.pack_start(button, True, True, 0)
		button.grab_default()
		
		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SP.destroy())
		self.win_SP.action_area.pack_start(button, True, True, 0)
		
		self.win_SP.show_all()		
		return
	
	def settingsPlanetsSubmit(self, widget, data):
		query=[]
		for i in range(len(data)):
			sql = 'UPDATE settings_planet SET label = "%s"'%(data[i]['label'].get_text())
			radio={"visible":0,"visible_aspect_line":0,"visible_aspect_grid":0}
			for key,val in radio.iteritems():
				if data[i][key].get_active():
					radio[key]=1
				sql += ', %s = %s' % (key,radio[key])
			sql += ' WHERE id = '+str(data[i]['id'])
			query.append(sql)

		#query
		db.query(query)
		#update chart
		self.updateChart()
		#destroy window
		self.win_SP.destroy()


	"""
	
	Menu item to set color options
	
	settingsColors
	settingsColorsSubmit
	
	"""
	
	def settingsColorsReset(self, widget, id):
		self.SCdata[id]['code'].set_text(db.defaultColors[self.SCdata[id]['key']])
		self.SCdata[id]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(db.defaultColors[self.SCdata[id]['key']]))
		return
			
	def settingsColors(self, widget):
		# initialize settings colors selector
		self.colorseldlg = None
				
		# create a new window
		self.win_SC = gtk.Dialog()
		self.win_SC.set_icon_from_file(cfg.iconWindow)
		self.win_SC.set_title(_("Color Settings"))
		self.win_SC.connect("delete_event", lambda w,e: self.win_SC.destroy())
		self.win_SC.move(150,150)
		self.win_SC.set_border_width(5)
		self.win_SC.set_size_request(470,450)
		
		#create a table
		table = gtk.Table(24, 4, False)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		table.set_border_width(10)
		
		#data to be processed
		self.SCdata = []
		delimiter="--------------------------------------------"
		
		#Zodiac background colors
		table.attach(gtk.Label(delimiter),0,4,0,1,xoptions=gtk.FILL,xpadding=10)
		table.attach(gtk.Label(_("Zodiac Background Colors")),0,4,1,2,xoptions=gtk.FILL,xpadding=10)
		table.attach(gtk.Label(delimiter),0,4,2,3,xoptions=gtk.FILL,xpadding=10)
		x=3	
		for i in range(12):
			self.SCdata.append({})
			self.SCdata[-1]['key']="zodiac_bg_%s"%(i)
			self.SCdata[-1]['name']=gtk.Label(openAstro.zodiac[i])
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["zodiac_bg_%s"%(i)])
			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["zodiac_bg_%s"%(i)]))
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1
		
		#Circle and Line Colors
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(_("Circles and Lines Colors")),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		for i in range(3):
			self.SCdata.append({})
			self.SCdata[-1]['key']="zodiac_radix_ring_%s"%(i)
			self.SCdata[-1]['name']=gtk.Label("%s %s" %(_("Radix Ring"),(i+1)) )
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["zodiac_radix_ring_%s"%(i)])
			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["zodiac_radix_ring_%s"%(i)]))
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1
			
		for i in range(4):
			self.SCdata.append({})
			self.SCdata[-1]['key']="zodiac_transit_ring_%s"%(i)
			self.SCdata[-1]['name']=gtk.Label("%s %s" %(_("Transit Ring"),(i+1)) )
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["zodiac_transit_ring_%s"%(i)])
			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["zodiac_transit_ring_%s"%(i)]))
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1								
		
		self.SCdata.append({})
		self.SCdata[-1]['key']="houses_radix_line"
		self.SCdata[-1]['name']=gtk.Label(_("Cusp Radix"))
		self.SCdata[-1]['code'] = gtk.Entry(25)
		self.SCdata[-1]['code'].set_width_chars(10)
		self.SCdata[-1]['code'].set_text(openAstro.colors["houses_radix_line"])
		self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["houses_radix_line"]))
		self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
		self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
		self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
		self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
			
		table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
		x+=1
		
		self.SCdata.append({})
		self.SCdata[-1]['key']="houses_transit_line"
		self.SCdata[-1]['name']=gtk.Label(_("Cusp Transit"))
		self.SCdata[-1]['code'] = gtk.Entry(25)
		self.SCdata[-1]['code'].set_width_chars(10)
		self.SCdata[-1]['code'].set_text(openAstro.colors["houses_transit_line"])
		self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["houses_transit_line"]))
		self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
		self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
		self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
		self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
			
		table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
		table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
		x+=1		

		#Zodiac icon colors
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(_("Zodiac Icon Colors")),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		for i in range(12):
			self.SCdata.append({})
			self.SCdata[-1]['key']="zodiac_icon_%s"%(i)
			self.SCdata[-1]['name']=gtk.Label(openAstro.zodiac[i])
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["zodiac_icon_%s"%(i)])
			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["zodiac_icon_%s"%(i)]))
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1			

		#Aspects colors
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(_("Aspects Colors")),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		for i in range(len(openAstro.aspects)):
			self.SCdata.append({})
			self.SCdata[-1]['key']="aspect_%s"%(openAstro.aspects[i]['degree'])
			self.SCdata[-1]['name']=gtk.Label(openAstro.aspects[i]['name'])
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["aspect_%s"%(openAstro.aspects[i]['degree'])])

			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["aspect_%s"%(openAstro.aspects[i]['degree'])]))
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1

		#Planet colors
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(_("Planet Colors")),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		table.attach(gtk.Label(delimiter),0,4,x,x+1,xoptions=gtk.FILL,xpadding=10)
		x+=1
		for i in range(len(openAstro.planets)):
			self.SCdata.append({})
			self.SCdata[-1]['key']="planet_%s"%(i)
			self.SCdata[-1]['name']=gtk.Label(openAstro.planets[i]['name'])
			self.SCdata[-1]['code'] = gtk.Entry(25)
			self.SCdata[-1]['code'].set_width_chars(10)
			self.SCdata[-1]['code'].set_text(openAstro.colors["planet_%s"%(i)])
			self.SCdata[-1]['code'].modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(openAstro.colors["planet_%s"%(i)]) )
			self.SCdata[-1]['button'] = gtk.Button(stock=gtk.STOCK_SELECT_COLOR)
			self.SCdata[-1]['button'].connect("clicked", self.settingsColorsChanger, len(self.SCdata)-1)
			self.SCdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SCdata[-1]['reset'].connect("clicked", self.settingsColorsReset, len(self.SCdata)-1)
				
			table.attach(self.SCdata[-1]['name'], 0, 1, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['code'], 1, 2, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['button'], 2, 3, x, x+1, xoptions=gtk.FILL, xpadding=10)
			table.attach(self.SCdata[-1]['reset'], 3, 4, x, x+1, xoptions=gtk.FILL, xpadding=10)
			x+=1
		
		#make the ui layout with ok button
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.set_border_width(5)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.win_SC.vbox.pack_start(scrolledwindow, True, True, 0)
		scrolledwindow.add_with_viewport(table)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsColorsSubmit)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SC.action_area.pack_start(button, True, True, 0)
		button.grab_default()		

		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SC.destroy())
		self.win_SC.action_area.pack_start(button, True, True, 0)

		self.win_SC.show_all()		
		return
	
	def settingsColorsChanger(self, widget, count):
		input_color = gtk.gdk.color_parse(self.SCdata[count]["code"].get_text())
		
		self.colorseldlg = gtk.ColorSelectionDialog(_("Please select a color"))
		colorsel = self.colorseldlg.colorsel
		colorsel.set_current_color(input_color)
		colorsel.set_has_palette(True)
		response = self.colorseldlg.run()
		if response == gtk.RESPONSE_OK:
			output_color = colorsel.get_current_color()
			r=int( output_color.red / 257 )
			g=int( output_color.green / 257 )
			b=int( output_color.blue / 257 )
			self.SCdata[count]["code"].set_text("#%02X%02X%02X"%(r,g,b))
			self.SCdata[count]['code'].modify_base(gtk.STATE_NORMAL, output_color)
		self.colorseldlg.hide()

		return
	
	def settingsColorsSubmit(self, widget):
		query=[]
		for i in range(len(self.SCdata)):
			sql = 'UPDATE color_codes SET code = "%s"' % (self.SCdata[i]['code'].get_text())
			sql += ' WHERE name = "%s"' % (self.SCdata[i]['key'])
			query.append(sql)

		#query
		db.query(query)
		#update colors
		openAstro.colors = db.getColors()
		#update chart
		self.updateChart()
		#destroy window
		self.win_SC.destroy()



	"""
	
	Menu item to edit options for label
	
	settingsLabel
	settingsLabelSubmit	
	
	"""
		
	def settingsLabelReset(self, widget, id):
		self.SLdata[id]['value'].set_text(db.defaultLabel[self.SLdata[id]['name']])
		return
		
	def settingsLabel(self, obj):
		# create a new window
		self.win_SL = gtk.Dialog()
		self.win_SL.set_icon_from_file(cfg.iconWindow)
		self.win_SL.set_title(_("Label Settings"))
		self.win_SL.connect("delete_event", lambda w,e: self.win_SL.destroy())
		self.win_SL.move(150,150)
		self.win_SL.set_border_width(5)
		self.win_SL.set_size_request(540,500)
		
		#create a table
		table = gtk.Table(len(openAstro.label), 3, False)
		table.set_border_width(10)
		table.set_col_spacings(0)
		table.set_row_spacings(0)
		
		#description
		table.set_row_spacing(0,8)
		label = gtk.Label(_("Label"))
		table.attach(label, 0, 1, 0, 1)
		label = gtk.Label(_("Value"))
		table.attach(label, 1, 2, 0, 1, xoptions=gtk.SHRINK, xpadding=10)
						
		self.SLdata = []
		x=1
		keys = openAstro.label.keys()
		keys.sort()
        	for key in keys:
			value=openAstro.label[key]
			self.SLdata.append({})
			self.SLdata[-1]['name'] = key
			self.SLdata[-1]['value'] = gtk.Entry()
			self.SLdata[-1]['value'].set_max_length(50)
			self.SLdata[-1]['value'].set_width_chars(25)
			self.SLdata[-1]['value'].set_text(value)
			self.SLdata[-1]['reset'] = gtk.Button(_("Default"))
			self.SLdata[-1]['reset'].connect("clicked", self.settingsLabelReset, len(self.SLdata)-1)
			table.attach(gtk.Label(key), 0, 1, x, x+1, xoptions=gtk.SHRINK, xpadding=10)
			table.attach(self.SLdata[-1]['value'], 1, 2, x, x+1, xoptions=gtk.SHRINK, xpadding=2, ypadding=2)
			table.attach(self.SLdata[-1]['reset'], 2, 3, x, x+1, xoptions=gtk.SHRINK, xpadding=2, ypadding=2)
			x=x+1
		
		#make the ui layout with ok button
		scrolledwindow = gtk.ScrolledWindow()
		scrolledwindow.set_border_width(5)
		scrolledwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.win_SL.vbox.pack_start(scrolledwindow, True, True, 0)
		scrolledwindow.add_with_viewport(table)
		
		#ok button
		button = gtk.Button(stock=gtk.STOCK_OK)
		button.connect("clicked", self.settingsLabelSubmit, self.SLdata)
		button.set_flags(gtk.CAN_DEFAULT)		
		self.win_SL.action_area.pack_start(button, True, True, 0)
		button.grab_default()
		
		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.win_SL.destroy())
		self.win_SL.action_area.pack_start(button, True, True, 0)
		
		self.win_SL.show_all()		
		return
	
	def settingsLabelSubmit(self, widget, data):
		query=[]
		for i in range(len(data)):
			if data[i]['value'].get_text() != openAstro.label[data[i]['name']]:
				sql = 'UPDATE label SET value = "%s" WHERE name = "%s"'%(data[i]['value'].get_text(),data[i]['name'])
				query.append(sql)
		#query
		db.query(query)
		#update label
		openAstro.label = db.getLabel()	
		#update chart
		self.updateChart()
		#destroy window
		self.win_SL.destroy()


	"""
		
		Update the chart with input list data

	"""

	def updateChartList(self, b, list):
		openAstro.type="Radix"
		openAstro.charttype=openAstro.label["radix"]
		openAstro.name=str(list["name"])
		openAstro.year=int(list["year"])
		openAstro.month=int(list["month"])
		openAstro.day=int(list["day"])
		openAstro.hour=float(list["hour"])
		openAstro.geolon=float(list["geolon"])
		openAstro.geolat=float(list["geolat"])
		openAstro.altitude=int(list["altitude"])
		openAstro.location=str(list["location"])
		openAstro.timezone=float(list["timezone"])
		openAstro.countrycode=''
		if "countrycode" in list:
			openAstro.countrycode=list["countrycode"]
		if "timezonestr" in list:
			openAstro.timezonestr=list["timezonestr"]
		else:
			openAstro.timezonestr=db.gnearest(openAstro.geolat,openAstro.geolon)['timezonestr']
		openAstro.geonameid=None
		if "geonameid" in list:
			openAstro.geonameid=list['geonameid']
			
		openAstro.utcToLocal()
		openAstro.makeSVG()
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)

	def updateChart(self):
		openAstro.makeSVG()
		self.draw.queue_draw()
		self.draw.setSVG(self.tempfilename)	

	def updateChartData(self):
		#check for internet connection
		if self.iconn:
			result = geoname.search(self.geoLoc.get_text(),self.geoCC.get_text())
			if result:
				self.geoLocFound = True
				lat=float(result[0]['lat'])
				lon=float(result[0]['lng'])
				gid=int(result[0]['geonameId'])
				cc=result[0]['countryCode']
				tzstr=result[0]['timezonestr']
				loc='%s, %s' % (result[0]['name'],result[0]['countryName'])
				dprint('updateChartData: %s,%s found; %s %s %s' % (
					self.geoLoc.get_text(),self.geoCC.get_text(),lat,lon,loc))
			else:
				self.geoLocFound = False
				#revert to defaults
				lat=openAstro.geolat
				lon=openAstro.geolon
				loc=openAstro.location
				cc=openAstro.countrycode
				tzstr=openAstro.timezonestr
				gid=openAstro.geonameid
				dprint('updateChartData: %s,%s not found, reverting to defaults' % (
					self.geoLoc.get_text(),self.geoCC.get_text()) )
				self.geoLoc.set_text(_('City not found! Try Again.'))
				return
		else:
			#using geonames database
			self.geoLocFound = True
			lat = float(self.GEON_lat)
			lon = float(self.GEON_lon)
			loc = self.GEON_loc
			cc = self.GEON_cc
			tzstr = self.GEON_tzstr
			gid = self.GEON_id

		#calculate timezone
		openAstro.timezonestr = tzstr
		openAstro.geonameid = gid

		#aware datetime object local time (with timezone info)
		dt = zonetab.stdtime(openAstro.timezonestr, int(self.dateY.get_text()), int(self.dateM.get_text()), int(self.dateD.get_text()), int(self.eH.get_text()), int(self.eM.get_text()), int(self.eS.get_text()))
		
		#naive datetime object UTC
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()
		
		#set globals
		openAstro.year = dt_utc.year
		openAstro.month = dt_utc.month
		openAstro.day = dt_utc.day
		openAstro.hour = openAstro.decHourJoin(dt_utc.hour, dt_utc.minute, dt_utc.second)
		openAstro.timezone = float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds / 3600) )
		openAstro.name = self.name.get_text()
		
		#location
		openAstro.geolat=lat
		openAstro.geolon=lon
		openAstro.location=loc
		openAstro.countrycode=cc
		
		#update local time
		openAstro.utcToLocal()

		#update labels
		labelDateStr = str(openAstro.year_loc)+'-%(#1)02d-%(#2)02d' % {'#1':openAstro.month_loc,'#2':openAstro.day_loc}		
		self.labelDate.set_text(labelDateStr)		
		labelTzStr = '%(#1)02d:%(#2)02d:%(#3)02d' % {'#1':openAstro.hour_loc,'#2':openAstro.minute_loc,'#3':openAstro.second_loc} + openAstro.decTzStr(openAstro.timezone)				
		self.labelTz.set_text(labelTzStr)
		self.ename.set_text(openAstro.name)
		self.entry2.set_text(' %s: %s\n %s: %s\n %s: %s' % ( _('Latitude'),lat,_('Longitude'),lon,_('Location'),loc) )

	def updateUI(self):

		#remove old actiongroup
		try:		
			self.uimanager.remove_action_group(self.actiongroup)
		except AttributeError:
			pass
					
		#create new actiongroup
		self.actiongroup = gtk.ActionGroup('UIManagerExample')

		#remove old ui's
		try:		
			self.uimanager.remove_ui(self.ui_mid_history)
			self.uimanager.remove_ui(self.ui_mid_quickopendatabase)
		except AttributeError:
			pass
		
		#new merge id's
		self.ui_mid_history = self.uimanager.new_merge_id()
		self.ui_mid_quickopendatabase = self.uimanager.new_merge_id()

		# Add actions
		self.actiongroup.add_actions(self.actions)
		self.actiongroup.get_action('Quit').set_property('short-label', _('Quit') )

		self.actiongroup.add_radio_actions([
			('z80', None, '_80%', None,'80%', 0),
			('z100', gtk.STOCK_ZOOM_100, '_100%', None,'100%', 1),
         ('z150', None, '_150%', None,'150%', 2),
         ('z200', None, '_200%', None,'200%', 3),
         ], 1, self.zoom)
	
		#create history actions
		history=db.history
		history.reverse()
		for i in range(10):
			if i < len(history):
				label=history[i][1]
				visible=True
				list=history[i]
			else:
				label='empty'
				visible=False
				list=[]
			self.uimanager.add_ui(self.ui_mid_history, '/MenuBar/File/History', 'history%i'%(i), 'history%i'%(i), gtk.UI_MANAGER_MENUITEM, False)
			action=gtk.Action('history%i'%(i),label,None,False)
			action.connect('activate',self.updateChartList,list)
			action.set_visible(visible)			
			self.actiongroup.add_action(action)

		#create quickdatabaseopen actions
		self.DB = db.getDatabase()
		for i in range(len(self.DB)):
			self.uimanager.add_ui(self.ui_mid_quickopendatabase, '/MenuBar/Event/QuickOpenDatabase', 'quickopendatabase%s'%(i), 'quickopendatabase%s'%(i), gtk.UI_MANAGER_MENUITEM, False)
			action=gtk.Action('quickopendatabase%s'%(i),self.DB[i]["name"],None,False)
			action.connect('activate',self.updateChartList,self.DB[i])
			action.set_visible(True)
			self.actiongroup.add_action(action)
		
		#update uimanager
		self.uimanager.insert_action_group(self.actiongroup, 0)		
		self.uimanager.ensure_update()
		

	def eventDataNew(self, widget):
		#default location
		openAstro.location=openAstro.home_location
		openAstro.geolat=float(openAstro.home_geolat)
		openAstro.geolon=float(openAstro.home_geolon)
		openAstro.countrycode=openAstro.home_countrycode
		
		#timezone string, example Europe/Amsterdam
		now = datetime.datetime.now()
		openAstro.timezone_str = zonetab.nearest_tz(openAstro.geolat,openAstro.geolon,zonetab.timezones())[2]
		#aware datetime object
		dt = zonetab.stdtime(openAstro.timezone_str, now.year, now.month, now.day, now.hour, now.minute, now.second)
		#naive utc datetime object
		dt_utc = dt.replace(tzinfo=None) - dt.utcoffset()

		#Default
		openAstro.name=_("New Chart")
		openAstro.charttype=openAstro.label["radix"]
		openAstro.year=dt_utc.year
		openAstro.month=dt_utc.month
		openAstro.day=dt_utc.day
		openAstro.hour=openAstro.decHourJoin(dt_utc.hour,dt_utc.minute,dt_utc.second)
		openAstro.timezone=float( (dt.utcoffset().days * 24) + (dt.utcoffset().seconds/3600) )
		
		#Make locals
		openAstro.utcToLocal()
		
		#open editor
		self.eventData(widget, edit=False)
		return

	def eventData(self, widget, edit=False):
		# create a new window
		self.window2 = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window2.set_icon_from_file(cfg.iconWindow)
		self.window2.set_title(_("Edit Event Details"))
		self.window2.connect("delete_event", lambda w,e: self.window2.destroy())
		self.window2.move(150,150)
		self.window2.set_border_width(10)
		
		#check internet connection
		self.checkInternetConnection()		
		
		#create a table
		table = gtk.Table(5, 2, False)
		table.set_col_spacings(15)
		table.set_row_spacings(15)
		self.window2.add(table)
		
		#Name entry
		hbox = gtk.HBox(False,5)
		table.attach(hbox,0,1,0,1)

		label=gtk.Label(_("Name")+":")
		hbox.pack_start(label,False,False,0)

		self.name = gtk.Entry()
		self.name.set_max_length(50)
		self.name.set_width_chars(25)
		self.name.set_text(openAstro.name)
		hbox.pack_start(self.name,False,False,0)
		
		#name entry ( non editable)
		self.ename = gtk.Label(openAstro.name)
		table.attach(self.ename, 1, 2, 0, 1)
		
		#if connection use geocoders, else use geonames sql database

		#display of location (non editable)
		self.entry2 = gtk.Label(' '+_('Latitude')+
			': %s\n '%openAstro.geolat+_('Longitude')+
			': %s\n '%openAstro.geolon+_('Location')+
			': %s' %openAstro.location)
		table.attach(self.entry2, 1, 2, 1, 2)
		#check for connection
		if self.iconn:
			hbox = gtk.HBox(False,5)
			table.attach(hbox,0,1,1,2)
			#entry for location (editable)
			label=gtk.Label(_("City")+": ")
			hbox.pack_start(label,False,False,0)
	
			self.geoLoc = gtk.Entry(50)
			self.geoLoc.set_width_chars(20)
			self.geoLoc.set_text(openAstro.location.partition(',')[0])
			hbox.pack_start(self.geoLoc,False,False,0)

			label=gtk.Label(" "+_("Country-code")+": ")
			hbox.pack_start(label,False,False,0)
			
			self.geoCC = gtk.Entry(2)
			self.geoCC.set_width_chars(2)
			self.geoCC.set_text(openAstro.countrycode)
			hbox.pack_start(self.geoCC,False,False,0)
		else:
			vbox=gtk.VBox(False,5)
			table.attach(vbox,0,1,1,2)
			hbox=gtk.HBox(False,5)
			#get nearest geoname
			self.GEON_nearest = db.gnearest(openAstro.geolat,openAstro.geolon)
			#continents
			self.contbox = gtk.ComboBox()
			self.contstore = gtk.ListStore(str,str)
			cell = gtk.CellRendererText()
			self.contbox.pack_start(cell)
			self.contbox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.contbox)
			self.contbox.set_wrap_width(1)

			sql = 'SELECT * FROM continent ORDER BY name ASC'
			db.gquery(sql)
			continentinfo=[]
			self.searchcontinent={}
			i = 0
			activecont = 3
			for row in db.gcursor:
				self.searchcontinent[row['code']]=i
				if row['code'] == self.GEON_nearest['continent']:
					activecont=i
					self.GEON_nearest['continent']=None
				self.contstore.append([row['name'],row['code']])
				i += 1
			db.gclose()
			self.contbox.set_model(self.contstore)
        
			#countries
			self.countrybox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.countrybox.pack_start(cell)
			self.countrybox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.countrybox)
			self.countrybox.set_wrap_width(1) 
			self.countrybox.connect('changed', self.eventDataChangedCountrybox)

			#provinces
			self.provbox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.provbox.pack_start(cell)
			self.provbox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.provbox)
			self.provbox.set_wrap_width(1) 
			self.provbox.connect('changed', self.eventDataChangedProvbox)

			#cities
			self.citybox = gtk.ComboBox()
			cell = gtk.CellRendererText()
			self.citybox.pack_start(cell)
			self.citybox.add_attribute(cell, 'text', 0)
			hbox.pack_start(self.citybox)
			self.citybox.set_wrap_width(2) 
			self.citybox.connect('changed', self.eventDataChangedCitybox)

			self.contbox.connect('changed', self.eventDataChangedContbox)
			self.contbox.set_active(activecont)
			
			#add search in database
			vbox.pack_start(hbox)
			hbox=gtk.HBox(False,5)			
			label=gtk.Label(_("Search City")+":")
			hbox.pack_start(label,False,False,0)
			self.citysearch = gtk.Entry()
			self.citysearch.set_max_length(34)
			self.citysearch.set_width_chars(24)
			hbox.pack_start(self.citysearch,False,False,0)
			self.citysearchbutton = gtk.Button(_('Search'))
			self.citysearchbutton.connect("clicked", self.citySearch)
			self.citysearch.connect("activate", self.citySearch)
			hbox.pack_start(self.citysearchbutton,False,False,0)
			label=gtk.Label("("+_("For example: London, GB")+")")
			hbox.pack_start(label,False,False,0)
			vbox.pack_start(hbox)

		#Year month day entry
		hbox = gtk.HBox(False,5)
		table.attach(hbox, 0, 1, 2, 3)
		
		label=gtk.Label(_("Year")+":")
		hbox.pack_start(label,False,False,0)

		self.dateY = gtk.Entry()
		self.dateY.set_max_length(4)
		self.dateY.set_width_chars(4)
		self.dateY.set_text(str(openAstro.year_loc))
		hbox.pack_start(self.dateY,False,False,0)

		label=gtk.Label(_("Month")+":")
		hbox.pack_start(label,False,False,0)

		self.dateM = gtk.Entry()
		self.dateM.set_max_length(2)
		self.dateM.set_width_chars(2)
		self.dateM.set_text('%(#)02d' % {'#':openAstro.month_loc})
		hbox.pack_start(self.dateM,False,False,0)

		label=gtk.Label("Day:")
		hbox.pack_start(label,False,False,0)

		self.dateD = gtk.Entry()
		self.dateD.set_max_length(2)
		self.dateD.set_width_chars(2)
		self.dateD.set_text('%(#)02d' % {'#':openAstro.day_loc})
		hbox.pack_start(self.dateD,False,False,0)

		#dat entry (non editable)
		labelDateStr = str(openAstro.year_loc)+'-%(#1)02d-%(#2)02d' % {'#1':openAstro.month_loc,'#2':openAstro.day_loc}
		self.labelDate = gtk.Label(labelDateStr)
		table.attach(self.labelDate, 1, 2, 2, 3)

		#time entry (editable) (Hour, Minutes, Seconds, Timezone)
		hbox = gtk.HBox(False,5)
		table.attach(hbox, 0, 1, 3, 4)

		label=gtk.Label(_("Hour")+":")
		hbox.pack_start(label,False,False,0)

		self.eH = gtk.Entry()
		self.eH.set_max_length(2)
		self.eH.set_width_chars(2)
		self.eH.set_text('%(#)02d' % {'#':openAstro.hour_loc})
		hbox.pack_start(self.eH,False,False,0)

		label=gtk.Label(_("Min")+":")
		hbox.pack_start(label,False,False,0)

		self.eM = gtk.Entry()
		self.eM.set_max_length(2)
		self.eM.set_width_chars(2)
		self.eM.set_text('%(#)02d' % {'#':openAstro.minute_loc})
		hbox.pack_start(self.eM,False,False,0)
		
		label=gtk.Label("Sec:")
		hbox.pack_start(label,False,False,0)
		
		self.eS = gtk.Entry()
		self.eS.set_max_length(2)
		self.eS.set_width_chars(2)
		self.eS.set_text('%(#)02d' % {'#':openAstro.second_loc})
		hbox.pack_start(self.eS,False,False,0)
		
		#time entry (non editable)
		labelTzStr = '%(#1)02d:%(#2)02d:%(#3)02d' % {'#1':openAstro.hour_loc,'#2':openAstro.minute_loc,'#3':openAstro.second_loc} + openAstro.decTzStr(openAstro.timezone)
		self.labelTz = gtk.Label(labelTzStr)
		table.attach(self.labelTz, 1, 2, 3, 4)

		#buttonbox
		buttonbox = gtk.HBox(False, 5)
		table.attach(buttonbox, 0, 2, 4, 5)
		
		#save to database button
		if edit:
			self.savebutton = gtk.Button(_('Save'),gtk.STOCK_SAVE)
			self.savebutton.connect("clicked", self.openDatabaseEditAsk)
			buttonbox.pack_start(self.savebutton,False,False,0)
		else:
			self.savebutton = gtk.Button(_('Add to Database'))
			self.savebutton.connect("clicked", self.eventDataSaveAsk)
			buttonbox.pack_start(self.savebutton,False,False,0)
				
		#Test button
		button = gtk.Button(_('Test'),gtk.STOCK_APPLY)
		button.connect("clicked", self.eventDataApply)
		buttonbox.pack_start(button,False,False,0)
  		#ok button
  		if edit == False:
			button = gtk.Button(stock=gtk.STOCK_OK)
			button.connect("clicked", self.eventDataSubmit)
			button.set_flags(gtk.CAN_DEFAULT)
			buttonbox.pack_start(button,False,False,0)
			button.grab_default()
            
		#cancel button
		button = gtk.Button(stock=gtk.STOCK_CANCEL)
		button.connect("clicked", lambda w: self.window2.destroy())
		buttonbox.pack_start(button,False,False,0)
		
		self.window2.show_all()
		return


	def citySearch(self, widget):
		
		#text entry
		city=self.citysearch.get_text()

		#look for country in search string
		isoalpha2=None
		if city.find(","):
			split = city.split(",")
			for x in range(len(split)):
				sql="SELECT * FROM countryinfo WHERE \
				(isoalpha2 LIKE ? OR name LIKE ?) LIMIT 1"
				y=split[x].strip()
				db.gquery(sql,(y,y))
				result=db.gcursor.fetchone()
				if result != None:
					isoalpha2=result["isoalpha2"]
					city=city.replace(split[x]+",","").replace(","+split[x],"").strip()
					#print "%s,%s"%(city,isoalpha2)
					break
			
		#normal search
		normal = city
		fuzzy = "%"+city+"%"
		if isoalpha2:
			extra = " AND country='%s'"%(isoalpha2)
		else:
			extra = ""
		
		sql = "SELECT * FROM geonames WHERE \
		(name LIKE ? OR asciiname LIKE ?)%s \
		LIMIT 1" %(extra)
		db.gquery(sql,(normal,normal))
		result=db.gcursor.fetchone()
		
		if result == None:
			sql = "SELECT * FROM geonames WHERE \
			(name LIKE ? OR asciiname LIKE ?)%s \
			LIMIT 1" %(extra)
			db.gquery(sql,(fuzzy,fuzzy))
			result=db.gcursor.fetchone()

		if result == None:
			sql = "SELECT * FROM geonames WHERE \
			(alternatenames LIKE ?)%s \
			LIMIT 1"%(extra)
			db.gquery(sql,(fuzzy,))
			result=db.gcursor.fetchone()
					
		if result != None:
			#set continent
			sql = "SELECT continent FROM countryinfo WHERE isoalpha2=? LIMIT 1"
			db.gquery(sql,(result["country"],))
			self.contbox.set_active(self.searchcontinent[db.gcursor.fetchone()[0]])
			#set country
			self.countrybox.set_active(self.searchcountry[result["country"]])
			#set admin1
			self.provbox.set_active(self.searchprov[result["admin1"]])
			#set city
			self.citybox.set_active(self.searchcity[result["geonameid"]])
			
		return

    
	def eventDataChangedContbox(self, combobox):
		model = combobox.get_model()
		index = combobox.get_active()

		store = gtk.ListStore(str,str)
		store.clear()
		sql = "SELECT * FROM countryinfo WHERE continent=? ORDER BY name ASC"
		db.gquery(sql,(model[index][1],))
		list = []
		i=0
		activecountry=0
		self.searchcountry={}
		for row in db.gcursor:
			self.searchcountry[row['isoalpha2']]=i
			if self.GEON_nearest['country'] == row['isoalpha2']:
				activecountry=i
				self.GEON_nearest['country']=None
			list.append((row['name'],row['isoalpha2']))
			i+=1
		db.gclose()
		for i in range(len(list)):
			store.append(list[i])
		self.countrybox.set_model(store)
		self.countrybox.set_active(activecountry) 
		return
      
	def eventDataChangedCountrybox(self, combobox):
		model = combobox.get_model()
		index = combobox.get_active()
		self.provlist = gtk.ListStore(str,str,str,str)
		self.provlist.clear()
		sql = "SELECT * FROM admin1codes WHERE country=? ORDER BY admin1 ASC"
		db.gquery(sql,(model[index][1],))
		list = []
		i=0
		activeprov=0
		self.searchprov={}
		for row in db.gcursor:
			self.searchprov[row["admin1"]] = i
			if self.GEON_nearest['admin1'] == row['admin1']:
				activeprov=i
				self.GEON_nearest['admin1'] = None
			list.append((row['province'],row['country'],row['admin1'],model[index][0]))
			i+=1
		db.gclose()
		for i in range(len(list)):
			self.provlist.append(list[i])
		self.provbox.set_model(self.provlist)
		self.provbox.set_active(activeprov) 
		return

	def eventDataChangedProvbox(self, combobox):
		model = combobox.get_model()
		index = combobox.get_active()

		self.citylist = gtk.ListStore(str,str,str,str,str,str,str,str)
		self.citylist.clear()
		sql = 'SELECT * FROM geonames WHERE country=? AND admin1=? ORDER BY name ASC'
		db.gquery(sql,(model[index][1],model[index][2]))
		list = []
		i=0
		activecity=0
		self.searchcity={}
		for row in db.gcursor:
			self.searchcity[row["geonameid"]]=i
			if self.GEON_nearest['geonameid'] == row['geonameid']:
				activecity=i
				self.GEON_nearest['geonameid'] = None
			list.append((row['name'],row['latitude'],row['longitude'],model[index][3],model[index][0],row['country'],row['geonameid'],row['timezone']))
			i+=1
		db.gclose()
		for i in range(len(list)):
			self.citylist.append(list[i])
		self.citybox.set_model(self.citylist)
		self.citybox.set_active(activecity) 
		return

	def eventDataChangedCitybox(self, combobox):
		model = combobox.get_model()
		index = combobox.get_active()
		#change label for eventdata
		self.GEON_lat = model[index][1]
		self.GEON_lon = model[index][2]
		self.GEON_loc = '%s, %s, %s' % (model[index][0],model[index][4],model[index][3])
		self.GEON_cc = model[index][5]
		self.GEON_id = model[index][6]
		self.GEON_tzstr = model[index][7]
		dprint( 'evenDataChangedCitybox: %s:%s:%s:%s:%s:%s' % (self.GEON_loc,self.GEON_lat,self.GEON_lon,self.GEON_cc,self.GEON_tzstr,self.GEON_id) )
		#settingslocationmode
		if self.settingsLocationMode:
			self.LLoc.set_text(_('Location')+': %s'%(self.GEON_loc))
			self.LLat.set_text(_('Latitude')+': %s'%(self.GEON_lat))
			self.LLon.set_text(_('Longitude')+': %s'%(self.GEON_lon))
		else:		
			self.entry2.set_text(' %s: %s\n %s: %s\n %s: %s' % (
				_('Latitude'),self.GEON_lat,_('Longitude'),self.GEON_lon,_('Location'),self.GEON_loc) )

	
	def eventDataSaveAsk(self, widget):
		#check for duplicate name	
		en = db.getDatabase()
		for i in range(len(en)):
			if en[i]["name"] == self.name.get_text():
				dialog=gtk.Dialog(_('Duplicate'),self.window2,0,(gtk.STOCK_OK, gtk.RESPONSE_DELETE_EVENT))
				dialog.set_icon_from_file(cfg.iconWindow)			
				dialog.connect("response", lambda w,e: dialog.destroy())				
				dialog.connect("close", lambda w,e: dialog.destroy())
				dialog.vbox.pack_start(gtk.Label(_('There is allready an entry for this name, please choose another')),True,True,0)
				dialog.show_all()				
				return
		#ask for confirmation
		dialog=gtk.Dialog(_('Question'),self.window2,gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		dialog.set_icon_from_file(cfg.iconWindow)
		dialog.connect("close", lambda w,e: dialog.destroy())
		dialog.connect("response",self.eventDataSave)
		dialog.vbox.pack_start(gtk.Label(_('Are you sure you want to save this entry to the database?')),True,True,0)
		dialog.show_all()	
		return	
	
	def eventDataSave(self, widget, response_id):
		if response_id == gtk.RESPONSE_ACCEPT:
			#update chart data
			self.updateChartData()
			#set query to save
			#add data from event_natal table
			sql='INSERT INTO event_natal \
				(id,name,year,month,day,hour,geolon,geolat,altitude,location,timezone,notes,image,countrycode,geonameid,timezonestr,extra)\
				 VALUES (null,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
			tuple=(openAstro.name,openAstro.year,openAstro.month,openAstro.day,openAstro.hour,
				openAstro.geolon,openAstro.geolat,openAstro.altitude,openAstro.location,
				openAstro.timezone,'','',openAstro.countrycode,openAstro.geonameid,openAstro.timezonestr,'')
			db.pquery([sql],[tuple])
			dprint('saved to database: '+openAstro.name)
			self.updateUI()
			widget.destroy()		
		else:
			widget.destroy()
			dprint('rejected save to database')
		return

	def eventDataSubmit(self, widget):
		#check if no changes were made
		if self.name.get_text() == openAstro.name and \
		self.dateY.get_text() == str(openAstro.year_loc) and \
		self.dateM.get_text() == '%(#)02d' % {'#':openAstro.month_loc} and \
		self.dateD.get_text() == '%(#)02d' % {'#':openAstro.day_loc} and \
		self.eH.get_text() == '%(#)02d' % {'#':openAstro.hour_loc} and \
		self.eM.get_text() == '%(#)02d' % {'#':openAstro.minute_loc} and \
		self.eS.get_text() == '%(#)02d' % {'#':openAstro.second_loc}:
			if self.iconn and \
			self.geoCC.get_text() == openAstro.countrycode and \
			self.geoLoc.get_text() == openAstro.location.partition(',')[0]:
				#go ahead ;)				
				self.window2.destroy()
				return
		
		#apply data
		self.eventDataApply( widget )
		
		if self.geoLocFound:
			self.window2.destroy()
			#update history
			db.addHistory()
			self.updateUI()
			return
		else:
			return

	def eventDataApply(self, widget):
		#update chart data
		openAstro.charttype=openAstro.label["radix"]
		openAstro.type="Radix"
		openAstro.transit=False
		self.updateChartData()
		
		#update chart
		self.updateChart()

	def quit_cb(self, b):
		dprint('Quitting program')
		gtk.main_quit()


#cairo svg class
class drawSVG(gtk.DrawingArea):
	def __init__(self):
		super(drawSVG, self).__init__()
		self.connect("expose_event", self.exposeEvent)

	def setSVG(self,svg):
		self.svg = rsvg.Handle(svg)
		self.emit("expose-event",gtk.gdk.Event(gtk.gdk.EXPOSE))
		width=self.svg.props.width*openAstro.zoom
		height=self.svg.props.height*openAstro.zoom
		self.set_size_request(int(width),int(height))
		dprint('drawSVG.setSVG file %s' % (svg))

	def exposeEvent(self,widget,event):
		try:
			context = self.window.cairo_create()
		except AttributeError:
			return True

		if self.svg != None:

			#set a clip region for the expose event
			context.rectangle(event.area.x, event.area.y,event.area.width, event.area.height)
			context.clip()
				
			self.svg.render_cairo(context)


#debug print function
def dprint(str):
	if "--debug" in sys.argv or DEBUG:
		print '%s' % str

#gtk main

def main():
    gtk.main()
    return 0

#start the whole bunch

if __name__ == "__main__":
	cfg = openAstroCfg()
	db = openAstroSqlite()
	openAstro = openAstroInstance()	
	mainWindow()
	main()

