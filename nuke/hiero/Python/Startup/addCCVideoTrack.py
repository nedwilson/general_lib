#!/usr/bin/python

import os
import hiero.core
import hiero.ui
import ConfigParser
import re
from PySide2.QtWidgets import *
from PySide2.QtCore import *


class AddCCVideoTrack(QAction):

	g_showLUT = None
	g_showRoot = None
	g_shotRegExp = None
	g_initFail = False
	g_cdlPathFormat = None
	g_plateColorspace = None
	
	def __init__(self):
		QAction.__init__(self, "Add CC Video Track", None)
		self.triggered.connect(self.addCCTrack)
		hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)
		# retrieve global values from config file/system environment
		try:
			ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
			config = ConfigParser.ConfigParser()
			config.read(ih_show_cfg_path)
			self.g_showRoot = os.environ['IH_SHOW_ROOT']
			self.g_showLUT = os.environ['IH_SHOW_CFG_LUT']
			self.g_shotRegExp = re.compile(config.get(os.environ['IH_SHOW_CODE'], 'shot_regexp'))
			self.g_cdlPathFormat = config.get(os.environ['IH_SHOW_CODE'], 'shot_dir_format') + '{pathsep}' + config.get(os.environ['IH_SHOW_CODE'], 'cdl_dir_format') + '{pathsep}{shot}.' + config.get(os.environ['IH_SHOW_CODE'], 'cdl_file_ext')
			self.g_plateColorspace = config.get(os.environ['IH_SHOW_CODE'], 'plate_colorspace')
		except:
			g_initFail = True
			
	def addCCTrack(self):

		if not self.g_initFail:
			activeSeq = hiero.ui.activeSequence()
			trackItems = hiero.ui.getTimelineEditor(hiero.ui.activeSequence()).selection()

			# go from linear to AlexaLog if necessary
			if self.g_plateColorspace == 'linear':
				for ti in trackItems:
					csEffect = ti.parent().createEffect('OCIOColorSpace', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
					csEffect.node().knob('out_colorspace').setValue('AlexaV3LogC')

			for ti in trackItems:
				matchobject = self.g_shotRegExp.search(ti.name())
				if matchobject:
					s_shot = matchobject.group('shot')
					s_seq = matchobject.group('sequence')
					
					d_cdl_path = {}
					d_cdl_path['pathsep'] = os.path.sep
					d_cdl_path['show_root'] = os.environ['IH_SHOW_ROOT']
					d_cdl_path['sequence'] = s_seq
					d_cdl_path['shot'] = s_shot
					s_cdlFile = self.g_cdlPathFormat.format(**d_cdl_path)
					print "Attempting to add OCIOCDLTransform with path %s"%s_cdlFile
					if not os.path.exists(s_cdlFile):
						print "CDL file does not exist at path %s."%s_cdlFile
					else:
						# cdlEffect = ti.parent().createEffect('OCIOCDLTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
						# cdlEffect.node().knob('read_from_file').setValue(True)
						cdlEffect = ti.parent().createEffect('OCIOFileTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
						cdlEffect.node().knob('file').setValue(s_cdlFile)
						cdlEffect.node().knob('cccid').setValue("0")
						
			for ti in trackItems:
				lutEffect = ti.parent().createEffect('OCIOFileTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
				lutEffect.node().knob('file').setValue(self.g_showLUT)
		else:
			print "ERROR: initialization failed. Have the In-House environment variables been set up? Does the show config file exist?"


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
