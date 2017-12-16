#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Shot():

    def __init__(self, m_shot_code, m_path, m_dbid, m_sequence, m_task_template, m_head_in, m_cut_in, m_cut_out, m_tail_out, m_cut_duration):
        self.g_shot_code = m_shot_code
        self.g_path = m_path
        self.g_dbid = m_dbid
        self.g_sequence = m_sequence
        self.g_task_template = m_task_template
        self.g_head_in = m_head_in
        self.g_cut_in = m_cut_in
        self.g_cut_out = m_cut_out
        self.g_tail_out = m_tail_out
        self.g_cut_duration = m_cut_duration
    def __str__(self):
        ret_str = """class Shot():
    Name: {g_shot_code}
    Path: {g_path}
    DBID: {g_dbid}
    Sequence: {g_sequence}
    Task Template: {g_task_template}
    Head In: {g_head_in}
    Cut In: {g_cut_in}
    Cut Out: {g_cut_out}
    Tail Out: {g_tail_out}
    Cut Duration: {g_cut_duration}
""".format(g_shot_code = self.g_shot_code, 
           g_path = self.g_path, 
           g_dbid = self.g_dbid, 
           g_sequence = self.g_sequence.g_seq_code, 
           g_task_template = self.g_task_template, 
           g_head_in = self.g_head_in, 
           g_cut_in = self.g_cut_in, 
           g_cut_out = self.g_cut_out, 
           g_tail_out = self.g_tail_out, 
           g_cut_duration = self.g_cut_duration)
        return ret_str

