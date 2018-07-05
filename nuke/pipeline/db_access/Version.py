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
    def set_status(self, m_status):
        self.g_status = m_status
    def set_delivered(self, m_delivered):
        self.g_delivered = m_delivered
    def set_client_code(self, m_client_code):
        self.g_client_code = m_client_code
    def set_playlists(self, m_playlists):
        self.g_playlists = m_playlists
    def __str__(self):
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
           g_shot = self.g_shot.g_shot_code,
           g_artist = self.g_artist.g_full_name,
           g_task = self.g_task.g_task_name,
           g_status = self.g_status,
           g_delivered = self.g_delivered,
           g_client_code = self.g_client_code,
           g_playlists = ', '.join([pl.g_playlist_name for pl in self.g_playlists]))
        return ret_str

