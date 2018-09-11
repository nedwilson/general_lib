#!/usr/bin/python

import os
import re
import glob
import xml.etree.ElementTree as ET
from db_access import Version
from timecode import TimeCode
from ccdata import CCData


#
#
# class is initialized with one object of type db_access.Version.Version()
# ValueError will be raised if this is the wrong type
# 
# after object is initialized, call load_from_filesystem() which will try to locate the XML
# file on disk. If found, all of the various deliverables will be populated.
    
class VersionDelivery():

    # todo: convert parameters to monolithic dictionary
    def __init__(self, dbversion):
        if not dbversion.__class__.__name__ == 'Version':
            raise TypeError("VersionDelivery class must be initialized with object of type db_access.Version.")
        self.version_data = {}
        self.version_data['dbversion'] = dbversion
        self.version_data['dbshot'] = dbversion.g_shot
        self.version_data['dbartist'] = dbversion.g_artist
        self.version_data['xmlfile'] = None
        self.version_data['shot'] = None
        self.version_data['avidqt'] = None
        self.version_data['b_avidqt'] = False
        self.version_data['vfxqt'] = None
        self.version_data['b_vfxqt'] = False
        self.version_data['exportqt'] = None
        self.version_data['b_exportqt'] = False
        self.version_data['hires_format'] = None
        self.version_data['lores_ext'] = None
        self.version_data['hires'] = None
        self.version_data['hires_ext'] = None
        self.version_data['b_hires'] = False
        self.version_data['matte'] = None
        self.version_data['matte_ext'] = None
        self.version_data['b_matte'] = False
        self.version_data['start_frame'] = 0
        self.version_data['end_frame'] = 0
        self.version_data['duration'] = 0
        self.version_data['start_tc'] = None
        self.version_data['end_tc'] = None
        self.version_data['artist'] = None
        self.version_data['notes'] = None
        self.version_data['package'] = None
        self.version_data['ccfile'] = None
        self.version_data['ccdata'] = None
        self.version_data['vendor_name'] = None
        self.version_data['vendor_code'] = None
        self.version_data['version_separator'] = '_v'
        self.version_data['version_number'] = 0
        self.version_data['package'] = None
        self.version_data['batchid'] = None
        self.version_data['client_version'] = None
        self.version_data['element_type'] = 'comp'
        self.version_data['subdate'] = None
        self.version_data['client_filename'] = None
        self.version_data['subreason'] = None
        self.version_data['client_filetype'] = None
    
    # sets the name of the delivery package
    def set_package(self, package):
        self.version_data['package'] = package

    def set_batch_id(self, batch_id):
        self.version_data['batchid'] = batch_id

    def set_vendor_code(self, vendor_code):
        self.version_data['vendor_code'] = vendor_code
        
    def set_vendor_name(self, vendor_name):
        self.version_data['vendor_name'] = vendor_name

    def set_version_separator(self, version_separator):
        self.version_data['version_separator'] = version_separator
        
    def set_client_version(self, client_version):
        self.version_data['client_version'] = client_version
    
    def set_element_type(self, element_type):
        self.version_data['element_type'] = element_type

    def set_subdate(self, subdate):
        self.version_data['subdate'] = subdate

    def set_client_filename(self, client_filename):
        self.version_data['client_filename'] = client_filename

    def set_subreason(self, subreason):
        self.version_data['subreason'] = subreason

    def set_client_filetype(self, client_filetype):
        self.version_data['client_filetype'] = client_filetype
                        
    # loads the XML file from the shot delivery folder/version name subfolder
    def load_from_filesystem(self):
        hires_path = self.version_data['dbversion'].g_path_to_frames
        delivery_root = os.path.dirname(os.path.dirname(hires_path))
        if os.path.basename(os.path.dirname(delivery_root)) != 'delivery':
            raise Exception("Hires frames must be located in the delivery subfolder of the shot. Alternative paths are not supported at this time. This version\'s hires frames are located here: %s"%os.path.dirname(delivery_root))
        tmp_xmlfile = os.path.join(delivery_root, 'support_files', '%s.xml'%self.version_data['dbversion'].g_version_code)
        if not os.path.exists(tmp_xmlfile):
            raise Exception("Unable to locate XML file at %s"%tmp_xmlfile)
        self.version_data['xmlfile'] = tmp_xmlfile
        xmlfile_handle = open(tmp_xmlfile)
        xml_data = xmlfile_handle.read()
        xmlfile_handle.close()
        root = ET.fromstring(xml_data)
        dsub_dict = {}
        for element in root.getchildren():
            dsub_dict[element.tag] = element.text

        self.version_data['shot'] = dsub_dict['Shot']
        try:
            self.version_data['avidqt'] = os.path.join(delivery_root, 'mov', dsub_dict['AvidQTFileName'])
            self.version_data['lores_ext'] = os.path.splitext(dsub_dict['AvidQTFileName'])[1].lstrip('.')
            self.version_data['b_avidqt'] = True
        except KeyError:
            self.version_data['lores_ext'] = 'mov'
            pass
        try:
            self.version_data['vfxqt'] = os.path.join(delivery_root, 'mov', dsub_dict['VFXQTFileName'])
            self.version_data['b_vfxqt'] = True
        except KeyError:
            pass
        try:
            self.version_data['exportqt'] = os.path.join(delivery_root, 'mov', dsub_dict['ExportQTFileName'])
            self.version_data['b_exportqt'] = True
        except KeyError:
            pass
        self.version_data['b_hires'] = False
        try:
            self.version_data['hires_format'] = dsub_dict['HiResFormat']
            self.version_data['hires'] = hires_path.replace('%04d', '*')
            self.version_data['hires_ext'] = os.path.splitext(hires_path)[1].replace('.', '')
            self.version_data['b_hires'] = True
        except KeyError:
            self.version_data['hires_format'] = '1920x1080'
            self.version_data['hires'] = 'NO_HIRES_FRAMES'
            self.version_data['hires_ext'] = 'NO_HIRES'
            self.version_data['b_hires'] = False

        try:
            self.version_data['matte'] = os.path.join(delivery_root, 'matte', dsub_dict['MatteFileName'])
            self.version_data['matte_ext'] = os.path.splitext(dsub_dict['MatteFileName'])[1].replace('.', '')
            self.version_data['b_matte'] = True
        except KeyError:
            pass
        self.version_data['start_frame'] = int(dsub_dict['StartFrame'])
        self.version_data['end_frame'] = int(dsub_dict['EndFrame'])
        self.version_data['duration'] = self.version_data['end_frame'] - self.version_data['start_frame'] + 1
        self.version_data['start_tc'] = TimeCode(dsub_dict['StartTimeCode'])
        self.version_data['end_tc'] = TimeCode(dsub_dict['EndTimeCode'])
        self.version_data['artist'] = dsub_dict['Artist']
        self.version_data['notes'] = dsub_dict['SubmissionNotes']
        
        version_re_text = '%s([0-9]+)'%self.version_data['version_separator']
        try:
            self.version_data['version_number'] = int(re.search(version_re_text, self.version_data['dbversion'].g_version_code).group(1))
        except:
            pass
        # try and find a .CC file
        ccfiles = glob.glob(os.path.join(delivery_root, 'support_files', '*.c*'))
        if len(ccfiles) > 0:
            self.version_data['ccfile'] = ccfiles[0]
            self.version_data['ccdata'] = CCData(ccfiles[0])
        else:
            __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
            print os.path.join(__location__, 'default.cc')
            self.version_data['ccfile'] = os.path.join(__location__, 'default.cc')
            self.version_data['ccdata'] = CCData(os.path.join(__location__, 'default.cc'))
            
    def __repr__(self):
        return str(self.version_data)
            
        