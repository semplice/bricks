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
# This is the main executable.
#

from gi.repository import Gtk, GObject

import apt.progress.base

import t9n.library

import os, sys, threading, traceback

import time

import libbricks.engine as engine

from libbricks.features import features, features_order

_ = t9n.library.translation_init("bricks")

#GLADEFILE = "./cymbaline.glade"
GLADEFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bricks.glade")

os.environ["DEBIAN_FRONTEND"] = "gnome"
os.environ["APT_LISTCHANGES_FRONTEND"] = "gtk"

class AcquireProgress(apt.progress.base.AcquireProgress):
	""" Handles the Acquire step. """
	
	def __init__(self, parent):
		
		self.parent = parent
		
	def fetch(self, item):
		""" Changes progress_text with the current package. """
		
		apt.progress.base.AcquireProgress.fetch(self, item)
		
		self.parent.progress_set_text("Fetching %s..." % item.shortdesc)
	
	def stop(self):
		""" Finish the progress. """
		
		apt.progress.base.AcquireProgress.stop(self)
		
		self.parent.progress_finish_percentage()
	
	def pulse(self, item):
		
		apt.progress.base.AcquireProgress.pulse(self, item)
		
		self.parent.progress_set_quota(self.total_bytes)
		self.parent.progress_set_percentage(self.current_bytes)
		
		return True

class InstallProgress(apt.progress.base.InstallProgress):
	""" Handles the Install step. """
	
	def __init__(self, parent):
		
		apt.progress.base.InstallProgress.__init__(self)
		
		self.parent = parent
	
	def finish_update(self):
		""" Finish the progress. """
				
		apt.progress.base.InstallProgress.finish_update(self)
		
		self.parent.progress_finish_percentage()
	
	def status_change(self, pkg, percent, status):
		""" Update percentage. """
				
		self.parent.progress_set_quota(100) # Does not fire if on start_update :/
		self.parent.progress_set_text(status + "...")
		
		apt.progress.base.InstallProgress.status_change(self, pkg, percent, status)
		
		self.parent.progress_set_percentage(percent)
		
		return True

class Apply(threading.Thread):
	def __init__(self, parent):
		
		self.parent = parent
		
		threading.Thread.__init__(self)
	
	def run(self):
		""" Apply the changes! """
		
		atleastone = False # hack to not commit if not needed
		
		try:
			# Get the status of each switch, then change cache accordingly
			for feature, objs in self.parent._objects.items():
				
				status, packages, allpackages = engine.status(feature)
				
				change = objs["switch"].get_active()
				if change == status:
					# We shouldn't touch this feature.
					print "Skipping %s" % feature
					continue
				else:
					atleastone = True
				
				if change:
					# Should mark for installation!
					engine.install(allpackages)
				else:
					# Should mark for removal!
					engine.remove(packages)
			
			#self.parent.progress_set_quota(100)
			#for lol in range(100):
			#	self.parent.progress_set_text(str(lol))
			#	self.parent.progress_set_percentage(lol)
			#	#self.parent.update_progress(str(lol), lol)
			#	time.sleep(0.3)
			
			# Commit
			if atleastone:
				engine.cache.commit(AcquireProgress(self.parent), InstallProgress(self.parent))
		except:
			excp = sys.exc_info()
			error = "".join(traceback.format_exception(excp[0],excp[1],excp[2]))
			print(error)
			GObject.idle_add(
				self.parent.error_window.format_secondary_markup,
				_("Press Close to exit from the application.") + "\n\n<i>" + error + "</i>")
			GObject.idle_add(self.parent.error_window.show)
		else:
			self.parent.really_quit()

class GUI:
	def progress_set_text(self, text):
		""" Sets the text of the progress label """
		
		GObject.idle_add(self.progress_text.set_markup, "<i>%s</i>" % text)
		
	def progress_set_quota(self, quota=100):
		""" Sets the final quota for this job. """
		
		self.quota = float(quota)
	
	def progress_get_quota(self):
		""" Returns the current progress quota. """
		
		return self.quota
	
	def progress_set_percentage(self, final):
		""" Update the progress percentage with final. """
		
		try:
			final = self.quota / final # Get the exact percentage from quota
			final = self.possible / final # Get the final exact percentage
						
			if final < self.possible:
				# We can safely update the progressbar.
				GObject.idle_add(self.progress_bar.set_fraction, self.current + final)
			else:
				# Assume we reached the maximum.
				GObject.idle_add(self.progress_bar.set_fraction, self.current + self.possible)
		except:
			pass
	
	def progress_finish_percentage(self):
		""" Resets the progress bar. """
			
		self.current = 0.0
		GObject.idle_add(self.progress_bar.set_fraction, 0.0)
	
	def really_quit(self, caller=None, witherror=False):
		
		Gtk.main_quit()
		if witherror: sys.exit(1)
	
	def quit(self, caller=None):
		
		# Set window parts insensitive
		GObject.idle_add(self.selection_box.set_sensitive, False)
		GObject.idle_add(self.close.set_sensitive, False)
		
		# Show progress
		GObject.idle_add(self.progress_box.show)
		
		applyclass = Apply(self)
		applyclass.start()
	
	def build_feature_objects(self):
		""" Builds GTK+ elements to list the features onto the GUI. """
		
		for feature in features_order:
			dic = features[feature]
			self._objects[feature] = {}
			
			# Generate high level HBox
			self._objects[feature]["container"] = Gtk.HBox()
			
			# Generate icon & text HBox
			self._objects[feature]["icontextcontainer"] = Gtk.HBox()
			self._objects[feature]["icontextcontainer"].set_spacing(5)
			
			# Generate text VBox
			self._objects[feature]["textcontainer"] = Gtk.VBox()
			self._objects[feature]["textcontainer"].set_spacing(3)
			
			# Generate switch
			self._objects[feature]["switch"] = Gtk.Switch()
			self._objects[feature]["switch"].set_halign(Gtk.Align.END)
			self._objects[feature]["switch"].set_valign(Gtk.Align.CENTER)
			# Preset the switch
			if engine.status(feature)[0]:
				self._objects[feature]["switch"].set_active(True)
			else:
				self._objects[feature]["switch"].set_active(False)

			# Generate icon
			self._objects[feature]["icon"] = Gtk.Image()
			self._objects[feature]["icon"].set_from_icon_name(
				dic["icon"],
				Gtk.IconSize.DIALOG)
			
			# Generate title
			self._objects[feature]["title"] = Gtk.Label()
			self._objects[feature]["title"].set_alignment(0.0,0.0)
			self._objects[feature]["title"].set_markup(
				"<b>%s</b>" % dic["title"])
			
			# Generate subtext
			if "subtext" in dic:
				self._objects[feature]["subtext"] = Gtk.Label()
				self._objects[feature]["subtext"].set_alignment(0.0,0.0)
				self._objects[feature]["subtext"].set_markup(
					dic["subtext"])
				self._objects[feature]["subtext"].set_line_wrap(True)
			
			# Pack title and subtext
			self._objects[feature]["textcontainer"].pack_start(
				self._objects[feature]["title"],
				False,
				False,
				0)
			if "subtext" in dic:
				self._objects[feature]["textcontainer"].pack_start(
					self._objects[feature]["subtext"],
					False,
					False,
					0)
			
			# Pack icon and textcontainer
			self._objects[feature]["icontextcontainer"].pack_start(
				self._objects[feature]["icon"],
				False,
				False,
				0)
			self._objects[feature]["icontextcontainer"].pack_start(
				self._objects[feature]["textcontainer"],
				True,
				True,
				0)
			
			# Pack icontextcontainer and switch
			self._objects[feature]["container"].pack_start(
				self._objects[feature]["icontextcontainer"],
				True,
				True,
				0)
			self._objects[feature]["container"].pack_start(
				self._objects[feature]["switch"],
				False,
				False,
				0)
			
			
			# Pack container into the main container
			self.container.pack_start(
				self._objects[feature]["container"],
				False,
				False,
				0)
			
	
	def __init__(self):
		""" Initialize the GUI. """
		
		self.quota = None
		self.current = 0.0
		self.possible = 1 # Acquire and Install
		
		self._objects = {}
		
		self.builder = Gtk.Builder()
		self.builder.add_from_file(GLADEFILE)
		
		
		self.window = self.builder.get_object("window")
		self.window.connect("destroy", lambda x: Gtk.main_quit())

		self.close = self.builder.get_object("close")
		self.close.connect("clicked", self.quit)
		
		self.selection_box = self.builder.get_object("main")
		
		self.progress_box = self.builder.get_object("progress_box")
		self.progress_text = self.builder.get_object("progress_text")
		self.progress_bar = self.builder.get_object("progress_bar")
		
		
		self.error_window = self.builder.get_object("error_window")
		
		self.error_close = self.builder.get_object("error_close")
		self.error_close.connect("clicked", self.really_quit, True)
		
		
		self.container = self.builder.get_object("features_container")
		
		self.build_feature_objects()
		
	
		self.window.show_all()
		self.progress_box.hide()


if __name__ == "__main__":
	g = GUI()
	GObject.threads_init()
	Gtk.main()
	#GObject.threads_leave()
