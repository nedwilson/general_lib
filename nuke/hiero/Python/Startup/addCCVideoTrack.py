#!/usr/bin/python

import os
import hiero.core
import hiero.ui
import ConfigParser
from PySide2.QtWidgets import *
from PySide2.QtCore import *


class AddCCVideoTrack(QAction):

	g_showLUT = None
	g_showRoot = None

	def __init__(self):
		QAction.__init__(self, "Add CC Video Track", None)
		self.triggered.connect(self.addCCTrack)
		hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
		# retrieve global values from config file/system environment
		ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
		config = ConfigParser.ConfigParser()
		config.read(ih_show_cfg_path)
		self.g_showRoot = os.environ['IH_SHOW_ROOT']
		self.g_showLUT = os.path.join(self.g_showRoot, "SHARED", "lut", config.get(os.environ['IH_SHOW_CODE'], 'lut'))

	def addCCTrack(self):

		activeSeq = hiero.ui.activeSequence()
		trackItems = activeSeq.videoTracks()[-1].items()

        # todo: make sure that the CC track doesn't already exist. If it does, delete the effects in it and remake.
		ccTrack = hiero.core.VideoTrack("CC")
		activeSeq.addTrack(ccTrack)

		for ti in trackItems:
			csEffect = ccTrack.createEffect('OCIOColorSpace', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
			csEffect.node().knob('out_colorspace').setValue('AlexaV3LogC')

		for ti in trackItems:
			s_shot = ti.name()
			# todo: pull this out into a config file
			s_seq = ti.name()[0:5]
			s_cdlFile = os.path.join(self.g_showRoot, s_seq, s_shot, 'data', 'cdl', '%s.ccc'%s_shot)
			cdlEffect = ccTrack.createEffect('OCIOCDLTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
			cdlEffect.node().knob('read_from_file').setValue(True)
			cdlEffect.node().knob('file').setValue(s_cdlFile)

		for ti in trackItems:
			lutEffect = ccTrack.createEffect('OCIOFileTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
			lutEffect.node().knob('file').setValue(self.g_showLUT)

# 		for ti in trackItems:
# 			csrEffect = ccTrack.createEffect('OCIOColorSpace', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
# 			csrEffect.node().knob('in_colorspace').setValue('Rec709')

	def eventHandler(self, event):
		enabled = True
		title = "Add CC Video Track"
		self.setText(title)
		event.menu.addAction( self )

# The act of initialising the action adds it to the right-click menu...
AddCCVideoTrackInstance = AddCCVideoTrack()

# Add it to the Menu bar Edit menu to enable keyboard shortcuts
# timelineMenu = hiero.ui.findMenuAction("Timeline")
# timelineMenu.menu().addAction(AddCCVideoTrack)
