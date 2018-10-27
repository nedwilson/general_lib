#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Playlist():

    def __init__(self, m_playlist_name, m_playlist_versions, m_dbid):
        self.g_playlist_name = m_playlist_name
        self.g_playlist_versions = m_playlist_versions
        self.g_dbid = m_dbid
    def __str__(self):
        ret_str = """class Playlist():
    Name: {g_playlist_name}
    Versions: {g_playlist_versions}
    DBID: {g_dbid}
""".format(g_playlist_name = self.g_playlist_name, 
           g_playlist_versions = ', '.join([ver.g_version_code for ver in self.g_playlist_versions]),
           g_dbid = self.g_dbid)
        return ret_str
        
