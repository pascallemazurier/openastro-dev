#!/usr/bin/env python

from distutils.core import setup, Extension
import glob, os.path, sys

f=open('VERSION')
VERSION=f.read()
f.close()

if 'build' in sys.argv or 'install' in sys.argv:
	instdir = os.path.dirname(os.path.abspath(__file__))
	os.system('make clean')
	os.system('make libswe.a')
	os.chdir(instdir)

f=glob.glob('locale/*')
pre_data_files=[]
for a in range(len(f)):
	if f[a] == "locale/templates":
		continue
	pre_data_files.append( ('share/openastro.org/%s/LC_MESSAGES'%(f[a]),['%s/LC_MESSAGES/openastro.mo'%(f[a])]) )

pre_data_files += [
	('share/applications', ['openastro.org.desktop']),
	('share/openastro.org', ['openastro-svg.xml','openastro-svg-table.xml','openastro-ui.xml','geonames.sql','famous.sql']),
	('share/openastro.org/icons', ['icons/openastro.svg']),
	('share/openastro.org/icons/aspects', glob.glob('icons/aspects/*.svg')),
	]

setup(name='OpenAstro.org',
      version=VERSION,
      description='Open Source Astrology',
      author='Pelle van der Scheer',
      author_email='pellesimon@gmail.com',
      url='http://www.openastro.org',
      license='GPL',
      scripts=['openastro.py'],
      packages=['openastromod'],
      data_files=pre_data_files,
     )
