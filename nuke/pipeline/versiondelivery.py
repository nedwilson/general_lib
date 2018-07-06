#!/usr/bin/python

import os
import xml.etree.ElementTree as ET
from db_access import Version
from timecode import TimeCode

#
#
# class is initialized with one object of type db_access.Version.Version()
# ValueError will be raised if this is the wrong type
# 
# after object is initialized, call load_from_filesystem() which will try to locate the XML
# file on disk. If found, all of the various deliverables will be populated.
    
class VersionDelivery():

    def __init__(self, dbversion):
        if not dbversion.__class__.__name__ == 'Version':
            raise TypeError("VersionDelivery class must be initialized with object of type db_access.Version.")
        self.dbversion = dbversion
        self.dbshot = dbversion.g_shot
        self.dbartist = dbversion.g_artist
        self.xmlfile = None
        self.shot = None
        self.avidqt = None
        self.b_avidqt = False
        self.vfxqt = None
        self.b_vfxqt = False
        self.exportqt = None
        self.b_exportqt = False
        self.hires_format = None
        self.hires = None
        self.hires_ext = None
        self.b_hires = False
        self.matte = None
        self.b_matte = False
        self.start_frame = 0
        self.end_frame = 0
        self.start_tc = None
        self.end_tc = None
        self.artist = None
        self.notes = None
        
    def load_from_filesystem(self):
        hires_path = self.dbversion.g_path_to_frames
        delivery_root = os.path.dirname(os.path.dirname(hires_path))
        if os.path.basename(os.path.dirname(delivery_root)) != 'delivery':
            raise Exception("Hires frames must be located in the delivery subfolder of the shot. Alternative paths are not supported at this time.")
        tmp_xmlfile = os.path.join(delivery_root, 'support_files', '%s.xml'%self.dbversion.g_version_code)
        if not os.path.exists(tmp_xmlfile):
            raise Exception("Unable to locate XML file at %s"%tmp_xmlfile)
        self.xmlfile = tmp_xmlfile
        xmlfile_handle = open(tmp_xmlfile)
        xml_data = xmlfile_handle.read()
        xmlfile_handle.close()
        root = ET.fromstring(xml_data)
        dsub_dict = {}
        for element in root.getchildren():
            dsub_dict[element.tag] = element.text

        self.shot = dsub_dict['Shot']
        try:
            self.avidqt = os.path.join(delivery_root, 'mov', dsub_dict['AvidQTFileName'])
            self.b_avidqt = True
        except KeyError:
            pass
        try:
            self.vfxqt = os.path.join(delivery_root, 'mov', dsub_dict['VFXQTFileName'])
            self.b_vfxqt = True
        except KeyError:
            pass
        try:
            self.exportqt = os.path.join(delivery_root, 'mov', dsub_dict['ExportQTFileName'])
            self.b_exportqt = True
        except KeyError:
            pass
        self.hires_format = dsub_dict['HiResFormat']
        self.hires = hires_path.replace('%04d', '*')
        self.hires_ext = os.path.splitext(hires_path)[1].replace('.', '')
        self.b_hires = True
        try:
            self.matte = os.path.join(delivery_root, 'mov', dsub_dict['MatteFileName'])
            self.b_matte = True
        except KeyError:
            pass
        self.start_frame = int(dsub_dict['StartFrame'])
        self.end_frame = int(dsub_dict['EndFrame'])
        self.start_tc = TimeCode(dsub_dict['StartTimeCode'])
        self.end_tc = TimeCode(dsub_dict['EndTimeCode'])
        self.artist = dsub_dict['Artist']
        self.notes = dsub_dict['SubmissionNotes']
            
            
            
        