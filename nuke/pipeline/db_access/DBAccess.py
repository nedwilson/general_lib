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
    def fetch_plate(self, m_plate_name, m_shot_obj):
        """Returns a plate object from the database"""

    @abc.abstractmethod
    def fetch_sequence(self, m_seq_code):
        """Returns a sequence object from the database"""

    @abc.abstractmethod
    def create_sequence(self, m_seq_obj):
        """Creates a sequence based on the object provided, and populates the object with the resulting database query"""

    @abc.abstractmethod
    def create_shot(self, m_shot_obj):
        """Creates a shot based on the object provided, and populates the object with the resulting database query"""
            
    @abc.abstractmethod
    def create_plate(self, m_plate_obj):
        """Creates a plate based on the object provided, and populates the object with the resulting database query"""
        
        