#!/usr/bin/python

#
#
# db_access library
#
#

# data class definitions
    
class Note():

    def __init__(self, m_subject, m_to, m_from, m_links, m_body, m_type, m_dbid):
        self.g_subject = m_subject
        self.g_to = m_to
        self.g_from = m_from
        self.g_links = m_links
        self.g_body = m_body
        self.g_type = m_type
        self.g_dbid = m_dbid

    def __str__(self):
        ret_str = """class Note():
    Subject: {g_subject}
    To: {g_to}
    From: {g_from}
    Body: {g_body}
    Type: {g_type}
    DBID: {g_dbid}
""".format(g_subject = self.g_subject,
           g_to = self.g_to.g_full_name,
           g_from = self.g_from.g_full_name,
           g_body = self.g_body,
           g_type = self.g_type,
           g_dbid = self.g_dbid)
        
        ret_str += "    Links: "
        for link in self.g_links:
            if link.__class__.__name__ == "Version":
                ret_str += "Version %s, "%link.g_version_code
            elif link.__class__.__name__ == "Shot":
                ret_str += "Shot %s, "%link.g_shot_code
            elif link.__class__.__name__ == "Playlist":
                ret_str += "Playlist %s, "%link.g_playlist_name
        return ret_str.rstrip().rstrip(',')

