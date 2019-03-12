#
#
# db_access library
#
#

import ConfigParser
import sys
import os
import re

import DBAccess
import ShotgunDBAccess

# globals

class DBAccessGlobals():

    g_ih_show_code = None
    g_ih_show_root = None
    g_ih_show_cfg_path = None
    g_config = None
    g_python_class = None
    g_db_access_class = None
    g_shot_regexp = None
    g_shot_dir_format = None
    g_seq_dir_format = None
    g_thumb_template = None
    
    @staticmethod
    def populate_globals():
        try:
            DBAccessGlobals.g_ih_show_code = os.environ['IH_SHOW_CODE']
            DBAccessGlobals.g_ih_show_root = os.environ['IH_SHOW_ROOT']
            DBAccessGlobals.g_ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
            DBAccessGlobals.g_config = ConfigParser.ConfigParser()
            DBAccessGlobals.g_config.read(DBAccessGlobals.g_ih_show_cfg_path)
            DBAccessGlobals.g_python_class = DBAccessGlobals.g_config.get('database', 'python_class')
            DBAccessGlobals.g_shot_regexp = re.compile(DBAccessGlobals.g_config.get(DBAccessGlobals.g_ih_show_code, 'shot_regexp'))
            DBAccessGlobals.g_shot_dir_format = DBAccessGlobals.g_config.get(DBAccessGlobals.g_ih_show_code, 'shot_dir_format')
            DBAccessGlobals.g_seq_dir_format = DBAccessGlobals.g_config.get(DBAccessGlobals.g_ih_show_code, 'seq_dir_format')
            DBAccessGlobals.g_thumb_template = DBAccessGlobals.g_config.get('thumbnails', 'template_%s'%sys.platform)
        except ConfigParser.NoSectionError:
            e = sys.exc_info()
            print "ERROR: caught %s when attempting to populate globals, with message %s"%(e[0],e[1])
            raise e
        except ConfigParser.NoOptionError:
            e = sys.exc_info()
            print "ERROR: caught %s when attempting to populate globals, with message %s"%(e[0],e[1])
            raise e
        except:        
            e = sys.exc_info()
            print "ERROR: caught %s when attempting to populate globals, with message %s"%(e[0],e[1])
            raise e
    
    @staticmethod
    def get_db_access(m_logger_object=None):

        if DBAccessGlobals.g_db_access_class:
            return DBAccessGlobals.g_db_access_class

        if not DBAccessGlobals.g_ih_show_code:
            DBAccessGlobals.populate_globals()
        
        types = [sc.__name__ for sc in DBAccess.DBAccess.__subclasses__()]
        if not DBAccessGlobals.g_python_class in types:
            raise NotImplementedError("No class definition available for DBAccess subclass %s"%DBAccessGlobals.g_python_class)
        else:
            DBAccessGlobals.g_db_access_class = eval('%s.%s()'%(DBAccessGlobals.g_python_class, DBAccessGlobals.g_python_class))
            if m_logger_object:
                DBAccessGlobals.g_db_access_class.set_logger_object(m_logger_object)
            return DBAccessGlobals.g_db_access_class
    
    @staticmethod
    def get_path_for_shot(m_shot_code):
        if not DBAccessGlobals.g_ih_show_code:
            DBAccessGlobals.populate_globals()

        matchobject = DBAccessGlobals.g_shot_regexp.search(m_shot_code)
        shot = None
        seq = None
        # make sure this file matches the shot pattern
        if not matchobject:
            raise ValueError("Shot name provided %s does not match regular expression!")
        else:
            shot = matchobject.groupdict()['shot']
            seq = matchobject.groupdict()['sequence']
        shot_dir = DBAccessGlobals.g_shot_dir_format.format(show_root=DBAccessGlobals.g_ih_show_root, sequence=seq, shot=shot, pathsep=os.path.sep)
        return shot_dir

    @staticmethod
    def get_path_for_sequence(m_seq_code):
        if not DBAccessGlobals.g_ih_show_code:
            DBAccessGlobals.populate_globals()

        seq_dir = DBAccessGlobals.g_seq_dir_format.format(show_root=DBAccessGlobals.g_ih_show_root, sequence=m_seq_code, pathsep=os.path.sep)
        return seq_dir


# imports of data classes
