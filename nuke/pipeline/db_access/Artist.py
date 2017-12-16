#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Artist():

    def __init__(self, m_first_name, m_last_name, m_username, m_dbid):
        self.g_first_name = m_first_name
        self.g_last_name = m_last_name
        self.g_full_name = "%s %s"%(m_first_name, m_last_name)
        self.g_username = m_username
        self.g_dbid = m_dbid

    def __str__(self):
        ret_str = """class Artist():
    Name: {g_full_name}
    Username: {g_username}
    DBID: {g_dbid}
""".format(g_full_name = self.g_full_name,
           g_username = self.g_username,
           g_dbid = self.g_dbid)
        return ret_str

