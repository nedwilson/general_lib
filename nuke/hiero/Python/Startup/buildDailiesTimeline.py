from PySide2.QtWidgets import *
from PySide2.QtCore import *
import hiero.core
import hiero.ui
import glob
import os
import sys
import time
from stat import S_ISREG, S_ISDIR, ST_MTIME, ST_MODE


class BuildDailiesTimeline(QAction):
	g_s_project_root = "/Volumes/monovfx/inhouse/zmonolith"
	g_s_show_lut = "/Volumes/monovfx/inhouse/zmonolith/SHARED/lut/AlexaV3_K1S1_LogC2Video_EE_davinci3d_Profile_To_Rec709_2-4_G1_Og1_P1_Lum.cube"

	def __init__(self):
		QAction.__init__(self, "Build Dailies Timeline", None)
		self.triggered.connect(self.build_dailies_timeline)
		hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)

	def likely_plate(self, m_s_basename):
		# path to the directory (relative or absolute)
		tmp_shot = m_s_basename.split('_')[0]
		tmp_seq = tmp_shot[0:3]
		dirpath = os.path.join(self.g_s_project_root, tmp_seq, tmp_shot, 'pix', 'plates')

		# get all entries in the directory w/ stats
		entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath) if not 'temp' in fn)
		l_entries = list(entries)
		entries = ((os.stat(path), path) for path in l_entries)
		l_entries = list(entries)
		# leave only directories, insert modification date
		# entries = ((stat[ST_MTIME], path)
		# NOTE: use `ST_MTIME` to sort by a modification date
		entries = []
		for stat, path in l_entries:
			if S_ISDIR(stat[ST_MODE]):
				entries.append((stat[ST_MTIME], path))

		sorted_entries = sorted(entries)
		return sorted_entries[-1][1]	
		
	def build_dailies_timeline(self):
		g_s_dailies_dir = QFileDialog.getExistingDirectory(None, 'Open Submission Directory', '/Volumes/monovfx/inhouse/from_inhouse', QFileDialog.ShowDirsOnly)

		print "INFO: Examining Dailies Submission folder at: %s"%g_s_dailies_dir

		s_dailies_date = os.path.split(g_s_dailies_dir)[-1]
		dailies_project = hiero.core.newProject()
		dailies_project.setProjectRoot(self.g_s_project_root)
		dailies_project.saveAs("%s/%s_review_v001.hrox"%(g_s_dailies_dir, s_dailies_date))

		tl_bin = dailies_project.clipsBin()

		quicktime_bin = hiero.core.Bin("Quicktimes")
		plates_bin = hiero.core.Bin("Plates")
		exr_bin = hiero.core.Bin("EXRs")

		review_seq = hiero.core.Sequence("review")
		qt_video_track = hiero.core.VideoTrack("quicktimes")
		plate_video_track = hiero.core.VideoTrack("plates")
		exr_video_track = hiero.core.VideoTrack("exrs")
		cc_video_track = hiero.core.VideoTrack("cc")
		review_seq.addTrack(qt_video_track)
		review_seq.addTrack(plate_video_track)
		review_seq.addTrack(exr_video_track)
		review_seq.addTrack(cc_video_track)
		review_seq_bi = hiero.core.BinItem(review_seq)

		tl_bin.addItem(quicktime_bin)
		tl_bin.addItem(plates_bin)
		tl_bin.addItem(exr_bin)
		tl_bin.addItem(review_seq_bi)

		vt_pos = 0
		b_is_temp = False
		for qt_file in sorted(glob.glob(os.path.join(g_s_dailies_dir, '_vfx', '*.mov'))):
			b_is_temp = False
			tmp_basename = os.path.basename(qt_file).replace('_vfx', '').split('.')[0]
			tmp_shot = os.path.basename(qt_file).split('_')[0]
			tmp_seq = tmp_shot[0:3]
	
			# Create Quicktime MediaSource
			tmp_qt_ms = hiero.core.MediaSource(qt_file)
			tmp_qt_clip = hiero.core.Clip(tmp_qt_ms, (tmp_qt_ms.startTime() + 1), (tmp_qt_ms.startTime() + tmp_qt_ms.duration() - 1))
			quicktime_bin.addItem(hiero.core.BinItem(tmp_qt_clip))
			# Create Quicktime TrackItem
			tmp_qt_track_item = qt_video_track.createTrackItem(tmp_shot)
			tmp_qt_track_item.setSource(tmp_qt_clip)
			tmp_qt_track_item.setTimelineIn(vt_pos)
			tmp_qt_track_item.setTimelineOut(vt_pos + tmp_qt_ms.duration() - 2)
			tmp_qt_track_item.reformatState().setType("disabled")
			qt_video_track.addItem(tmp_qt_track_item)
			
			if "temp" in qt_file:
				b_is_temp = True
				
			if not b_is_temp:
				# Create EXR Media Source
				tmp_exr_file = os.path.join(self.g_s_project_root, tmp_seq, tmp_shot, 'pix', 'comp', tmp_basename, "%s.%%04d.exr"%tmp_basename)
				tmp_exr_ms = hiero.core.MediaSource(tmp_exr_file)
				tmp_exr_clip = hiero.core.Clip(tmp_exr_ms, (tmp_exr_ms.startTime() + 1), (tmp_exr_ms.startTime() + tmp_exr_ms.duration() - 1))
				exr_bin.addItem(hiero.core.BinItem(tmp_exr_clip))
				# Create EXR TrackItem
				tmp_exr_track_item = exr_video_track.createTrackItem(tmp_shot)
				tmp_exr_track_item.setSource(tmp_exr_clip)
				tmp_exr_track_item.setTimelineIn(vt_pos)
				tmp_exr_track_item.setTimelineOut(vt_pos + tmp_exr_ms.duration() - 2)
				tmp_exr_track_item.reformatState().setType("disabled")
				exr_video_track.addItem(tmp_exr_track_item)

				# Create EXR Plate Media Source
				plate_tmp_dir = self.likely_plate(tmp_basename)
				tmp_exr_plate_file = os.path.join(plate_tmp_dir, "%s.%%04d.exr"%os.path.basename(plate_tmp_dir))
				tmp_exr_plate_ms = hiero.core.MediaSource(tmp_exr_plate_file)
				tmp_exr_plate_clip = hiero.core.Clip(tmp_exr_plate_ms, (tmp_exr_ms.startTime() + 1), (tmp_exr_ms.startTime() + tmp_exr_ms.duration() - 1))
				plates_bin.addItem(hiero.core.BinItem(tmp_exr_plate_clip))
				# Create EXR Plate TrackItem
				tmp_exr_plate_track_item = plate_video_track.createTrackItem(tmp_shot)
				tmp_exr_plate_track_item.setSource(tmp_exr_plate_clip)
				tmp_exr_plate_track_item.setTimelineIn(vt_pos)
				tmp_exr_plate_track_item.setTimelineOut(vt_pos + tmp_exr_ms.duration() - 2)
				tmp_exr_plate_track_item.reformatState().setType("disabled")
				plate_video_track.addItem(tmp_exr_plate_track_item)

				# Add Color Correction Layer
				cs_effect = hiero.core.EffectTrackItem('OCIOColorSpace', timelineIn=vt_pos, timelineOut=(vt_pos + tmp_exr_ms.duration() - 2))
				cs_effect.node().knob('out_colorspace').setValue('AlexaV3LogC')
				cc_video_track.addSubTrackItem(cs_effect, 0)
	
				tmp_cdl_file = os.path.join(self.g_s_project_root, tmp_seq, tmp_shot, 'data', 'cdl', '%s.cdl'%tmp_shot)
				cdl_effect = hiero.core.EffectTrackItem('OCIOCDLTransform', timelineIn=vt_pos, timelineOut=(vt_pos + tmp_exr_ms.duration() - 2))
				cdl_effect.node().knob('read_from_file').setValue(True)
				cdl_effect.node().knob('file').setValue(tmp_cdl_file)
				cc_video_track.addSubTrackItem(cdl_effect, 1)

				lut_effect = hiero.core.EffectTrackItem('OCIOFileTransform', timelineIn=vt_pos, timelineOut=(vt_pos + tmp_exr_ms.duration() - 2))
				lut_effect.node().knob('file').setValue(self.g_s_show_lut)
				cc_video_track.addSubTrackItem(lut_effect, 2)
	
				cs_effect_two = hiero.core.EffectTrackItem('OCIOColorSpace', timelineIn=vt_pos, timelineOut=(vt_pos + tmp_exr_ms.duration() - 2))
				cs_effect_two.node().knob('in_colorspace').setValue('rec709')
				cc_video_track.addSubTrackItem(cs_effect_two, 3)

			vt_pos += tmp_qt_ms.duration() - 1
	
		dailies_project.save()

	# This handles events from the Project Bin View
	def eventHandler(self,event):
		enabled = True
		title = "Build Dailies Timeline"
		self.setText(title)
		event.menu.addAction( self )

# Instantiate the Menu to get it to register itself.
BuildDailiesTimelineInstance = BuildDailiesTimeline()

