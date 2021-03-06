#!/usr/bin/python

import sys
import os
import re
import ConfigParser
import pprint
import threading
import traceback


import Sequence
import Shot
import Plate
import Version
import Task
import Artist
import Playlist
import Note

import DBAccessGlobals
import DBAccess

from timecode import TimeCode

import tinydb

# Shotgun-specific data source implementation

class TinyDBAccess(DBAccess.DBAccess):

    # updated from Shotgun to TinyDB
    def __init__(self):
        try:
            self.g_tinydbfile = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'tinydb_file_%s'%sys.platform)
            self.g_tinydb = tinydb.TinyDB(self.g_tinydbfile)
        except ConfigParser.NoSectionError:
            e = sys.exc_info()
            print e[1]
        except ConfigParser.NoOptionError:
            e = sys.exc_info()
            print e[1]
        except:        
            e = sys.exc_info()
            print e[1]

    # updated from Shotgun to TinyDB
    def fetch_shot(self, m_shot_code):
        # use the sequence matching regular expression here instead of hard coding m_shot_code[0:5]
        matchobject = DBAccessGlobals.DBAccessGlobals.g_shot_regexp.search(m_shot_code)
        shot = None
        seq = None
        # make sure this file matches the shot pattern
        if not matchobject:
            raise ValueError("Shot name provided %s does not match regular expression!"%m_shot_code)
        else:
            shot = matchobject.groupdict()['shot']
            seq = matchobject.groupdict()['sequence']
            
        local_seq = Sequence.Sequence(seq, DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(seq), -1)
        dbseq = self.fetch_sequence(seq)
        local_seq.g_dbid = dbseq.g_dbid
                    
        shot_ret = Shot.Shot(shot, DBAccessGlobals.DBAccessGlobals.get_path_for_shot(shot), -1, local_seq, None, 1001, 1009, 1092, 1100, 84)

        shot_table = self.g_tinydb.table('Shot')
        shot_query = tinydb.Query()
        dbshot = shot_table.get(shot_query.code == m_shot_code)
        if dbshot:
            shot_ret.g_dbid = dbshot.doc_id
            shot_ret.g_task_template = dbshot.task_template
            shot_ret.g_head_in = dbshot.sg_head_in
            shot_ret.g_cut_in = dbshot.sg_cut_in
            shot_ret.g_cut_out = dbshot.sg_cut_out
            shot_ret.g_tail_out = dbshot.sg_tail_out
            shot_ret.g_cut_duration = dbshot.sg_cut_duration

        return shot_ret

    # updated from Shotgun to TinyDB
    def fetch_shot_from_id(self, m_shot_id):

        shot_ret = Shot.Shot("BLANK", "", m_shot_id, None, None, 1001, 1009, 1092, 1100, 84)
        shot_ret = Shot.Shot(shot, DBAccessGlobals.DBAccessGlobals.get_path_for_shot(shot), -1, local_seq, None, 1001, 1009, 1092, 1100, 84)

        shot_table = self.g_tinydb.table('Shot')
        dbshot = shot_table.get(doc_id=m_shot_id)
        if dbshot:
            dbseq = self.fetch_sequence(dbshot.sg_sequence)
            shot_ret.g_sequence = dbseq            
            shot_ret.g_task_template = dbshot.task_template
            shot_ret.g_head_in = dbshot.sg_head_in
            shot_ret.g_cut_in = dbshot.sg_cut_in
            shot_ret.g_cut_out = dbshot.sg_cut_out
            shot_ret.g_tail_out = dbshot.sg_tail_out
            shot_ret.g_cut_duration = dbshot.sg_cut_duration

        return shot_ret

    # updated from Shotgun to TinyDB
    def fetch_plate(self, m_plate_name, m_shot_obj):
        plate_ret = Plate.Plate(m_plate_name,
                              1001,
                              1100,
                              100,
                              "",
                              "00:00:41:17",
                              "",
                              "",
                              "",
                              "00:00:45:20",
                              m_shot_obj,
                              -1)
        plate_table = self.g_tinydb.table('Plate')
        plate_query = tinydb.Query()
        dbplate = plate_table.get(plate_query.code == m_plate_name)
        if dbplate:
            plate_ret.g_dbid = dbplate.doc_id
            plate_ret.g_start_frame = dbplate.sg_start_frame
            plate_ret.g_end_frame = dbplate.sg_end_frame
            plate_ret.g_duration = dbplate.sg_duration
            plate_ret.g_filesystem_path = dbplate.sg_filesystem_path
            plate_ret.g_start_timecode = dbplate.sg_start_timecode
            plate_ret.g_clip_name = dbplate.sg_clip_name
            plate_ret.g_scene = dbplate.sg_scene
            plate_ret.g_take = dbplate.sg_take
            plate_ret.g_end_timecode = dbplate.sg_end_timecode
            
        return plate_ret

    # updated from Shotgun to TinyDB
    def fetch_sequence(self, m_seq_code):
        seq_path = DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(m_seq_code)
        seq_ret = Sequence.Sequence(m_seq_code, seq_path, -1)
        seq_table = self.g_tinydb.table('Sequence')
        seq_query = tinydb.Query()
        dbseq = seq_table.get(seq_query.code == m_seq_code)

        if dbseq:
            seq_ret.g_dbid = dbseq.doc_id
            
        return seq_ret

    # updated from Shotgun to TinyDB
    def fetch_artist(self, m_full_name):
        artist_ret = Artist.Artist('Alan', 'Smithee', 'alan', -1)
        name_list = m_full_name.split(' ')
        if len(name_list) == 0:
            return artist_ret
        artist_ret.g_first_name = name_list[0]
        if len(name_list) > 1:
            artist_ret.g_last_name = ' '.join(name_list[1:])
        else:
            artist_ret.g_last_name = ''

        artist_table = self.g_tinydb.table('Artist')
        artist_query = tinydb.Query()
        dbartist = artist_table.get((artist_query.firstname == artist_ret.g_first_name) & (artist_query.lastname == artist_ret.g_last_name))

        if dbartist:
            artist_ret.g_dbid = dbartist.doc_id
            artist_ret.g_username = dbartist.login
        return artist_ret

    # updated from Shotgun to TinyDB
    def fetch_artist_from_username(self, m_username):
        artist_ret = Artist.Artist('Alan', 'Smithee', 'alan', -1)
        if not m_username or m_username == '':
            return artist_ret
        else:
            artist_ret.g_username = m_username

        artist_table = self.g_tinydb.table('Artist')
        artist_query = tinydb.Query()
        dbartist = artist_table.get(artist_query.login == m_username)

        if dbartist:
            artist_ret.g_dbid = dbartist.doc_id
            artist_ret.g_first_name = dbartist.firstname
            artist_ret.g_last_name = dbartist.lastname
        return artist_ret

    # updated from Shotgun to TinyDB
    def fetch_artist_from_id(self, m_artist_id):
        artist_ret = Artist.Artist('Alan', 'Smithee', 'alan', -1)
        if not m_artist_id:
            return artist_ret
        else:
            artist_ret.g_dbid = m_artist_id

        artist_table = self.g_tinydb.table('Artist')
        dbartist = artist_table.get(doc_id=m_artist_id)

        if dbartist:
            artist_ret.g_username = dbartist.login
            artist_ret.g_first_name = dbartist.firstname
            artist_ret.g_last_name = dbartist.lastname
        return artist_ret

    def fetch_tasks_for_shot(self, m_shot_obj):
        tasks_array = []
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['entity', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}],
        ]
        fields = ['content', 'task_assignees', 'sg_status_list', 'entity', 'id']
        sg_tasks = self.g_sg.find("Task", filters, fields)
        if not sg_tasks:
            return tasks_array
        else:
            for sg_task in sg_tasks:
                artist = Artist.Artist('Alan', 'Smithee', 'asmithee', -1)
                if len(sg_task['task_assignees']) > 0:
                    try:
                        artist = self.fetch_artist_from_id(sg_task['task_assignees'][0]['id'])
                    except KeyError:
                        print "WARNING: Task %s appears to have a blank assignees list. Using generic Artist object."
                task_ret = Task.Task(sg_task['content'], artist, sg_task['sg_status_list'], m_shot_obj, sg_task['id'])
                tasks_array.append(task_ret)
            return tasks_array
    
    def fetch_task_from_id(self, m_task_id, m_shot_obj):
        task_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['entity', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}],
            ['id', 'is', m_task_id]
        ]
        fields = ['content', 'task_assignees', 'sg_status_list', 'entity', 'id']
        sg_task = self.g_sg.find_one("Task", filters, fields)
        if not sg_task:
            return task_ret
        else:
            # print threading.current_thread().getName()
            # print sg_task
            artist = None
            try:
                artist = self.fetch_artist_from_id(sg_task['task_assignees'][0]['id'])
            except:
                print "ERROR: Task assignees for task %s is NULL!"%sg_task
                artist = Artist.Artist('Alan', 'Smithee', 'asmithee', -1)
            task_ret = Task.Task(sg_task['content'], artist, sg_task['sg_status_list'], m_shot_obj, sg_task['id'])
            return task_ret

    def update_task_status(self, m_task_obj):
        data = {
            'sg_status_list' : m_task_obj.g_status,
        }
        self.g_sg.update('Task', m_task_obj.g_dbid, data)

    def update_version(self, m_version_obj):
        if m_version_obj.g_matte_only:
            data = {
                'sg_path_to_matte_frames' : m_version_obj.g_path_to_matte_frames
            }
            if m_version_obj.g_matte_ready : 
                data['sg_matte_ready_'] = True
            if m_version_obj.g_matte_delivered : 
                data['sg_matte_delivered_'] = True
        else:        
            data = {
                'description' : m_version_obj.g_description, 
                'sg_first_frame' : m_version_obj.g_start_frame, 
                'sg_last_frame' : m_version_obj.g_end_frame, 
                'frame_count' : m_version_obj.g_duration, 
                'sg_path_to_frames' : m_version_obj.g_path_to_frames, 
                'sg_path_to_movie' : m_version_obj.g_path_to_movie, 
                'user' : {'type' : 'HumanUser', 'id' : int(m_version_obj.g_artist.g_dbid)}, 
                'sg_status_list' : m_version_obj.g_status, 
                'sg_delivered' : str(m_version_obj.g_delivered)
            }
            if m_version_obj.g_client_code : 
                data['client_code'] = m_version_obj.g_client_code
            if m_version_obj.g_path_to_matte_frames : 
                data['sg_path_to_matte_frames'] = m_version_obj.g_path_to_matte_frames
            if m_version_obj.g_matte_ready : 
                data['sg_matte_ready_'] = True
            if m_version_obj.g_matte_delivered : 
                data['sg_matte_delivered_'] = True

        self.g_sg.update('Version', m_version_obj.g_dbid, data)

    def update_version_status(self, m_version_obj):
        data = {
            'sg_status_list' : m_version_obj.g_status,
        }
        if m_version_obj.g_delivered:
            data['sg_delivered'] = 'True'
            
        self.g_sg.update('Version', m_version_obj.g_dbid, data)

    def update_version_matte_delivered(self, m_version_obj):
        data = {
            'sg_matte_delivered_' : True
        }
        self.g_sg.update('Version', m_version_obj.g_dbid, data)

    def update_shot_status(self, m_shot_obj):
        data = {
            'sg_status_list' : m_shot_obj.g_status,
        }
        self.g_sg.update('Shot', m_shot_obj.g_dbid, data)
                        
    def fetch_version(self, m_version_name, m_shot_obj):
        ver_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['entity', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}],
            ['code', 'is', m_version_name]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task', 'sg_delivered', 'client_code', 'playlists', 'sg_path_to_matte_frames', 'sg_matte_ready_', 'sg_matte_delivered_']
        sg_ver = self.g_sg.find_one("Version", filters, fields)
        if not sg_ver:
            return ver_ret
        else:
            local_task = self.fetch_task_from_id(int(sg_ver['sg_task']['id']), m_shot_obj)
            local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
            ver_ret = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], m_shot_obj, local_artist, local_task)
            tmp_delivered = False
            if sg_ver['sg_delivered'] == 'True':
                tmp_delivered = True
            ver_ret.set_delivered(tmp_delivered)
            ver_ret.set_client_code(sg_ver['client_code'])
            tmp_playlists = []
            for tmp_pl_struct in sg_ver['playlists']:
                tmp_playlists.append(Playlist.Playlist(tmp_pl_struct['name'], [], tmp_pl_struct['id']))
            ver_ret.set_playlists(tmp_playlists)
            if sg_ver['sg_path_to_matte_frames']:
                ver_ret.set_path_to_matte_frames(sg_ver['sg_path_to_matte_frames'])
            if sg_ver['sg_matte_ready_'] == 'True':
                ver_ret.set_matte_ready(True)
            if sg_ver['sg_matte_delivered_'] == 'True':
                ver_ret.set_matte_delivered(True)
            return ver_ret

    def fetch_version_from_id(self, m_version_id):
        ver_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['id', 'is', m_version_id]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task', 'sg_delivered', 'client_code', 'playlists', 'sg_path_to_matte_frames', 'sg_matte_ready_', 'sg_matte_delivered_']
        sg_ver = self.g_sg.find_one("Version", filters, fields)
        if not sg_ver:
            return ver_ret
        else:
            local_shot = self.fetch_shot_from_id(sg_ver['entity']['id'])
            local_task = self.fetch_task_from_id(int(sg_ver['sg_task']['id']), local_shot)
            local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
            ver_ret = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], local_shot, local_artist, local_task)
            tmp_delivered = False
            if sg_ver['sg_delivered'] == 'True':
                tmp_delivered = True
            ver_ret.set_delivered(tmp_delivered)
            ver_ret.set_client_code(sg_ver['client_code'])
            tmp_playlists = []
            for tmp_pl_struct in sg_ver['playlists']:
                tmp_playlists.append(Playlist.Playlist(tmp_pl_struct['name'], [], tmp_pl_struct['id']))
            ver_ret.set_playlists(tmp_playlists)
            if sg_ver['sg_path_to_matte_frames']:
                ver_ret.set_path_to_matte_frames(sg_ver['sg_path_to_matte_frames'])
            if sg_ver['sg_matte_ready_'] == 'True':
                ver_ret.set_matte_ready(True)
            if sg_ver['sg_matte_delivered_'] == 'True':
                ver_ret.set_matte_delivered(True)
            return ver_ret

    def fetch_versions_with_status(self, m_status):
        ver_ret = []
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['sg_status_list', 'is', m_status]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task', 'sg_delivered', 'client_code', 'playlists', 'sg_path_to_matte_frames', 'sg_matte_ready_', 'sg_matte_delivered_']
        sg_vers = self.g_sg.find("Version", filters, fields)
        if not sg_vers:
            return ver_ret
        else:
            for sg_ver in sg_vers:
                shot_obj = self.fetch_shot_from_id(sg_ver['entity']['id'])
                local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
                tmp_ver = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], shot_obj, local_artist, None)
                tmp_delivered = False
                if sg_ver['sg_delivered'] == 'True':
                    tmp_delivered = True
                tmp_ver.set_delivered(tmp_delivered)
                tmp_ver.set_client_code(sg_ver['client_code'])
                tmp_playlists = []
                for tmp_pl_struct in sg_ver['playlists']:
                    tmp_playlists.append(Playlist.Playlist(tmp_pl_struct['name'], [], tmp_pl_struct['id']))
                tmp_ver.set_playlists(tmp_playlists)
                if sg_ver['sg_path_to_matte_frames']:
                    tmp_ver.set_path_to_matte_frames(sg_ver['sg_path_to_matte_frames'])
                if sg_ver['sg_matte_ready_'] == 'True':
                    tmp_ver.set_matte_ready(True)
                if sg_ver['sg_matte_delivered_'] == 'True':
                    tmp_ver.set_matte_delivered(True)
                ver_ret.append(tmp_ver)
            return ver_ret

    def fetch_versions_with_mattes(self):
        ver_ret = []
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['sg_matte_ready_', 'is', True],
            ['sg_matte_delivered_', 'is', False]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task', 'sg_delivered', 'client_code', 'playlists', 'sg_path_to_matte_frames', 'sg_matte_ready_', 'sg_matte_delivered_']
        sg_vers = self.g_sg.find("Version", filters, fields)
        if not sg_vers:
            return ver_ret
        else:
            for sg_ver in sg_vers:
                shot_obj = self.fetch_shot_from_id(sg_ver['entity']['id'])
                local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
                tmp_ver = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], shot_obj, local_artist, None)
                tmp_delivered = False
                if sg_ver['sg_delivered'] == 'True':
                    tmp_delivered = True
                tmp_ver.set_delivered(tmp_delivered)
                tmp_ver.set_client_code(sg_ver['client_code'])
                tmp_playlists = []
                for tmp_pl_struct in sg_ver['playlists']:
                    tmp_playlists.append(Playlist.Playlist(tmp_pl_struct['name'], [], tmp_pl_struct['id']))
                tmp_ver.set_playlists(tmp_playlists)
                if sg_ver['sg_path_to_matte_frames']:
                    tmp_ver.set_path_to_matte_frames(sg_ver['sg_path_to_matte_frames'])
                if sg_ver['sg_matte_ready_'] == 'True':
                    tmp_ver.set_matte_ready(True)
                if sg_ver['sg_matte_delivered_'] == 'True':
                    tmp_ver.set_matte_delivered(True)
                ver_ret.append(tmp_ver)
            return ver_ret

    def fetch_versions_for_shot(self, m_shot_obj):
        ver_ret = []
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['entity', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task', 'sg_delivered', 'client_code', 'playlists', 'sg_path_to_matte_frames', 'sg_matte_ready_', 'sg_matte_delivered_']
        sg_vers = self.g_sg.find("Version", filters, fields)
        if not sg_vers:
            return ver_ret
        else:
            for sg_ver in sg_vers:
                local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
                tmp_ver = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], m_shot_obj, local_artist, None)
                tmp_delivered = False
                if sg_ver['sg_delivered'] == 'True':
                    tmp_delivered = True
                tmp_ver.set_delivered(tmp_delivered)
                tmp_ver.set_client_code(sg_ver['client_code'])
                tmp_playlists = []
                for tmp_pl_struct in sg_ver['playlists']:
                    tmp_playlists.append(Playlist.Playlist(tmp_pl_struct['name'], [], tmp_pl_struct['id']))
                tmp_ver.set_playlists(tmp_playlists)
                if sg_ver['sg_path_to_matte_frames']:
                    tmp_ver.set_path_to_matte_frames(sg_ver['sg_path_to_matte_frames'])
                if sg_ver['sg_matte_ready_'] == 'True':
                    tmp_ver.set_matte_ready(True)
                if sg_ver['sg_matte_delivered_'] == 'True':
                    tmp_ver.set_matte_delivered(True)
                ver_ret.append(tmp_ver)
            return ver_ret

    def fetch_playlist(self, m_playlist_name):                
        playlist_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['code', 'is', m_playlist_name]
        ]
        fields = ['id', 'code', 'versions']
        sg_playlist = self.g_sg.find_one("Playlist", filters, fields)
        if not sg_playlist:
            return playlist_ret
        else:
            version_list = []
            for version in sg_playlist['versions']:
                version_list.append(self.fetch_version_from_id(version['id']))
                
            playlist_ret = Playlist.Playlist(sg_playlist['code'], version_list, sg_playlist['id'])
            return playlist_ret

    def fetch_notes_for_version(self, m_version_obj, b_populate_playlists=False):
        notes_ret = []
        fields = ['id', 'subject', 'addressings_to', 'user', 'content', 'sg_note_type', 'note_links']
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['note_links', 'is', {'type' : 'Version', 'id' : int(m_version_obj.g_dbid)}]
        ]
        sg_notes = self.g_sg.find("Note", filters, fields)
        for sg_note in sg_notes:
            t_id = sg_note['id']
            t_body = sg_note['content']
            t_from = self.fetch_artist_from_id(sg_note['user']['id'])
            t_to = self.fetch_artist_from_id(sg_note['addressings_to'][0]['id'])
            t_type = sg_note['sg_note_type']
            t_subject = sg_note['subject']
            t_links = []
            for link in sg_note['note_links']:
                if link['type'] == 'Shot':
                    t_links.append(self.fetch_shot_from_id(link['id']))
                elif link['type'] == 'Version':
                    t_links.append(self.fetch_version_from_id(link['id']))
                elif link['type'] == 'Playlist':
                    if b_populate_playlists:
                        t_links.append(self.fetch_playlist(link['name']))
                    else:
                        t_links.append(Playlist.Playlist(link['name'], [], link['id']))
            t_note_obj = Note.Note(t_subject, t_to, t_from, t_links, t_body, t_type, t_id)
            notes_ret.append(t_note_obj)
        return notes_ret

    def create_playlist(self, m_playlist_obj):
        version_list = []
        for ver in m_playlist_obj.g_playlist_versions:
            version_list.append({'type' : 'Version', 'id' : ver.g_dbid})
        
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_playlist_obj.g_playlist_name,
            'versions' : version_list
        }
        sg_playlist = None
        if m_playlist_obj.g_dbid == -1:
            sg_playlist = self.g_sg.create('Playlist', data)
        else:
            sg_playlist = self.g_sg.update('Playlist', m_playlist_obj.g_dbid, data)
        m_playlist_obj.g_dbid = sg_playlist['id']

    def delete_playlist(self, m_playlist_obj):
        self.g_sg.delete("Playlist", m_playlist_obj.g_dbid)

    def create_sequence(self, m_seq_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_seq_obj.g_seq_code,
            'sg_status_list' : 'ip'
        }
        sg_seq = self.g_sg.create('Sequence', data)
        m_seq_obj.g_dbid = sg_seq['id']

    def create_task(self, m_task_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'entity' : {'type' : 'Shot', 'id' : int(m_task_obj.g_shot.g_dbid)},
            'content' : m_task_obj.g_task_name,
            'sg_status_list' : 'wtg'
        }
        if m_task_obj.g_pipeline_step_id != -1:
            data['step'] = {'type' : 'Step', 'id' : int(m_task_obj.g_pipeline_step_id) }

        sg_task = self.g_sg.create('Task', data)
        m_task_obj.g_dbid = sg_task['id']
        
    def create_shot(self, m_shot_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_shot_obj.g_shot_code,
            'sg_status_list' : 'wtg',
            'sg_sequence' : {'type' : 'Sequence', 'id' : int(m_shot_obj.g_sequence.g_dbid)},
            'sg_head_in' : m_shot_obj.g_head_in,
            'sg_cut_in' : m_shot_obj.g_cut_in,
            'sg_cut_out' : m_shot_obj.g_cut_out,
            'sg_tail_out' : m_shot_obj.g_tail_out,
            'sg_cut_duration' : m_shot_obj.g_cut_duration
        }
        # fetch the task template
        filters = [
            ['code', 'is', self.g_shotgun_task_template]
        ]
        fields = ['id', 'code']
        sg_tt = self.g_sg.find_one("TaskTemplate", filters, fields)
        if sg_tt:
            data['task_template'] = {'type' : 'TaskTemplate', 'id' : int(sg_tt['id'])}
            m_shot_obj.g_task_template = sg_tt['code']
        sg_shot = self.g_sg.create('Shot', data)
        m_shot_obj.g_dbid = sg_shot['id']        

    def create_version(self, m_version_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_version_obj.g_version_code,
            'description' : m_version_obj.g_description,
            'sg_first_frame' : m_version_obj.g_start_frame,
            'sg_last_frame' : m_version_obj.g_end_frame,
            'frame_count' : m_version_obj.g_duration,
            'sg_path_to_frames' : m_version_obj.g_path_to_frames,
            'sg_path_to_movie' : m_version_obj.g_path_to_movie,
            'entity' : {'type' : 'Shot', 'id' : int(m_version_obj.g_shot.g_dbid)},
            'user' : {'type' : 'HumanUser', 'id' : int(m_version_obj.g_artist.g_dbid)},
            'sg_task' : {'type' : 'Task', 'id' : int(m_version_obj.g_task.g_dbid)},
            'sg_delivered' : str(m_version_obj.g_delivered)
        }
        if m_version_obj.g_client_code : 
            data['client_code'] = m_version_obj.g_client_code
        if m_version_obj.g_path_to_matte_frames : 
            data['sg_path_to_matte_frames'] = m_version_obj.g_path_to_matte_frames
        if m_version_obj.g_matte_ready : 
            data['sg_matte_ready_'] = True
        if m_version_obj.g_matte_delivered : 
            data['sg_matte_delivered_'] = True
        try:
            sg_version = self.g_sg.create('Version', data)
            m_version_obj.g_dbid = sg_version['id']
        except:
            exception = sys.exc_info()
            print "Caught exception %s!"%exception[1]
            print data
            print traceback.print_exception(exception[0], exception[1], exception[2])

    def create_plate(self, m_plate_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_plate_obj.g_plate_name,
            'sg_status_list' : 'ip',
            'sg_shot_code' : {'type' : 'Shot', 'id' : int(m_plate_obj.g_shot.g_dbid)},
            'sg_start_frame' : m_plate_obj.g_start_frame, 
            'sg_end_frame' : m_plate_obj.g_end_frame, 
            'sg_duration' : m_plate_obj.g_duration, 
            'sg_filesystem_path' : { 
                'url' : 'file://%s'%m_plate_obj.g_filesystem_path, 
                'local_storage': {
                    'type': 'LocalStorage', 
                    'id': 2, 
                    'name': 'primary'
                }, 
                'local_path' :  m_plate_obj.g_filesystem_path,
                'local_path_mac' : m_plate_obj.g_filesystem_path,
                'local_path_linux' : m_plate_obj.g_filesystem_path
            }, 
            'sg_start_timecode' : m_plate_obj.g_start_timecode, 
            'sg_clip_name' : m_plate_obj.g_clip_name, 
            'sg_scene' : m_plate_obj.g_scene, 
            'sg_take' : m_plate_obj.g_take, 
            'sg_end_timecode' : m_plate_obj.g_end_timecode
        }
        sg_plate = self.g_sg.create('CustomEntity01', data)
        m_plate_obj.g_dbid = sg_plate['id']

    def create_note(self, m_note_obj):
        links_ar = []
        for link in m_note_obj.g_links:
            if link.__class__.__name__ == "Version":
                links_ar.append({'type':'Version', 'id':int(link.g_dbid)})
            elif link.__class__.__name__ == "Shot":
                links_ar.append({'type':'Shot', 'id':int(link.g_dbid)})
            elif link.__class__.__name__ == "Playlist":
                links_ar.append({'type':'Playlist', 'id':int(link.g_dbid)})
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'subject' : m_note_obj.g_subject,
            'addressings_to' : [{'type' : 'HumanUser', 'id' : int(m_note_obj.g_to.g_dbid)}],
            'user' : {'type' : 'HumanUser', 'id' : int(m_note_obj.g_from.g_dbid)},
            'note_links' : links_ar,
            'content' : m_note_obj.g_body,
            'sg_note_type' : m_note_obj.g_type
        }
        sg_note = self.g_sg.create('Note', data)
        m_note_obj.g_dbid = sg_note['id']
            
    # uploads a thumbnail for a given database object type.
    # currently, valid values are 'Shot', 'Plate', and 'Version'
    def upload_thumbnail(self, m_entity_type, m_entity, m_thumb_path, altid = -1):
        try:
            if m_entity_type == 'Plate':
                self.g_sg.upload_thumbnail('CustomEntity01', m_entity.g_dbid, m_thumb_path)
            elif m_entity_type == 'Shot':
                self.g_sg.upload_thumbnail('Shot', m_entity.g_dbid, m_thumb_path)
            elif m_entity_type == 'Version':
                self.g_sg.upload_thumbnail('Version', m_entity.g_dbid, m_thumb_path)
            elif m_entity_type == 'PublishedFile':
                self.g_sg.upload_thumbnail('PublishedFile', altid, m_thumb_path)
            else:
                raise ValueError('ShotgunDBAccess.upload_thumbnail(): entity type %s not supported.'%m_entity_type)
        except:
            print "ShotgunDbAccess: upload_thumbnail(): Unexpected Error caught!"
            print sys.exc_info()[0]
            print sys.exc_info()[1]

    def publish_for_shot(self, m_shot_obj, m_publish_path, m_clean_notes):
        dbpublishret = None
        # set shotgun authentication
        auth_user = sgtk.get_authenticated_user()
        if auth_user == None:
            sa = sgtk.authentication.ShotgunAuthenticator()
            user = sa.create_script_user(api_script=DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_script_name'), api_key=DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_api_key'), host=DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_server_path'))
            sgtk.set_authenticated_user(user)
    
        # retrieve Shotgun Toolkit object
        tk = sgtk.sgtk_from_entity('Shot', int(m_shot_obj.g_dbid))
        # grab context for published version
        context = tk.context_from_entity('Shot', int(m_shot_obj.g_dbid))
        sg_publish_name = os.path.basename(m_publish_path).split('.')[0].split('_v')[0]
        sg_publish_ver = int(os.path.basename(m_publish_path).split('.')[0].split('_v')[1])

        if os.path.splitext(m_publish_path)[1] == '.dpx':
            dbpublishret = sgtk.util.register_publish(tk, context, m_publish_path, sg_publish_name, sg_publish_ver, comment = '\n'.join(m_clean_notes), published_file_type = 'DPX Image Sequence')
        elif os.path.splitext(m_publish_path)[1] == '.exr':
            dbpublishret = sgtk.util.register_publish(tk, context, m_publish_path, sg_publish_name, sg_publish_ver, comment = '\n'.join(m_clean_notes), published_file_type = 'EXR Image Sequence')
        elif os.path.splitext(m_publish_path)[1] == '.nk':
            dbpublishret = sgtk.util.register_publish(tk, context, m_publish_path, sg_publish_name, sg_publish_ver, comment = '\n'.join(m_clean_notes), published_file_type = 'Nuke Script')
        return dbpublishret
           
    
    