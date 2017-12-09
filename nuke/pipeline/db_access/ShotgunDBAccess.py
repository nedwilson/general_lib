#!/usr/bin/python

import sys
import os
import re
import ConfigParser
import shotgun_api3
import pprint


import Sequence
import Shot
import Plate

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
