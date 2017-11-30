import re
import os
from stat import S_ISREG, S_ISDIR, ST_MTIME, ST_MODE
import hiero.core
import hiero.ui
from PySide2.QtWidgets import *
from PySide2.QtCore import *

class BuildShotLayers(QAction):

    g_shot_re = re.compile(r'([a-zA-Z]{3}[0-9]{4})')
    g_show_path = r'/Volumes/monovfx/inhouse/zmonolith'
    g_s_show_lut = r'/Volumes/monovfx/inhouse/zmonolith/SHARED/lut/AlexaV3_K1S1_LogC2Video_EE_davinci3d_Profile_To_Rec709_2-4_G1_Og1_P1_Lum.cube'

    def get_bin(self, o_project, s_bin):
        tl_bin = o_project.clipsBin()
        all_bins = tl_bin.bins()
        o_bin = None
        if not s_bin in [x.name() for x in all_bins]:
            o_bin = hiero.core.Bin(s_bin)
            tl_bin.addItem(o_bin)
        else:
            o_bin = [x for x in all_bins if x.name() == s_bin][-1]
        return o_bin

    def get_track(self, o_sequence, s_track):
        all_tracks = o_sequence.videoTracks()
        o_track = None
        if not s_track in [x.name() for x in all_tracks]:
            o_track = hiero.core.VideoTrack(s_track)
            o_sequence.addTrack(o_track)
        else:
            o_track = [x for x in all_tracks if x.name() == s_track][-1]
        return o_track

    def latest_element(self, m_shot, m_element_type):
        # path to the directory (relative or absolute)
        tmp_seq = m_shot[0:3]
        dirpath = None
        if m_element_type == "plate":
            dirpath = os.path.join(self.g_show_path, tmp_seq, m_shot, 'pix', 'plates') 
        elif m_element_type == "comp":
            dirpath = os.path.join(self.g_show_path, tmp_seq, m_shot, 'pix', 'comp')
        if not os.path.isdir(dirpath):
            return None
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
        if len(sorted_entries) == 0:
            return None
        else:
            return sorted_entries[-1][1]    

    def __init__(self):
        QAction.__init__(self, "Build Shot Layers", None)
        self.triggered.connect(self.build_shot_layers)
        hiero.core.events.registerInterest("kShowContextMenu/kTimeline", self.eventHandler)

    def build_shot_layers(self):
    
        g_project = hiero.core.projects()[-1]
        g_sequence = hiero.ui.activeSequence()

        plate_bin = self.get_bin(g_project, "plate")
        comp_bin = self.get_bin(g_project, "comp")
        rendered_comp_bin = self.get_bin(g_project, "rendered_comp")
   
        plate_track = self.get_track(g_sequence, "plate")
        comp_track = self.get_track(g_sequence, "comp")
        rendered_comp_track = self.get_track(g_sequence, "rendered_comp")
        cc_video_track = self.get_track(g_sequence, "cc")

        for ti in hiero.ui.getTimelineEditor(g_sequence).selection():
            match = self.g_shot_re.match(ti.name())
            if match:
                c_shot = match.group(0)
                c_seq = c_shot[0:3]
                print "INFO: Examining VFX shot %s on timeline."%c_shot
                c_shot_path = os.path.join(self.g_show_path, c_seq, c_shot)
                if not os.path.isdir(c_shot_path):
                    continue
                print "INFO: Located shot at %s."%c_shot_path
                # create the plate
                plate_tmp_dir = self.latest_element(c_shot, "plate")
                if not plate_tmp_dir:
                    continue
                tmp_exr_plate_file = os.path.join(plate_tmp_dir, "%s.%%04d.exr"%os.path.basename(plate_tmp_dir))
                tmp_exr_plate_ms = hiero.core.MediaSource(tmp_exr_plate_file)
                # assume 8 frame handles, and we all know what happens when you assume
                tmp_exr_plate_clip = hiero.core.Clip(tmp_exr_plate_ms)
                plate_bin.addItem(hiero.core.BinItem(tmp_exr_plate_clip))
                # Create EXR Plate TrackItem
                tmp_exr_plate_track_item = plate_track.createTrackItem(c_shot)
                tmp_exr_plate_track_item.setSource(tmp_exr_plate_clip)
                tmp_exr_plate_track_item.setSourceIn(8)
                tmp_exr_plate_track_item.setTimelineIn(ti.timelineIn())
                tmp_exr_plate_track_item.setTimelineOut(ti.timelineOut())
                tmp_exr_plate_track_item.setPlaybackSpeed(1.0)
                tmp_exr_plate_track_item.reformatState().setType("disabled")
                plate_track.addItem(tmp_exr_plate_track_item)
        
                # create the rendered comp
                comp_tmp_dir = self.latest_element(c_shot, "comp")
                if not comp_tmp_dir:
                    continue
                tmp_exr_comp_file = os.path.join(comp_tmp_dir, "%s.%%04d.exr"%os.path.basename(comp_tmp_dir))
                tmp_exr_comp_ms = hiero.core.MediaSource(tmp_exr_comp_file)
                # assume 8 frame handles, and we all know what happens when you assume
                tmp_exr_comp_clip = hiero.core.Clip(tmp_exr_comp_ms)
                rendered_comp_bin.addItem(hiero.core.BinItem(tmp_exr_comp_clip))
                # Create EXR comp TrackItem
                tmp_exr_comp_track_item = rendered_comp_track.createTrackItem(c_shot)
                tmp_exr_comp_track_item.setSource(tmp_exr_comp_clip)
                tmp_exr_comp_track_item.setSourceIn(9 if (tmp_exr_comp_ms.startTime() == 1000) else 8)
                tmp_exr_comp_track_item.setTimelineIn(ti.timelineIn())
                tmp_exr_comp_track_item.setTimelineOut(ti.timelineOut())
                tmp_exr_comp_track_item.setPlaybackSpeed(1.0)
                tmp_exr_comp_track_item.reformatState().setType("disabled")
                rendered_comp_track.addItem(tmp_exr_comp_track_item)
        
                # create the Nuke script
                tmp_nk_comp_file = os.path.join(c_shot_path, "nuke", "%s.nk"%os.path.basename(comp_tmp_dir))
                if not os.path.exists(tmp_nk_comp_file):
                    continue
                tmp_nk_comp_ms = hiero.core.MediaSource(tmp_nk_comp_file)
                # assume 8 frame handles, and we all know what happens when you assume
                tmp_nk_comp_clip = None
                try:
                    tmp_nk_comp_clip = hiero.core.Clip(tmp_nk_comp_ms)
                except RuntimeError as e:
                    print "ERROR: Brad is an idiot. Comp script for %s will not parse."%tmp_nk_comp_file
                    continue
                comp_bin.addItem(hiero.core.BinItem(tmp_nk_comp_clip))
                # Create Nuke comp TrackItem
                tmp_nk_comp_track_item = rendered_comp_track.createTrackItem(c_shot)
                tmp_nk_comp_track_item.setSource(tmp_nk_comp_clip)
                tmp_nk_comp_track_item.setSourceIn(8)
                tmp_nk_comp_track_item.setTimelineIn(ti.timelineIn())
                tmp_nk_comp_track_item.setTimelineOut(ti.timelineOut())
                tmp_nk_comp_track_item.setPlaybackSpeed(1.0)
                tmp_nk_comp_track_item.reformatState().setType("disabled")
                comp_track.addItem(tmp_nk_comp_track_item)
        
                # Add Color Correction Layer
                cs_effect = hiero.core.EffectTrackItem('OCIOColorSpace', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
                cs_effect.node().knob('out_colorspace').setValue('AlexaV3LogC')
                cc_video_track.addSubTrackItem(cs_effect, 0)

                tmp_cdl_file = os.path.join(c_shot_path, 'data', 'cdl', '%s.cdl'%c_shot)
                cdl_effect = hiero.core.EffectTrackItem('OCIOCDLTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
                cdl_effect.node().knob('read_from_file').setValue(True)
                cdl_effect.node().knob('file').setValue(tmp_cdl_file)
                cc_video_track.addSubTrackItem(cdl_effect, 1)

                lut_effect = hiero.core.EffectTrackItem('OCIOFileTransform', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
                lut_effect.node().knob('file').setValue(self.g_s_show_lut)
                cc_video_track.addSubTrackItem(lut_effect, 2)

                cs_effect_two = hiero.core.EffectTrackItem('OCIOColorSpace', timelineIn=ti.timelineIn(), timelineOut=ti.timelineOut())
                cs_effect_two.node().knob('in_colorspace').setValue('rec709')
                cc_video_track.addSubTrackItem(cs_effect_two, 3)

    def eventHandler(self, event):
        enabled = True
        title = "Build Shot Layers"
        self.setText(title)
        event.menu.addAction( self )

# The act of initialising the action adds it to the right-click menu...
BuildShotLayersInstance = BuildShotLayers()

