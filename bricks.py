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

from gi.repository import Gtk, Gdk, GObject

import apt.progress.base

import locale, t9n.library

import os, sys, threading, traceback

import time

import libbricks.engine as engine

from libbricks.features import features, features_order

locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain("bricks", "/usr/share/locale")

_ = t9n.library.translation_init("bricks")

#GLADEFILE = "./cymbaline.glade"
GLADEFILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "bricks.glade")

os.environ["DEBIAN_FRONTEND"] = "gnome"
os.environ["APT_LISTCHANGES_FRONTEND"] = "gtk"

TYPE_DESCRIPTION = {
	"package-base":_("Core packages"),
	"package-openbox":_("Graphical support tools")
}

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
				
				# Get things to purge, if any
				to_purge = ()
				if "purge" in features[feature]:
					to_purge = features[feature]["purge"]
				
				change = objs["switch"].get_active()
				if change and change == status:
					# We shouldn't touch this feature.
					continue
				elif not change:
					# We need to check every checkbox to see if we need
					# to change something
					toinstall = []
					toremove = []
					allfalse = True # should check if there is at least one True item
					for dep, checkbox in self.parent.checkboxes[feature].items():
						value = checkbox.get_active()
						if value and not engine.is_installed(dep):
							# Package needs to be installed.
							toinstall.append(dep)
							allfalse = False
						elif value:
							allfalse = False
						elif not value and engine.is_installed(dep):
							# Package is installed and needs removal
							toremove.append(dep)
					
					if allfalse:
						# Every checkbox is false, we can mark for removal
						# the entire "packages"
						atleastone = True
						engine.remove(packages, purge=to_purge)
					else:
						# the user customized the feature.
						# We need to be sure that the meta package is
						# being processed as well.
						
						# First, we need to loop through the customizable
						# metapackages
						for meta in features[feature]["enable_selection"]:
							meta = features[feature][meta]
							
							# Now that we got the package name, we need to
							# get its dependencies...
							deps = engine.dependencies_loop_simplified(meta, asString=True)
							
							# ...and see if one of ours is there
							for pkg in toremove:
								if pkg in deps:
									# Yeah! Just add meta to toremove
									toremove.append(meta)
									break

					print "Packages to install:", toinstall
					print "Packages to remove:", toremove
					if toinstall:
						atleastone = True
						engine.install(toinstall)
					if toremove:
						atleastone = True
						engine.remove(toremove, auto=False, purge=to_purge)
				else:
					atleastone = True
					
					# Should mark for installation!
					engine.install(allpackages)
			
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
#				_("Press Close to exit from the application.") + "\n\n<i>" + error + "</i>")
				"<i>%s</i>\n\n" % excp[1] + _("Press Close to exit from the application."))
			GObject.idle_add(self.parent.error_window.show)
		else:
			self.parent.really_quit()

class GUI_BUILD(threading.Thread):
	""" Somewhat ugly workaround to make GTK+ building the feature widgets
	in the background. """
	
	def __init__(self, parent):
		""" Initialize the class """
		
		threading.Thread.__init__(self)
		
		self.parent = parent
	
	def run(self):
		""" Actually do things! """
		
		self.parent.build_feature_objects()
		self.parent.on_advanced_enabled_clicked(self.parent.advanced_enabled)

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
		GObject.idle_add(self.advanced_enabled.set_sensitive, False)
		
		# Show progress
		GObject.idle_add(self.progress_box.show)
		
		applyclass = Apply(self)
		applyclass.start()
	
	def on_advanced_checkutton_toggled(self, caller, feature):
		""" Called when one of the many checkbuttons of the 'advanced view'
		has been toggled. """
		
		# Avoid looping if switchstate is already True (see later)
		switchstate = self._objects[feature]["switch"].get_active()
		
		if not caller.get_active():
			# Value is False, we can safely say that the feature will not be
			# installed in full (we need to get the switch to OFF)
			GObject.idle_add(self._objects[feature]["switch"].set_active, False)
		elif not switchstate:
			# We need to check every related checkbutton in order to assume
			# if the new feature will be fully installed.
			alltrue = True
			for dependency, checkbutton in self.checkboxes[feature].items():
				if not checkbutton.get_active():
					alltrue = False
			
			if alltrue:
				GObject.idle_add(self._objects[feature]["switch"].set_active, True)
	
	def on_switch_pressed(self, caller, other, feature):
		""" Called when one of the switches has been pressed. """

		status = caller.get_active()

		if not status:
			for dependency, checkbutton in self.checkboxes[feature].items():
				if not checkbutton.get_active():
					# We hoped to use only one loop, but it doesn't seem
					# possible unfortunately
					return
		
		for dependency, checkbutton in self.checkboxes[feature].items():
			GObject.idle_add(checkbutton.set_active, status)
			
	def generate_advanced(self, vbox, feature):
		""" Generates and adds proper checkbox for the advanced expander. """
		
		self.checkboxes[feature] = {}
		
		dic = features[feature]
		
		for typ in dic["enable_selection"]:
			
			# Generate a frame that houses the type
			frame = Gtk.Frame()
			frame.set_shadow_type(Gtk.ShadowType.NONE)
			label = Gtk.Label()
			label.set_markup("<b>%s</b>" % TYPE_DESCRIPTION[typ])
			frame.set_label_widget(label)
			typ_vbox = Gtk.VBox()
			alignment = Gtk.Alignment()
			alignment.set_padding(2,2,12,0)
			alignment.add(typ_vbox)
			frame.add(alignment)
			
			# retrieve dependencies
			dps = engine.dependencies_loop_simplified(dic[typ])
			
			for dep in dps:
				if dep.name.startswith("meta-") or dep.name in self.checkboxes[feature]:
					continue
				if dep.installed:
					version = dep.installed
				else:
					version = dep.versions[0]
				self.checkboxes[feature][dep.name] = Gtk.CheckButton(dep.name + " - " + version.summary)
				self.checkboxes[feature][dep.name].get_child().set_line_wrap(True)
				if dep.installed:
					self.checkboxes[feature][dep.name].set_active(True)
				self.checkboxes[feature][dep.name].connect("toggled",self.on_advanced_checkutton_toggled, feature)
				typ_vbox.pack_start(
					self.checkboxes[feature][dep.name],
					False,
					False,
					0)
			
			vbox.pack_start(
				frame,
				False,
				False,
				0)
	
	def build_feature_objects(self):
		""" Builds GTK+ elements to list the features onto the GUI. """
		
		for feature in features_order:
			dic = features[feature]
			self._objects[feature] = {}
			
			# Generate high level VBox
			self._objects[feature]["main_container"] = Gtk.VBox()
			
			# Generate high level HBox
			self._objects[feature]["container"] = Gtk.HBox()
			
			# Generate icon & text HBox
			self._objects[feature]["icontextcontainer"] = Gtk.HBox()
			self._objects[feature]["icontextcontainer"].set_spacing(5)
			
			# Generate text VBox (advanced selection also hooked here)
			self._objects[feature]["textcontainer"] = Gtk.VBox()
			self._objects[feature]["textcontainer"].set_spacing(3)
			
			# Generate switch
			self._objects[feature]["switch"] = Gtk.Switch()
			self._objects[feature]["switch"].set_halign(Gtk.Align.END)
			self._objects[feature]["switch"].set_valign(Gtk.Align.CENTER)
			# Preset the switch
			print "FEATURE %s STATUS: %s" % (feature, engine.status(feature)[0])
			if engine.status(feature)[0]:
				self._objects[feature]["switch"].set_active(True)
			else:
				self._objects[feature]["switch"].set_active(False)
			self._objects[feature]["switch"].connect(
				"notify::active",
				self.on_switch_pressed,
				feature)

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

			# Add it
			self._objects[feature]["textcontainer"].pack_start(
				self._objects[feature]["title"],
				False,
				False,
				0)
			
			# Generate subtext
			if "subtext" in dic:
				self._objects[feature]["subtext"] = Gtk.Label()
				self._objects[feature]["subtext"].set_alignment(0.0,0.0)
				self._objects[feature]["subtext"].set_markup(
					dic["subtext"])
				self._objects[feature]["subtext"].set_line_wrap(True)

				# Add it
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
			
			# Pack normal container into the main VBox...
			self._objects[feature]["main_container"].pack_start(
				self._objects[feature]["container"],
				False,
				False,
				0)

			# Generate Expander to attach, if we should
			if "enable_selection" in dic:
				self._objects[feature]["expander_vbox"] = Gtk.VBox()
				self._objects[feature]["expander_align"] = Gtk.Alignment()
				self._objects[feature]["expander_align"].set_padding(
					5,5,12,0)
				# Generate a list of checkboxes to add to the vbox..
				self.generate_advanced(
					self._objects[feature]["expander_vbox"],
					feature)
				
				self._objects[feature]["expander_align"].add(
					self._objects[feature]["expander_vbox"])


				# Add it
				self._objects[feature]["main_container"].pack_start(
					self._objects[feature]["expander_align"],
					False,
					False,
					0)
			
			# Pack main_container into the main container
			GObject.idle_add(self.container.pack_start,
				self._objects[feature]["main_container"],
				False,
				False,
				0)
		
		# Show the box
		GObject.idle_add(self.waiting.hide)
		GObject.idle_add(self.selection_box.show_all)

		GObject.idle_add(self.close.set_sensitive, True)
		GObject.idle_add(self.advanced_enabled.set_sensitive, True)
	
	def on_advanced_enabled_clicked(self, caller):
		""" Called when the "Enable advanced mode" checkbutton has been
			clicked. """
		
		value = caller.get_active()
		
		for feature in features_order:
			if "expander_align" in self._objects[feature]:
				if value:
					GObject.idle_add(self._objects[feature]["expander_align"].show)
				else:
					GObject.idle_add(self._objects[feature]["expander_align"].hide)
	
	def enable_feature(self, obj, feature):
		""" Enables the feature 'feature' """
		
		GObject.idle_add(self._objects[feature]["switch"].set_active, True)
		GObject.idle_add(self.error_box.modify_bg, Gtk.StateType.NORMAL, Gdk.color_parse("#729fcf"))
		GObject.idle_add(self.error_image.set_from_icon_name, "gtk-dialog-info", Gtk.IconSize(6))
		GObject.idle_add(self.error_label.set_markup, _("Press the <i>Close</i> button to apply the changes."))
		GObject.idle_add(self.error_enable.hide)
	
	def __init__(self, ERROR_APP, ERROR_FEATURE):
		""" Initialize the GUI. """
		
		self.quota = None
		self.current = 0.0
		self.possible = 1 # Acquire and Install
		
		self._objects = {}
		self.checkboxes = {}
		
		self.builder = Gtk.Builder()
		self.builder.set_translation_domain("bricks")
		self.builder.add_from_file(GLADEFILE)
		
		self.window = self.builder.get_object("window")
		self.window.connect("destroy", lambda x: Gtk.main_quit())

		self.close = self.builder.get_object("close")
		self.close.connect("clicked", self.quit)
		
		self.error_box = self.builder.get_object("error_box")
		self.error_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#F07568"))
		self.error_image = self.builder.get_object("error_image")
		self.error_label = self.builder.get_object("error_label")
		self.error_enable = self.builder.get_object("error_enable")
		
		self.advanced_enabled = self.builder.get_object("advanced_enabled")
		self.advanced_enabled.connect("toggled", self.on_advanced_enabled_clicked)
		
		self.waiting = self.builder.get_object("waiting")
		self.selection_box = self.builder.get_object("main")
		
		self.progress_box = self.builder.get_object("progress_box")
		self.progress_text = self.builder.get_object("progress_text")
		self.progress_bar = self.builder.get_object("progress_bar")
		
		
		self.error_window = self.builder.get_object("error_window")
		
		self.error_close = self.builder.get_object("error_close")
		self.error_close.connect("clicked", self.really_quit, True)
		
		
		self.container = self.builder.get_object("features_container")
		
		self.window.show_all()
		self.progress_box.hide()
		self.selection_box.hide()
		
		self.close.set_sensitive(False)
		self.advanced_enabled.set_sensitive(False)

		if not ERROR_APP:
			self.error_box.hide()
		else:
			self.error_label.set_markup(
				_("<b>%s</b> requires \"<i>%s</i>\", which is not currently enabled.") %
					(ERROR_APP, features[ERROR_FEATURE]["title"])
			)
		
			# Connect Enable button
			self.error_enable.connect("clicked", self.enable_feature, ERROR_FEATURE)

		gb = GUI_BUILD(self)
		GObject.idle_add(gb.start)

if __name__ == "__main__":
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	# Parse arguments
	ERROR_APP = None
	ERROR_FEATURE = None
	if len(sys.argv) > 1:
		if sys.argv[1] in ("-h","--help"):
			print(_("USAGE: bricks <ERROR_APP> <ERROR_FEATURE>"))
			print(_("This application doesn't require any argument."))
			print(_("ERROR_APP and ERROR_FEATURE are internally used."))
			sys.exit(0)
		else:
			ERROR_APP = sys.argv[1]
			if len(sys.argv) == 2:
				print(_("ERROR: ERROR_APP requires also an ERROR_FEATURE."))
				sys.exit(1)
			else:
				ERROR_FEATURE = sys.argv[2]
	
	g = GUI(ERROR_APP, ERROR_FEATURE)
	GObject.threads_init()
	Gtk.main()
	#GObject.threads_leave()
