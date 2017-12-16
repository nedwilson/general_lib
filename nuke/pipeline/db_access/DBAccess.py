#!/usr/bin/python

import abc

# main DBAccess class definition
# contains static methods for the DBAccess class factory, as well as generic housekeeping tasks

class DBAccess(object):

    __metaclass__ = abc.ABCMeta
    
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
    def fetch_artist_from_id(self, m_artist_id):                
        """Returns an artist object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def fetch_tasks_for_shot(self, m_shot_obj):
        """Returns an array of task objects assosciated with the shot object from the database"""

    @abc.abstractmethod
    def fetch_task_from_id(self, m_task_id, m_shot_obj):
        """Returns a task object assosciated with the shot object from the database using the database ID as a search parameter"""
            
    @abc.abstractmethod
    def fetch_version(self, m_version_name, m_shot_obj):
        """Returns a version object from the database"""

    @abc.abstractmethod
    def fetch_version_from_id(self, m_version_id):
        """Returns a version object from the database using the database ID as a search parameter"""

    @abc.abstractmethod
    def fetch_playlist(self, m_playlist_name):                
        """Returns a playlist object from the database"""

    @abc.abstractmethod
    def create_playlist(self, m_playlist_obj):
        """Creates a playlist based on the object provided, and populates the object with the resulting database query
           If the object already exists, with a g_dbid value != -1, method will perform update instead of create."""
    
    @abc.abstractmethod
    def create_sequence(self, m_seq_obj):
        """Creates a sequence based on the object provided, and populates the object with the resulting database query"""

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
    def upload_thumbnail(self, m_entity_type, m_entity, m_thumb_path):
        """Uploads a thumbnail to the database and attaches it to a specific entity"""
        