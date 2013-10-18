#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# bricks - configure semplice features
# Copyright (C) 2013  Eugenio "g7" Paolantonio
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This is the core library.
#

from libbricks.features import features

import apt

# Obtain cache content
cache = apt.Cache()

def __dependencies_loop(deplist, pkg, onelevel=False):
	""" Loops through pkg's dependencies.
	
	Returns a list with every package found. """
	
	if onelevel: onelevellist = []
	
	if not pkg.is_installed: return
	
	for depf in pkg.installed.dependencies:
		for dep in depf:
			if dep.name in cache and not cache[dep.name] in deplist:
				deplist.append(cache[dep.name])
			
				__dependencies_loop(deplist, cache[dep.name])
			
			if onelevel:
				if dep.name in cache:
					onelevellist.append(cache[dep.name])
	
	if onelevel: return onelevellist

def dependencies_loop_simplified(pkg, asString=False):
	""" A simpler and faster way to do an onelevel dependency list.
	
	If asString is True, the list will contain only the package names,
	not the apt.package objects (as it does by default) """
	
	lst = []
	
	if type(pkg) == str: pkg = cache[pkg]
	
	if pkg.installed:
		version = pkg.installed
	else:
		version = pkg.versions[0]
	
	for depf in version.dependencies:
		for dep in depf:
			if dep.name in cache:
				if not asString:
					lst.append(cache[dep.name])
				else:
					lst.append(dep.name)
	
	return lst

def remove(packages, auto=True, purge=()):
	""" Marks the packages and its dependencies for removal. """
	
	print packages
	
	for package in packages:
		
		print "processing", package
		package = cache[package]
		
		if not package.is_installed: continue
		
		# How logic works:
		# 1) We loop trough dependencies's dependencies and add them to
		# the list.
		# 2) We sequentially remove every package in list
		#    - via is_auto_installed we check if we can safely remove it
		
		deplist = []
		onelevel = __dependencies_loop(deplist, package, onelevel=True)
		#onelevel = dependencies_loop_simplified(package)
				
		# Mark for deletion the first package, to fire up auto_removable
		
		# Purge?
		if package.name in purge:
			package.mark_delete(purge=True)
		else:
			package.mark_delete(purge=False)
		
		# Also ensure we remove AT LEAST the first level of dependencies
		# (that is, the actual package's dependencies).
		if auto:
			markedauto = []
			for pkg in onelevel:
				if not pkg.marked_install and pkg.is_installed and not pkg.is_auto_installed:
					pkg.mark_auto()
					markedauto.append(pkg)
			
			for pkg in deplist:
				if not pkg.marked_install and pkg.is_installed and pkg.is_auto_removable:
					print("Marking %s for deletion..." % pkg)
					# Purge?
					if pkg.name in purge:
						pkg.mark_delete(purge=True)
					else:
						pkg.mark_delete(purge=False)
			
			# Restore auted items
			for pkg in markedauto:
				if not pkg.marked_delete: pkg.mark_auto(False)
		else:
			# We need to ensure that the onelevel packages are not marked
			# as automatically installed, otherwise the user may drop
			# them via autoremove or aptitude.
			for pkg in onelevel:
				if pkg.is_installed and pkg.is_auto_installed:
					pkg.mark_auto(auto=False)

def install(packages):
	""" Marks the packages for installation. """
	
	for package in packages:
		
		package = cache[package]
		package.mark_install()

def status(feature):
	""" Returns a tuple that contains:
	
	- A boolean value (True if feature is fully installed, False if not)
	- A list of packages installed.
	- A list of all packages of the feature.
	"""
	 
	status = None
	packages = []
	allpackages = []
	
	for variant in get_variants():
		if "package-%s" % variant in features[feature]:
			pkgname = features[feature]["package-%s" % variant]
			pkg = cache[pkgname]
			 
			if pkg.is_installed:
				status = True
				packages.append(pkgname)
			else:
				status = False
			
			allpackages.append(pkgname)
	
	if status == None and "package-base" in features[feature]:
		# Only package-base.
		pkgname = features[feature]["package-base"]
		pkg = cache[pkgname]
		
		if pkg.is_installed:
			status = True
			packages.append(pkgname)
		else:
			status = False
		
	if "package-base" in features[feature]:
		pkgname = features[feature]["package-base"]
		
		packages.append(pkgname)
		allpackages.append(pkgname)		
	
	return (status, packages, allpackages)

def get_variants():
	""" Returns the Semplice variants. Hardcoded to openbox now. """
	
	return ("openbox",)

def is_installed(pkg):
	""" Returns True if the specified package is installed, False if not. """
	
	return cache[pkg].is_installed
