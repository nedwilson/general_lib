#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Version():

    def __init__(self, 
                 m_version_code, 
                 m_dbid,
                 m_description,
                 m_start_frame, 
                 m_end_frame,
                 m_duration,
                 m_path_to_frames,
                 m_path_to_movie,
                 m_shot,
                 m_artist,
                 m_task):
        self.g_version_code = m_version_code 
        self.g_dbid = m_dbid
        self.g_description = m_description
        self.g_start_frame = m_start_frame 
        self.g_end_frame = m_end_frame
        self.g_duration = m_duration
        self.g_path_to_frames = m_path_to_frames
        self.g_path_to_movie = m_path_to_movie
        self.g_shot = m_shot
        self.g_artist = m_artist
        self.g_task = m_task
        self.g_status = 'rev'
        self.g_delivered = False
        self.g_client_code = None
        self.g_playlists = None
        self.g_path_to_matte_frames = None
        self.g_matte_only = False
        self.g_matte_ready = False
        self.g_matte_delivered = False
        self.g_version_type = None
        self.g_version_entity = None
        self.g_path_to_dnxhd = None
        self.g_path_to_export = None
    def set_status(self, m_status):
        self.g_status = m_status
    def set_delivered(self, m_delivered):
        self.g_delivered = m_delivered
    def set_path_to_matte_frames(self, m_path_to_matte_frames):
        self.g_path_to_matte_frames = m_path_to_matte_frames
    def set_matte_only(self, m_matte_only):
        self.g_matte_only = m_matte_only
    def set_matte_ready(self, m_matte_ready):
        self.g_matte_ready = m_matte_ready
    def set_matte_delivered(self, m_matte_delivered):
        self.g_matte_delivered = m_matte_delivered
    def set_client_code(self, m_client_code):
        self.g_client_code = m_client_code
    def set_playlists(self, m_playlists):
        self.g_playlists = m_playlists
    def set_version_type(self, m_version_type):
        self.g_version_type = m_version_type
    def set_version_entity(self, m_version_entity):
        self.g_version_entity = m_version_entity
    def set_path_to_dnxhd(self, m_path_to_dnxhd):
        self.g_path_to_dnxhd = m_path_to_dnxhd
    def set_path_to_export(self, m_path_to_export):
        self.g_path_to_export = m_path_to_export
    def __str__(self):
        task = 'NULL'
        if self.g_task:
            task = self.g_task.task_name
        shot = 'NULL'
        if self.g_shot:
            shot = self.g_shot.s_shot_code
        artist = 'NULL'
        if self.g_artist:
            artist = self.g_artist.g_full_name
        ret_str = """class Version():
    Version Name: {g_version_code} 
    DBID: {g_dbid}
    Description: {g_description}
    Start Frame: {g_start_frame} 
    End Frame: {g_end_frame}
    Duration: {g_duration}
    Path to Frames: {g_path_to_frames}
    Path to Quicktime: {g_path_to_movie}
    Shot: {g_shot}
    Artist: {g_artist}
    Task: {g_task}
    Status: {g_status}
    Delivered: {g_delivered}
    Client Version Name: {g_client_code}
    Playlist(s): {g_playlists}
    Entity: {g_version_entity}
""".format(g_version_code = self.g_version_code, 
           g_dbid = self.g_dbid,
           g_description = self.g_description,
           g_start_frame = self.g_start_frame, 
           g_end_frame = self.g_end_frame,
           g_duration = self.g_duration,
           g_path_to_frames = self.g_path_to_frames,
           g_path_to_movie = self.g_path_to_movie,
           g_shot = shot,
           g_artist = artist,
           g_task = task,
           g_status = self.g_status,
           g_delivered = self.g_delivered,
           g_client_code = self.g_client_code,
           g_playlists = ', '.join([pl.g_playlist_name for pl in self.g_playlists]),
           g_version_entity = str(self.g_version_entity))
        return ret_str
    def __repr__(self):
        task = 'NULL'
        if self.g_task:
            task = self.g_task.task_name
        shot = 'NULL'
        if self.g_shot:
            shot = self.g_shot.s_shot_code
        artist = 'NULL'
        if self.g_artist:
            artist = self.g_artist.g_full_name
        ret_str = """class Version():
    Version Name: {g_version_code} 
    DBID: {g_dbid}
    Description: {g_description}
    Start Frame: {g_start_frame} 
    End Frame: {g_end_frame}
    Duration: {g_duration}
    Path to Frames: {g_path_to_frames}
    Path to Quicktime: {g_path_to_movie}
    Shot: {g_shot}
    Artist: {g_artist}
    Task: {g_task}
    Status: {g_status}
    Delivered: {g_delivered}
    Client Version Name: {g_client_code}
    Playlist(s): {g_playlists}
""".format(g_version_code = self.g_version_code, 
           g_dbid = self.g_dbid,
           g_description = self.g_description,
           g_start_frame = self.g_start_frame, 
           g_end_frame = self.g_end_frame,
           g_duration = self.g_duration,
           g_path_to_frames = self.g_path_to_frames,
           g_path_to_movie = self.g_path_to_movie,
           g_shot = shot,
           g_artist = artist,
           g_task = task,
           g_status = self.g_status,
           g_delivered = self.g_delivered,
           g_client_code = self.g_client_code,
           g_playlists = ', '.join([pl.g_playlist_name for pl in self.g_playlists]))
        return ret_str

