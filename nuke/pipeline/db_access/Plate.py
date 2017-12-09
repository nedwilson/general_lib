#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Plate():

    def __init__(self):
        self.g_plate_name = None
        self.g_start_frame = None
        self.g_end_frame = None
        self.g_duration = None
        self.g_filesystem_path = None
        self.g_start_timecode = None
        self.g_clip_name = None
        self.g_scene = None
        self.g_take = None
        self.g_end_timecode = None
        self.g_shot = None
        self.g_dbid = None
                
    def __init__(self, m_plate_name, m_start_frame, m_end_frame, m_duration, m_filesystem_path, m_start_timecode, m_clip_name, m_scene, m_take, m_end_timecode, m_shot, m_dbid):
        self.g_plate_name = m_plate_name
        self.g_start_frame = m_start_frame
        self.g_end_frame = m_end_frame
        self.g_duration = m_duration
        self.g_filesystem_path = m_filesystem_path
        self.g_start_timecode = m_start_timecode
        self.g_clip_name = m_clip_name
        self.g_scene = m_scene
        self.g_take = m_take
        self.g_end_timecode = m_end_timecode
        self.g_shot = m_shot
        self.g_dbid = m_dbid

    def __str__(self):
        ret_str = """class Plate():
    Name: {g_plate_name}
    Start Frame: {g_start_frame}
    End Frame: {g_end_frame}
    Duration: {g_duration}
    Filesystem Path: {g_filesystem_path}
    Start TimeCode: {g_start_timecode}
    Clip Name: {g_clip_name}
    Scene: {g_scene}
    Take: {g_take}
    End TimeCode: {g_end_timecode}
    Shot: {g_shot}
    DBID: {g_dbid}
""".format(g_plate_name = self.g_plate_name,
           g_start_frame = self.g_start_frame,
           g_end_frame = self.g_end_frame,
           g_duration = self.g_duration,
           g_filesystem_path = self.g_filesystem_path,
           g_start_timecode = self.g_start_timecode,
           g_clip_name = self.g_clip_name,
           g_scene = self.g_scene,
           g_take = self.g_take,
           g_end_timecode = self.g_end_timecode,
           g_shot = self.g_shot.g_shot_code,
           g_dbid = self.g_dbid)
        return ret_str

