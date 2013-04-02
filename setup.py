#!/usr/bin/env python
# bricks setup (using distutils)
# Copyright (C) 2013 Eugenio "g7" Paolantonio. All rights reserved.
# Work released under the GNU GPL license, version 3.

from distutils.core import setup

setup(name='bricks',
	version='1.0.2',
	description='Manage semplice features',
	author='Eugenio Paolantonio',
	author_email='me@medesimo.eu',
	url='http://github.com/semplice/bricks',
	# package_dir={'bin':''},
	scripts=['bricks.py'],
	packages=[
		"libbricks",
      ],
	data_files=[("/usr/share/bricks", ["bricks.glade"]),("/usr/share/applications", ["bricks.desktop"]),("/usr/share/polkit-1/actions/", ["org.semplice-linux.pkexec.bricks.policy"])],
	requires=['gi.repository.Gtk', 'gi.repository.GObject', 't9n', 'threading', 'gettext', 'time', 'locale', 'apt', 'os', 'sys'],
)
