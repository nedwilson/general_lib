#!/usr/bin/python

import abc

# main DBAccess class definition
# contains static methods for the DBAccess class factory, as well as generic housekeeping tasks

class DBAccess(object):

    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def set_logger_object(self, m_logger_object):
        """Sets a logger object to use"""

    @abc.abstractmethod
    def set_project_id(self, m_project_id):
        """The default project ID is set by the config file. Call this method if you wish to use a different project ID."""

    @abc.abstractmethod
    def log_message(self, m_log_level, m_log_message):
        """Uses the logger object defined in set_logger_object() to write a message,
           or creates a new one if none exists. m_log_level should be one of critical,
           error, warning, info, or debug."""

    @abc.abstractmethod
    def fetch_shot(self, m_shot_code):
        """Returns a shot object from the database"""

    @abc.abstractmethod
    def fetch_shot_from_id(self, m_shot_id):
        """Returns a shot object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def fetch_plate(self, m_plate_name, m_shot_obj):
        """Returns a plate object from the database"""

    @abc.abstractmethod
    def fetch_sequence(self, m_seq_code):
        """Returns a sequence object from the database"""

    @abc.abstractmethod
    def fetch_artist(self, m_full_name):                
        """Returns an artist object from the database"""

    @abc.abstractmethod
    def fetch_artist_from_username(self, m_username):                
        """Returns an artist object from the database"""

    @abc.abstractmethod
    def fetch_artist_from_id(self, m_artist_id):                
        """Returns an artist object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def fetch_tasks_for_shot(self, m_shot_obj):
        """Returns an array of task objects assosciated with the shot object from the database"""

    @abc.abstractmethod
    def fetch_task_from_id(self, m_task_id, m_shot_obj):
        """Returns a task object assosciated with the shot object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def update_task_status(self, m_task_obj):
        """Sets a status on an existing task."""

    @abc.abstractmethod
    def update_version_status(self, m_version_obj):
        """Sets a status on an existing version."""

    @abc.abstractmethod
    def update_version_matte_delivered(self, m_version_obj):
        """Sets matte delivered to true on an existing version."""
        
    @abc.abstractmethod
    def update_shot_status(self, m_shot_obj):
        """Sets a status on an existing shot."""
            
    @abc.abstractmethod
    def fetch_version(self, m_version_name, m_shot_obj):
        """Returns a version object from the database"""

    @abc.abstractmethod
    def fetch_version_from_id(self, m_version_id):
        """Returns a version object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def fetch_versions_with_status(self, m_status):
        """Returns a list of versions in the database matching the status provided"""

    @abc.abstractmethod
    def fetch_versions_with_mattes(self):
        """Returns a list of versions in the database with mattes ready to deliver"""

    @abc.abstractmethod
    def fetch_versions_for_shot(self, m_shot_obj):
        """Returns a list of versions in the database that have been submitted for a particular shot"""

    @abc.abstractmethod
    def fetch_versions_for_entity(self, m_version_name, m_entity_type, m_entity_id):
        """Returns a list of versions in the database, linked to an entity with id m_entity_id and of type
           m_entity_type, and where the name is m_version_name."""

    @abc.abstractmethod
    def fetch_playlist(self, m_playlist_name):                
        """Returns a playlist object from the database"""

    @abc.abstractmethod
    def fetch_playlists_timeframe(self, m_days_back=30, m_populate_versions=False):
        """Returns a list of playlist objects from the database created in the last N days. Default is 30 days, add
           m_days_back paramater to change the timeframe. Set m_populate_versions = True to retreive database objects
           for each version in the Playlist. Set to False by default since this is slow."""

    @abc.abstractmethod
    def fetch_notes_for_version(self, m_version_obj, b_populate_playlists=False):                
        """Returns a list of Note objects linked to a particular version. By default, it will not attempt
           to fill playlist objects with a database record for each version. However, setting b_populate_playlists 
           to True will turn this on. Warning, it's slow."""

    @abc.abstractmethod
    def create_playlist(self, m_playlist_obj):
        """Creates a playlist based on the object provided, and populates the object with the resulting database query
           If the object already exists, with a g_dbid value != -1, method will perform update instead of create."""

    @abc.abstractmethod
    def delete_playlist(self, m_playlist_obj):
        """Deletes a playlist with id matching m_playlist_obj.g_dbid"""
        
    @abc.abstractmethod
    def create_sequence(self, m_seq_obj):
        """Creates a sequence based on the object provided, and populates the object with the resulting database query"""

    @abc.abstractmethod
    def create_task(self, m_task_obj):
        """Creates a task based on the object provided, and populates the object with the resulting database query"""

    @abc.abstractmethod
    def create_shot(self, m_shot_obj):
        """Creates a shot based on the object provided, and populates the object with the resulting database query"""

    @abc.abstractmethod
    def create_version(self, m_version_obj):
        """Creates a version based on the object provided, and populates the object with the resulting database query"""
                
    @abc.abstractmethod
    def create_plate(self, m_plate_obj):
        """Creates a plate based on the object provided, and populates the object with the resulting database query"""

    @abc.abstractmethod
    def create_note(self, m_note_obj):
        """Creates a note based on the object provided, and populates the object with the resulting database query"""
        
    @abc.abstractmethod
    def upload_thumbnail(self, m_entity_type, m_entity, m_thumb_path):
        """Uploads a thumbnail to the database and attaches it to a specific entity"""

    @abc.abstractmethod
    def upload_movie(self, m_entity_type, m_entity, m_movie_path):
        """Uploads a movie file to the database and attaches it to a specific entity"""

    @abc.abstractmethod
    def publish_for_shot(self, m_shot_obj, m_publish_path, m_clean_notes):
        """Publishes an item for a shot"""

    @abc.abstractmethod
    def publish_for_ingest(self, m_shot_obj, m_publish_path, m_publish_name, m_publish_notes, m_publish_file_type):
        """Publishes a plate from the scan ingestion process, which will either be a Quicktime Movie or an Image Sequence.
           Supported publish file types are currently Movie or Plate."""
        