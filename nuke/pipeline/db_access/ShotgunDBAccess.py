#!/usr/bin/python

import sys
import os
import re
import ConfigParser
import shotgun_api3
import pprint
import threading


import Sequence
import Shot
import Plate
import Version
import Task
import Artist
import Playlist

import DBAccessGlobals
import DBAccess

from timecode import TimeCode


# Shotgun-specific data source implementation

class ShotgunDBAccess(DBAccess.DBAccess):

    def __init__(self):
        try:
            self.g_shotgun_api_key = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_api_key')
            self.g_shotgun_script_name = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_script_name')
            self.g_shotgun_server_path = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_server_path')
            self.g_shotgun_project_id = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_project_id')
            self.g_shotgun_task_template = DBAccessGlobals.DBAccessGlobals.g_config.get('database', 'shotgun_task_template')
            self.g_sg = shotgun_api3.Shotgun(self.g_shotgun_server_path, self.g_shotgun_script_name, self.g_shotgun_api_key)
        except ConfigParser.NoSectionError:
            e = sys.exc_info()
            print e[1]
        except ConfigParser.NoOptionError:
            e = sys.exc_info()
            print e[1]
        except:        
            e = sys.exc_info()
            print e[1]
            
    def fetch_shot(self, m_shot_code):
        shot_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['code', 'is', m_shot_code]
        ]
        fields = ['id', 'code', 'sg_sequence', 'task_template', 'sg_head_in', 'sg_cut_in', 'sg_cut_out', 'sg_tail_out', 'sg_cut_duration']
        sg_shot = self.g_sg.find_one("Shot", filters, fields)
        if not sg_shot:
            return shot_ret
        else:
            print "%s - inside fetch_shot(\'%s\')"%(threading.current_thread().getName(), m_shot_code)
            local_seq = None
            try:
                local_seq = Sequence.Sequence(sg_shot['sg_sequence']['name'], DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(sg_shot['sg_sequence']['name']), sg_shot['sg_sequence']['id'])
            except KeyError:
                print "ERROR: %s - Sequence is NULL! %s"%(threading.current_thread().getName(), sg_shot)
                local_seq = Sequence.Sequence(m_shot_code[0:5], DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(m_shot_code[0:5]), -1)
            local_shot_path = DBAccessGlobals.DBAccessGlobals.get_path_for_shot(sg_shot['code'])
            shot_ret = Shot.Shot(sg_shot['code'],
                            local_shot_path,
                            sg_shot['id'],
                            local_seq,
                            sg_shot['task_template']['name'],
                            sg_shot['sg_head_in'],
                            sg_shot['sg_cut_in'],
                            sg_shot['sg_cut_out'],
                            sg_shot['sg_tail_out'],
                            sg_shot['sg_cut_duration'])
            return shot_ret

    def fetch_shot_from_id(self, m_shot_id):
        shot_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['id', 'is', m_shot_id]
        ]
        fields = ['id', 'code', 'sg_sequence', 'task_template', 'sg_head_in', 'sg_cut_in', 'sg_cut_out', 'sg_tail_out', 'sg_cut_duration']
        sg_shot = self.g_sg.find_one("Shot", filters, fields)
        if not sg_shot:
            return shot_ret
        else:
            local_seq = Sequence.Sequence(sg_shot['sg_sequence']['name'], DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(sg_shot['sg_sequence']['name']), sg_shot['sg_sequence']['id'])
            local_shot_path = DBAccessGlobals.DBAccessGlobals.get_path_for_shot(sg_shot['code'])
            shot_ret = Shot.Shot(sg_shot['code'],
                            local_shot_path,
                            sg_shot['id'],
                            local_seq,
                            sg_shot['task_template']['name'],
                            sg_shot['sg_head_in'],
                            sg_shot['sg_cut_in'],
                            sg_shot['sg_cut_out'],
                            sg_shot['sg_tail_out'],
                            sg_shot['sg_cut_duration'])
            return shot_ret

    def fetch_plate(self, m_plate_name, m_shot_obj):
        plate_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['sg_shot_code', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}],
            ['code', 'is', m_plate_name]
        ]
        
        fields = ['code', 'sg_start_frame', 'sg_end_frame', 'sg_duration', 'sg_filesystem_path', 'sg_start_timecode', 'sg_clip_name', 'sg_scene', 'sg_take', 'sg_end_timecode', 'sg_shot_code', 'id']
        sg_plate = self.g_sg.find_one("CustomEntity01", filters, fields)
        if not sg_plate:
            return plate_ret
        else:
            useful_path = sg_plate['sg_filesystem_path']['url'].replace('file://', '')
            plate_ret = Plate.Plate(sg_plate['code'],
                              sg_plate['sg_start_frame'],
                              sg_plate['sg_end_frame'],
                              sg_plate['sg_duration'],
                              useful_path,
                              TimeCode(round(float(sg_plate['sg_start_timecode'])/41.6666666666666666)).time_code(),
                              sg_plate['sg_clip_name'],
                              sg_plate['sg_scene'],
                              sg_plate['sg_take'],
                              TimeCode(round(float(sg_plate['sg_end_timecode'])/41.6666666666666666)).time_code(),
                              m_shot_obj,
                              sg_plate['id'])
            return plate_ret

    def fetch_sequence(self, m_seq_code):                
        seq_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['code', 'is', m_seq_code]
        ]
        fields = ['id', 'code']
        sg_seq = self.g_sg.find_one("Sequence", filters, fields)
        if not sg_seq:
            return seq_ret
        else:
            local_seq_path = DBAccessGlobals.DBAccessGlobals.get_path_for_sequence(sg_seq['code'])
            seq_ret = Sequence.Sequence(sg_seq['code'], local_seq_path, sg_seq['id'])
            return seq_ret

    def fetch_artist(self, m_full_name):                
        artist_ret = None
        filters = [
            ['name', 'is', m_full_name]
        ]
        fields = ['firstname', 'lastname', 'name', 'login', 'id']
        sg_artist = self.g_sg.find_one("HumanUser", filters, fields)
        if not sg_artist:
            return artist_ret
        else:
            artist_ret = Artist.Artist(sg_artist['firstname'], sg_artist['lastname'], sg_artist['login'], sg_artist['id'])
            return artist_ret

    def fetch_artist_from_id(self, m_artist_id):                
        artist_ret = None
        filters = [
            ['id', 'is', m_artist_id]
        ]
        fields = ['firstname', 'lastname', 'name', 'login', 'id']
        sg_artist = self.g_sg.find_one("HumanUser", filters, fields)
        if not sg_artist:
            return artist_ret
        else:
            print threading.current_thread().getName()
            print sg_artist
            artist_ret = Artist.Artist(sg_artist['firstname'], sg_artist['lastname'], sg_artist['login'], sg_artist['id'])
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
                    artist = self.fetch_artist_from_id(sg_task['task_assignees'][0]['id'])
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
            print threading.current_thread().getName()
            print sg_task
            artist = None
            try:
                artist = self.fetch_artist_from_id(sg_task['task_assignees'][0]['id'])
            except KeyError:
                print "ERROR: Task assignees for task %s is NULL!"%sg_task
                artist = Artist.Artist('Alan', 'Smithee', 'asmithee', -1)
            task_ret = Task.Task(sg_task['content'], artist, sg_task['sg_status_list'], m_shot_obj, sg_task['id'])
            return task_ret

    def update_task_status(self, m_task_obj):
        data = {
            'sg_status_list' : m_task_obj.g_status,
        }
        self.g_sg.update('Task', m_task_obj.g_dbid, data)
                        
    def fetch_version(self, m_version_name, m_shot_obj):
        ver_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['entity', 'is', {'type' : 'Shot', 'id' : int(m_shot_obj.g_dbid)}],
            ['code', 'is', m_version_name]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task']
        sg_ver = self.g_sg.find_one("Version", filters, fields)
        if not sg_ver:
            return ver_ret
        else:
            local_task = self.fetch_task_from_id(int(sg_ver['sg_task']['id']), m_shot_obj)
            local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
            ver_ret = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], m_shot_obj, local_artist, local_task)
            return ver_ret

    def fetch_version_from_id(self, m_version_id):
        ver_ret = None
        filters = [
            ['project', 'is', {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)}],
            ['id', 'is', m_version_id]
        ]
        fields = ['code', 'id', 'description', 'sg_first_frame', 'sg_last_frame', 'frame_count', 'sg_path_to_frames', 'sg_path_to_movie', 'entity', 'user', 'sg_task']
        sg_ver = self.g_sg.find_one("Version", filters, fields)
        if not sg_ver:
            return ver_ret
        else:
            local_shot = self.fetch_shot_from_id(sg_ver['entity']['id'])
            local_task = self.fetch_task_from_id(int(sg_ver['sg_task']['id']), local_shot)
            local_artist = self.fetch_artist_from_id(int(sg_ver['user']['id']))
            ver_ret = Version.Version(sg_ver['code'], sg_ver['id'], sg_ver['description'], sg_ver['sg_first_frame'], sg_ver['sg_last_frame'], sg_ver['frame_count'], sg_ver['sg_path_to_frames'], sg_ver['sg_path_to_movie'], local_shot, local_artist, local_task)
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
        
    def create_sequence(self, m_seq_obj):
        data = {
            'project' : {'type' : 'Project', 'id' : int(self.g_shotgun_project_id)},
            'code' : m_seq_obj.g_seq_code,
            'sg_status_list' : 'ip'
        }
        sg_seq = self.g_sg.create('Sequence', data)
        m_seq_obj.g_dbid = sg_seq['id']
        
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
            'sg_task' : {'type' : 'Task', 'id' : int(m_version_obj.g_task.g_dbid)}
        }
        sg_version = self.g_sg.create('Version', data)
        m_version_obj.g_dbid = sg_version['id']        
        
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

    # uploads a thumbnail for a given database object type.
    # currently, valid values are 'Shot', 'Plate', and 'Version'
    def upload_thumbnail(self, m_entity_type, m_entity, m_thumb_path, altid = -1):
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
    
    
    