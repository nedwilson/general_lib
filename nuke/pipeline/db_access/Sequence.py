#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Sequence():

#     def __init__(self):
#         self.g_seq_code = None
#         self.g_path = None
#         self.g_dbid = None
#         
    def __init__(self, m_seq_code, m_path, m_dbid):
        self.g_seq_code = m_seq_code
        self.g_path = m_path
        self.g_dbid = m_dbid
    def __str__(self):
        ret_str = """class Sequence():
    Name: {g_seq_code}
    Path: {g_path}
    DBID: {g_dbid}
""".format(g_seq_code = self.g_seq_code, 
           g_path = self.g_path, 
           g_dbid = self.g_dbid)
        return ret_str
        
