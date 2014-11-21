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
# This is the list of features.
#

import t9n.library

_ = t9n.library.translation_init("bricks")

features = {
	"bluetooth": {
		"icon":"bluetooth",
		"title":_("Bluetooth support"),
		"subtext":_("Without bluetooth support you can't use bluetooth devices."),
		"package-base":"meta-base-feature-bluetooth",
		"package-openbox":"meta-openbox-feature-bluetooth",
		"purge":("bluez",),
		"enable_selection":("package-base","package-openbox")
	},
	"printing": {
		"icon":"printer",
		"title":_("Printing support"),
		"subtext":_("This includes printer drivers and manage tools."),
		"package-base":"meta-base-feature-printing",
		"package-openbox":"meta-openbox-feature-printing",
		"purge":("cups-daemon",),
		"enable_selection":("package-base","package-openbox")
	},
	"office": {
		"icon":"applications-office",
		"title":_("Office applications"),
		"subtext":_("Word processors and spreadsheets."),
		"package-openbox":"meta-openbox-feature-office",
		"enable_selection":("package-openbox",)
	},
	"composite": {
		"icon":"preferences-system-windows",
		"title":_("Visual effects"),
		"subtext":_("Visual effects such as transparencies, shadows, etc."),
		"package-openbox":"meta-openbox-feature-composite",
		"enable_selection":("package-openbox",)
	},
	"pulseaudio": {
		"icon":"preferences-system-sound",
		"title":_("Advanced audio support"),
		"subtext":_("Advanced audio support (PulseAudio)."),
		"package-base":"meta-base-feature-pulseaudio",
		"package-openbox":"meta-openbox-feature-pulseaudio",
		"enable_selection":("package-base","package-openbox")
	},
	"oneslip": {
		"icon":"applications-internet",
		"title":_("Web applications support"),
		"subtext":_("Support for web applications such as YouTube, Twitter and Facebook."),
		"package-openbox":"meta-openbox-feature-oneslip",
		"enable_selection":("package-openbox",)
	},
	"nonfree": {
		"icon":"system-software-install",
		"title":_("Proprietary packages"),
		"subtext":_("Proprietary packages such as firmwares, the Adobe(R) Flash Player plugin and more."),
		"package-base":"meta-nonfree",
		"enable_selection":("package-base",)
	}
}

features_order = ("bluetooth","printing","office","composite","pulseaudio","nonfree")
