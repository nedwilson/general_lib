#!/usr/bin/python

import pprint
import os
import OpenEXR
import Imath
import sys
from timecode import TimeCode
import sgtk
import db_access as DB

sgdb = DB.DBAccessGlobals.get_db_access()
mgr = sgtk.bootstrap.ToolkitManager()

# seq = sgdb.fetch_sequence('HC019')
# print seq

shot = sgdb.fetch_shot('SD078_015')
print shot

# print "Sequence Create"
# new_seq_path = DB.DBAccess.get_path_for_sequence('TS000')
# new_seq_obj = DB.Sequence('TS000', new_seq_path, -1)
# sgdb.create_sequence(new_seq_obj)
# print new_seq_obj

# print "Shot Create"
# new_shot_path = DB.DBAccess.get_path_for_shot('TS000_000')
# new_shot_obj = DB.Shot('TS000_000', new_shot_path, -1, seq, 'SWDM Task Template', 1001, 1009, 1088, 1096, 80)
# sgdb.create_shot(new_shot_obj)
# print new_shot_obj

plate = sgdb.fetch_plate('SD078_015_BS_LEFT', shot)
print plate

# print "Plate Create"
# 
# plates = ['/Volumes/raid_vol01/shows/spinel/CB061/CB061_300/pix/plates/CB061_300_BG/CB061_300_BG']
# g_write_frame_format = '%04d'
# mainplate_ext = 'exr'
# mainplate_first = 1001
# mainplate_last = 1056
# 
# plate_name = os.path.basename(plates[0])
# start_frame = mainplate_first
# end_frame = mainplate_last
# duration = (end_frame - start_frame + 1)
# thumb_frame = start_frame + (duration/2)
# plate_path = "%s.%s.%s"%(plates[0], g_write_frame_format, mainplate_ext)
# start_file_path = "%s.%s.%s"%(plates[0], mainplate_first, mainplate_ext)
# end_file_path = "%s.%s.%s"%(plates[0], mainplate_last, mainplate_ext)
# 
# start_file = OpenEXR.InputFile(start_file_path)
# 
# try:
#     start_tc_obj = start_file.header()['timeCode']
#     start_timecode = int((TimeCode("%02d:%02d:%02d:%02d"%(start_tc_obj.hours, start_tc_obj.minutes, start_tc_obj.seconds, start_tc_obj.frame)).frame_number() * 1000) / 24)
#     clip_name = start_file.header()['reelName']
#     scene = start_file.header()['Scene']
#     take = start_file.header()['Take']
# except KeyError:
#     e = sys.exc_info()
#     print e[0]
#     print e[1]
#     print e[2]
# 
# end_file = OpenEXR.InputFile(end_file_path)
# 
# try:
#     end_tc_obj = end_file.header()['timeCode']
#     end_timecode = int((TimeCode("%02d:%02d:%02d:%02d"%(end_tc_obj.hours, end_tc_obj.minutes, end_tc_obj.seconds, end_tc_obj.frame)).frame_number() * 1000) / 24)
# except KeyError:
#     e = sys.exc_info()
#     print e[0]
#     print e[1]
#     print e[2]
# 
# new_plate_obj = DB.Plate(plate_name, start_frame, end_frame, duration, plate_path, start_timecode, clip_name, scene, take, end_timecode, shot, -1)
# sgdb.create_plate(new_plate_obj)
# print new_plate_obj

tasks = sgdb.fetch_tasks_for_shot(shot)
task = None
for task_tmp in tasks:
    if "final" in task_tmp.g_task_name.lower():
        task = task_tmp
print task
    
artist = sgdb.fetch_artist("Ned Wilson")
print artist

# try to get a context from the Shotgun Toolkit
dbcontext = mgr.context_from_entity('CustomEntity01', plate.g_dbid)
print dbcontext

# print "Version Create"
# new_version_obj = DB.Version('HC019_300_comp_v002', 
#                              -1, 
#                              'Removed white halo around A-pillar.', 
#                              1001, 
#                              1065, 
#                              65, 
#                              '/Volumes/raid_vol01/shows/spinel/HC019/HC019_300/pix/comp/HC019_300_comp_v002/HC019_300_comp_v002.%04d.exr', 
#                              '/Volumes/raid_vol01/shows/spinel/HC019/HC019_300/pix/comp/HC019_300_comp_v002/HC019_300_comp_v002.mov',
#                              shot,
#                              artist,
#                              task)
# sgdb.create_version(new_version_obj)
# print new_version_obj

# version = sgdb.fetch_version('HC019_300_comp_v002', shot)
# print version




