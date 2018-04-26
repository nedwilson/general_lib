#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Task():

    def __init__(self, m_task_name, m_artist, m_status, m_shot, m_dbid):
        self.g_task_name = m_task_name
        self.g_artist = m_artist
        self.g_status = m_status
        self.g_shot = m_shot
        self.g_dbid = m_dbid

    def __str__(self):
        ret_str = """class Task():
    Name: {g_task_name}
    Artist: {g_artist}
    Status: {g_status}
    Shot: {g_shot}
    DBID: {g_dbid}
""".format(g_task_name = self.g_task_name,
           g_artist = self.g_artist.g_full_name,
           g_status = self.g_status,
           g_shot = self.g_shot.g_shot_code,
           g_dbid = self.g_dbid)
        return ret_str

