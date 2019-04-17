#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Version():

    def __init__(self, 
                 m_version_code = None, 
                 m_dbid = -1,
                 m_description = None,
                 m_start_frame = -1, 
                 m_end_frame = -1,
                 m_duration = -1,
                 m_path_to_frames = None,
                 m_path_to_movie = None,
                 m_shot = None,
                 m_artist = None,
                 m_task = None):
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

        self.data = {}

        self.data['g_version_code'] = m_version_code 
        self.data['g_dbid'] = m_dbid
        self.data['g_description'] = m_description
        self.data['g_start_frame'] = m_start_frame 
        self.data['g_end_frame'] = m_end_frame
        self.data['g_duration'] = m_duration
        self.data['g_path_to_frames'] = m_path_to_frames
        self.data['g_path_to_movie'] = m_path_to_movie
        self.data['g_shot'] = m_shot
        self.data['g_artist'] = m_artist
        self.data['g_task'] = m_task
        self.data['g_status'] = 'rev'
        self.data['g_delivered'] = False
        self.data['g_client_code'] = None
        self.data['g_playlists'] = None
        self.data['g_path_to_matte_frames'] = None
        self.data['g_matte_only'] = False
        self.data['g_matte_ready'] = False
        self.data['g_matte_delivered'] = False
        self.data['g_version_type'] = None
        self.data['g_version_entity'] = None
        self.data['g_path_to_dnxhd'] = None
        self.data['g_path_to_export'] = None

    # populate this object, initialized with None/-1, from a dictionary. Useful if the object has been serialized.
    def populate_from_dictionary(self, m_data_dict):
        # first, populate the data dictionary
        if not self.data:
            self.data = {}
        self.data['g_version_code'] = m_data_dict['g_version_code']
        self.data['g_dbid'] = int(m_data_dict['g_dbid'])
        self.data['g_description'] = m_data_dict['g_description']
        self.data['g_start_frame'] = int(m_data_dict['g_start_frame'])
        self.data['g_end_frame'] = int(m_data_dict['g_end_frame'])
        self.data['g_duration'] = int(m_data_dict['g_duration'])
        self.data['g_path_to_frames'] = m_data_dict['g_path_to_frames']
        self.data['g_path_to_movie'] = m_data_dict['g_path_to_movie']
        self.data['g_shot'] = m_data_dict['g_shot']
        self.data['g_artist'] = m_data_dict['g_artist']
        self.data['g_task'] = m_data_dict['g_task']
        self.data['g_status'] = m_data_dict['g_status']
        self.data['g_delivered'] = m_data_dict['g_delivered']
        self.data['g_client_code'] = m_data_dict['g_client_code']
        self.data['g_playlists'] = m_data_dict['g_playlists']
        self.data['g_path_to_matte_frames'] = m_data_dict['g_path_to_matte_frames']
        self.data['g_matte_only'] = m_data_dict['g_matte_only']
        self.data['g_matte_ready'] = m_data_dict['g_matte_ready']
        self.data['g_matte_delivered'] = m_data_dict['g_matte_delivered']
        self.data['g_version_type'] = m_data_dict['g_version_type']
        self.data['g_version_entity'] = m_data_dict['g_version_entity']
        self.data['g_path_to_dnxhd'] = m_data_dict['g_path_to_dnxhd']
        self.data['g_path_to_export'] = m_data_dict['g_path_to_export']
        # then, populate the class variables
        self.g_version_code = m_data_dict['g_version_code']
        self.g_dbid = int(m_data_dict['g_dbid'])
        self.g_description = m_data_dict['g_description']
        self.g_start_frame = int(m_data_dict['g_start_frame'])
        self.g_end_frame = int(m_data_dict['g_end_frame'])
        self.g_duration = int(m_data_dict['g_duration'])
        self.g_path_to_frames = m_data_dict['g_path_to_frames']
        self.g_path_to_movie = m_data_dict['g_path_to_movie']
        self.g_shot = m_data_dict['g_shot']
        self.g_artist = m_data_dict['g_artist']
        self.g_task = m_data_dict['g_task']
        self.g_status = m_data_dict['g_status']
        self.g_delivered = m_data_dict['g_delivered']
        self.g_client_code = m_data_dict['g_client_code']
        self.g_playlists = m_data_dict['g_playlists']
        self.g_path_to_matte_frames = m_data_dict['g_path_to_matte_frames']
        self.g_matte_only = m_data_dict['g_matte_only']
        self.g_matte_ready = m_data_dict['g_matte_ready']
        self.g_matte_delivered = m_data_dict['g_matte_delivered']
        self.g_version_type = m_data_dict['g_version_type']
        self.g_version_entity = m_data_dict['g_version_entity']
        self.g_path_to_dnxhd = m_data_dict['g_path_to_dnxhd']
        self.g_path_to_export = m_data_dict['g_path_to_export']

    def set_status(self, m_status):
        self.data['g_status'] = m_status
        self.g_status = m_status
    def set_delivered(self, m_delivered):
        self.data['g_delivered'] = m_delivered
        self.g_delivered = m_delivered
    def set_path_to_matte_frames(self, m_path_to_matte_frames):
        self.data['g_path_to_matte_frames'] = m_path_to_matte_frames
        self.g_path_to_matte_frames = m_path_to_matte_frames
    def set_matte_only(self, m_matte_only):
        self.data['g_matte_only'] = m_matte_only
        self.g_matte_only = m_matte_only
    def set_matte_ready(self, m_matte_ready):
        self.data['g_matte_ready'] = m_matte_ready
        self.g_matte_ready = m_matte_ready
    def set_matte_delivered(self, m_matte_delivered):
        self.data['g_matte_delivered'] = m_matte_delivered
        self.g_matte_delivered = m_matte_delivered
    def set_client_code(self, m_client_code):
        self.data['g_client_code'] = m_client_code
        self.g_client_code = m_client_code
    def set_playlists(self, m_playlists):
        self.data['g_playlists'] = [pl.g_playlist_name for pl in m_playlists]
        self.g_playlists = m_playlists
    def set_version_type(self, m_version_type):
        self.data['g_version_type'] = m_version_type
        self.g_version_type = m_version_type
    def set_version_entity(self, m_version_entity):
        self.data['g_version_entity'] = m_version_entity
        self.g_version_entity = m_version_entity
    def set_path_to_dnxhd(self, m_path_to_dnxhd):
        self.data['g_path_to_dnxhd'] = m_path_to_dnxhd
        self.g_path_to_dnxhd = m_path_to_dnxhd
    def set_path_to_export(self, m_path_to_export):
        self.data['g_path_to_export'] = m_path_to_export
        self.g_path_to_export = m_path_to_export
    def __str__(self):
        task = 'NULL'
        if self.g_task:
            task = self.g_task.task_name
        shot = 'NULL'
        if self.g_shot:
            shot = self.g_shot.g_shot_code
        artist = 'NULL'
        if self.g_artist:
            artist = self.g_artist.g_full_name
        playlists = 'NULL'
        if self.g_playlists:
            playlists = ', '.join([pl.g_playlist_name for pl in self.g_playlists])
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
           g_playlists = playlists,
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
        playlists = 'NULL'
        if self.g_playlists:
            playlists = ', '.join([pl.g_playlist_name for pl in self.g_playlists])
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
           g_playlists = playlists)
        return ret_str

