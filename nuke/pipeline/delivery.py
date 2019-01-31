#!/usr/local/bin/python

import sys
import ConfigParser
import os
import operator
import datetime
import glob
import re
import time
import shutil
import subprocess
import copy
import csv
import xlsxwriter
import tempfile
import traceback

# gmail/oauth

import httplib2
import oauth2client
import base64
import mimetypes

from oauth2client import client, tools
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase

# PyQt5

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# custom

import db_access as DB

from versiondelivery import VersionDelivery

g_version_status = 'rev'
g_version_status_qt = 'rev'
g_version_status_2k = 'p2k'
g_version_list = []
g_playlists = []
g_vdlist = []
g_ih_show_code = None
g_ih_show_root = None
g_ih_show_cfg_path = None
g_delivery_folder = None
g_config = None
g_cancel = False
ihdb = None
g_project_code = None
g_vendor_code = None
g_vendor_name = None
g_package_dir = None
g_batch_id = None
g_fileop = 'copy'
g_delivery_res = None
g_delivery_package = None
g_sub_file_path = None
g_ale_file = None
g_matte = False
g_combined = False
g_playlistonly = False
g_deliveryonly = False
g_playlist_age_days = 30
g_delivery_package_basename = None
g_subform_file_format = 'xlsx'

g_distro_list_to = None
g_distro_list_cc = None
g_mail_from = None
g_mail_from_address = None
g_write_ale = False
g_subform_lpf = False
g_show_code = ""
g_shared_root = ""
g_credentials_dir = ""
g_client_secret = ""
g_gmail_creds = ""
g_gmail_scopes = ""
g_application_name = ""
g_shot_count = 0
g_email_text = ""
g_rsync_enabled = False
g_rsync_filetypes = []
g_rsync_dest = ""
g_internal_approval_status = 'iapr'

def globals_from_config():
    global ihdb, g_ih_show_cfg_path, g_ih_show_root, g_ih_show_code, g_config, g_version_status, g_version_status_2k, g_version_status_qt, g_project_code, g_vendor_code, g_vendor_name, g_delivery_folder, g_fileop, g_delivery_res
    global g_distro_list_to, g_distro_list_cc, g_mail_from, g_write_ale, g_shared_root, g_credentials_dir, g_client_secret, g_gmail_creds, g_application_name, g_email_text, g_rsync_enabled, g_rsync_filetypes, g_rsync_dest, g_subform_lpf
    global g_playlist_age_days, g_internal_approval_status, g_subform_file_format
    try:
        g_ih_show_code = os.environ['IH_SHOW_CODE']
        g_ih_show_root = os.environ['IH_SHOW_ROOT']
        g_ih_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
        g_config = ConfigParser.ConfigParser()
        g_config.read(g_ih_show_cfg_path)
        g_version_status = g_config.get('delivery', 'version_status_qt')
        g_version_status_qt = g_config.get('delivery', 'version_status_qt')
        g_version_status_2k = g_config.get('delivery', 'version_status_2k')
        g_project_code = g_config.get(g_ih_show_code, 'project_code')
        g_vendor_code = g_config.get('delivery', 'vendor_code')
        g_vendor_name = g_config.get('delivery', 'vendor_name')
        g_delivery_folder = g_config.get('delivery', 'package_folder_%s'%sys.platform)
        g_fileop = g_config.get(g_ih_show_code, 'show_file_operation')
        g_delivery_res = g_config.get(g_ih_show_code, 'delivery_resolution')
        if g_config.get('delivery', 'subform_lineperfile') == 'yes':
            g_subform_lpf = True
        if g_config.get(g_ih_show_code, 'write_ale') == 'yes':
            g_write_ale = True
        ihdb = DB.DBAccessGlobals.get_db_access()
        print "INFO: globals initiliazed from config %s."%g_ih_show_cfg_path
    except KeyError:
        e = sys.exc_info()
        print e[1]
        print "This is most likely because this system has not been set up to run inside the In-House environment."
    except ConfigParser.NoSectionError:
        e = sys.exc_info()
        print e[1]
    except ConfigParser.NoOptionError:
        e = sys.exc_info()
        print e[1]
    except:        
        e = sys.exc_info()
        print e[1]
    # for playlist_age_days and internal_approval_status, it won't matter if it's not in the config file, just default to hard-coded values
    try:
        g_playlist_age_days = int(g_config.get('delivery', 'playlist_age_days'))
        g_internal_approval_status = g_config.get('delivery', 'internal_approval_status')
        g_subform_file_format = g_config.get('delivery', 'subform_file_format')
    except:
        pass


def handle_sync_and_send_email(m_source_folder, file_list):
    global g_config
    fh_tmpcfg, s_tmpcfg = tempfile.mkstemp(suffix='.cfg')
    os.write(fh_tmpcfg, '[delivery]\n')
    os.write(fh_tmpcfg, 'source_folder=%s\n'%m_source_folder)
    os.write(fh_tmpcfg, 'file_list=%s\n'%','.join(file_list))
    os.close(fh_tmpcfg)
    send_sync_bin = g_config.get('delivery', 'sync_email_cmd_%s'%sys.platform)
    sync_cmd = [send_sync_bin, s_tmpcfg]
    print "INFO: Executing command: %s"%" ".join(sync_cmd)
    subprocess.Popen(" ".join(sync_cmd), shell=True)

class ALEWriter():

    ale_fh = None
    header_list = None
    tape_name = 'INHOUSE_AVID'
    fps = '23.976'
    
    def __init__(self, input_filehandle):
        global g_config, g_ih_show_code
        self.ale_fh = input_filehandle
        self.tape_name = g_config.get(g_ih_show_code, 'ale_tapename')
        self.fps = g_config.get(g_ih_show_code, 'write_fps')

    # takes an array containing the names of the column headings.
    # example: column_header_list = ['Name', 'Tracks', 'Start', 'End', 'Tape', 'ASC_SOP', 'ASC_SAT', 'frame_range']
    # write_header(column_header_list)
    def write_header(self, column_headers):
        self.header_list = column_headers
        header_string = '\t'.join(self.header_list)
        ale_header = """Heading
FIELD_DELIM	TABS
VIDEO_FORMAT	1080
TAPE	%s
FPS	%s

Column
%s

Data
"""%(self.tape_name, self.fps, header_string)
        self.ale_fh.write(ale_header)
        return

    # takes an array of arrays. the master array contains a list of arrays, which represent individual rows in
    # the table. the individual rows contain values that match the headers provided to the write_header method.
    
    def set_tape_name(self, m_tape_name):
        self.tape_name = m_tape_name
        
    def write_data(self, row_data_list):
        for row in row_data_list:
            row_match_list = []
            for col_hdr in self.header_list:
                row_match_list.append(row[col_hdr])
            self.ale_fh.write('\t'.join(row_match_list))
            self.ale_fh.write('\n')
        return

def get_delivery_directory():
    global g_version_status, g_version_status_qt, g_version_status_2k, g_ih_show_code, g_project_code, g_vendor_code, \
        g_vendor_name, g_package_dir, g_batch_id, g_delivery_folder, g_delivery_package, g_combined, g_delivery_package_basename
    dt_hires = g_config.get('delivery', 'hires_delivery_type')
    dt_lores = g_config.get('delivery', 'lores_delivery_type')
    dt_combined = g_config.get('delivery', 'combined_delivery_type')
    delivery_type = dt_lores
    if g_version_status == g_version_status_2k:
        delivery_type = dt_hires
        
    if g_combined:
        delivery_type = dt_combined
        
    b_use_global_serial = False
    if g_config.get('delivery', 'use_global_serial') in ['Yes', 'yes', 'YES', 'Y', 'y', 'True', 'TRUE', 'true']:
        b_use_global_serial = True

    b_use_alphabetical_serial = False
    try:
        if g_config.get('delivery', 'use_alphabetical_serial') in ['Yes', 'yes', 'YES', 'Y', 'y', 'True', 'TRUE', 'true']:
            b_use_alphabetical_serial = True
    # most likely use_alphabetical_serial isn't defined in this show's config file
    except:
        pass

    if not b_use_alphabetical_serial:
        delivery_serial = int(g_config.get('delivery', 'serial_start'))
    else:
        delivery_serial = g_config.get('delivery', 'serial_start')
    date_format = g_config.get('delivery', 'date_format')
    today = datetime.date.today().strftime(date_format)
    
    matching_folders = sorted(glob.glob(os.path.join(g_delivery_folder, "*")))
    folder_re_text = g_config.get('delivery', 'package_directory_regexp')
    folder_re = re.compile(folder_re_text)
    
    max_serial = delivery_serial
    
    if len(matching_folders) > 0:
        for suspect_folder in matching_folders:
            folder_match = folder_re.search(suspect_folder)
            if folder_match:
                folder_match_dict = folder_match.groupdict()
                if b_use_global_serial:
                    if b_use_alphabetical_serial:
                        if ord(folder_match_dict['serial']) > ord(max_serial):
                            max_serial = folder_match_dict['serial']
                    else:
                        if int(folder_match_dict['serial']) > max_serial:
                            max_serial = int(folder_match_dict['serial'])
                else:
                    if folder_match_dict['date'] == today:
                        if b_use_alphabetical_serial:
                            if ord(folder_match_dict['serial']) > ord(max_serial):
                                max_serial = folder_match_dict['serial']
                        else:
                            if int(folder_match_dict['serial']) > max_serial:
                                max_serial = int(folder_match_dict['serial'])
    new_serial = ''
    if b_use_alphabetical_serial:
        new_serial = chr(ord(max_serial) + 1)
    else:
        new_serial = str(max_serial + 1)
    d_folder_format = {}
    if not g_deliveryonly:
        d_folder_format = {'vendor_code': g_vendor_code, 'project_code': g_project_code, 'date': today,
                           'serial': new_serial, 'delivery_type': delivery_type}
        g_package_dir = g_config.get('delivery', 'package_directory').format(**d_folder_format)
    else:
        folder_match = folder_re.search(g_package_dir)
        folder_match_dict = {}
        if folder_match:
            folder_match_dict = folder_match.groupdict()
        else:
            raise Exception('Error: Something is very wrong. Boolean g_deliveryonly is set to True, yet hero playlist name %s does not match package regex.'%g_package_dir)
        d_folder_format = {'vendor_code': g_vendor_code, 'project_code': g_project_code, 'date': folder_match_dict['date'],
                           'serial': folder_match_dict['serial'], 'delivery_type': delivery_type}

    g_batch_id = g_config.get('delivery', 'batch_id').format(**d_folder_format)
    g_delivery_package = os.path.join(g_delivery_folder, g_package_dir)

def vd_list_from_versions():
    global g_version_list, g_vdlist
    global g_config, g_ih_show_code, g_vendor_code, g_vendor_name, g_batch_id, g_package_dir, g_version_status, g_version_status_2k, g_version_status_qt, g_matte
    version_separator = g_config.get(g_ih_show_code, 'version_separator')
    ftu = g_config.get('delivery', 'fields_to_uppercase').split(',')
    element_type_re = re.compile(g_config.get('delivery', 'element_type_regexp'))
    client_version_fmt = g_config.get('delivery', 'client_version_format')
    subform_date_format = g_config.get('delivery', 'subform_date_format')
    vfmt_str = g_config.get(g_ih_show_code, 'version_format')
    
    client_filename_format = g_config.get('delivery', 'client_filename')
    client_matte_filename_format = g_config.get('delivery', 'client_matte_filename')
    for dbversion in g_version_list:
        print "INFO: Attempting to build a delivery for version %s."%dbversion.g_version_code
        vd_tmp = VersionDelivery(dbversion)
        vd_tmp.set_version_separator(version_separator)
        vd_tmp.set_vendor_code(g_vendor_code)
        vd_tmp.set_vendor_name(g_vendor_name)
        vd_tmp.set_package(g_package_dir)
        vd_tmp.set_batch_id(g_batch_id)
        et_match = element_type_re.search(vd_tmp.version_data['dbversion'].g_version_code)
        if et_match:
            vd_tmp.set_element_type(et_match.groupdict()['element_type'])
        vd_tmp.load_from_filesystem()
        # print vd_tmp.version_data
        for vd_tmp_key in vd_tmp.version_data.keys():
            if vd_tmp_key in ftu:
                tmp_str = vd_tmp.version_data[vd_tmp_key].upper()
                vd_tmp.version_data[vd_tmp_key] = tmp_str
        # get the version format string
        d_cv_fmt = { 'shot' : vd_tmp.version_data['shot'], 'version_separator' : version_separator, 'version_number' : vfmt_str%vd_tmp.version_data['version_number'], 'element_type' : vd_tmp.version_data['element_type'] }
        vd_tmp.set_client_version(client_version_fmt.format(**d_cv_fmt))
        vd_tmp.set_subdate(datetime.date.today().strftime(subform_date_format))
        if vd_tmp.version_data['b_hires']:
            vd_tmp.set_subreason(g_config.get('delivery', 'hires_subreason'))
        else:
            if g_matte:
                vd_tmp.set_subreason(g_config.get('delivery', 'matte_subreason'))
            else:
                vd_tmp.set_subreason(g_config.get('delivery', 'lores_subreason'))
        b_hires = False
        if g_version_status == g_version_status_2k:
            b_hires = True
        d_client_fname_fmt = {'client_version' : vd_tmp.version_data['client_version']}
        if b_hires:
            vd_tmp.set_client_filetype(vd_tmp.version_data['hires_ext'])
            d_client_fname_fmt['fileext'] = vd_tmp.version_data['hires_ext'].lower()
        else:
            if g_matte:
                vd_tmp.set_client_filetype(vd_tmp.version_data['matte_ext'])
                d_client_fname_fmt['fileext'] = vd_tmp.version_data['matte_ext'].lower()
            else:
                vd_tmp.set_client_filetype(vd_tmp.version_data['lores_ext'])
                d_client_fname_fmt['fileext'] = vd_tmp.version_data['lores_ext'].lower()
        
        if g_matte:
            vd_tmp.set_client_filename(client_matte_filename_format.format(**d_client_fname_fmt))
        else:
            vd_tmp.set_client_filename(client_filename_format.format(**d_client_fname_fmt))
        # lo-res and hi-res client filenames
        if vd_tmp.version_data['b_hires']:
            vd_tmp.set_client_hires_filetype(vd_tmp.version_data['hires_ext'])
            d_client_fname_fmt['fileext'] = vd_tmp.version_data['hires_ext'].lower()
            vd_tmp.set_client_hires_filename(client_filename_format.format(**d_client_fname_fmt))
        vd_tmp.set_client_lores_filetype(vd_tmp.version_data['lores_ext'])
        d_client_fname_fmt['fileext'] = vd_tmp.version_data['lores_ext'].lower()
        vd_tmp.set_client_lores_filename(client_filename_format.format(**d_client_fname_fmt))
                
        g_vdlist.append(vd_tmp)
    
def load_versions_for_status(m_status):
    global g_version_list, g_version_status_2k, g_version_status_qt, g_combined
    if g_combined:
        g_version_list = ihdb.fetch_versions_with_status(g_version_status_qt) + ihdb.fetch_versions_with_status(g_version_status_2k)
    else:
        g_version_list = ihdb.fetch_versions_with_status(m_status)

def load_versions_with_mattes():
    global g_version_list
    g_version_list = ihdb.fetch_versions_with_mattes()

def load_playlists():
    global g_playlists, g_playlist_age_days
    g_playlists = ihdb.fetch_playlists_timeframe(m_days_back=g_playlist_age_days)

def load_versions_from_playlist(m_playlist_obj):
    global g_version_list, g_internal_approval_status
    o_hero_playlist = ihdb.fetch_playlist(m_playlist_obj.g_playlist_name)
    tmp_version_list = []
    for tmp_version in o_hero_playlist.g_playlist_versions:
        if tmp_version.g_status == g_internal_approval_status:
            tmp_version_list.append(tmp_version)
    g_version_list = tmp_version_list

# build the submission form
def build_subform():
    
    global g_vdlist, g_version_status, g_version_status_2k, g_version_status_qt, g_delivery_folder, g_delivery_package, \
        g_config, g_sub_file_path, g_ale_file, g_matte, g_combined, g_subform_lpf, g_package_dir

    subform_file_format = g_config.get('delivery', 'subform_file_format')
    subform_filename_format = g_config.get('delivery', 'subform_filename_format')
    subform_filename = subform_filename_format.format(package = g_package_dir, ext = subform_file_format)
    subform_boolean_true = g_config.get('delivery', 'subform_boolean_true')
    subform_boolean_false = g_config.get('delivery', 'subform_boolean_false')

    delivery_path = os.path.join(g_delivery_folder, g_package_dir)
    l_subform_hardcode_items = g_config.get('delivery', 'subform_hardcode_items').split(',')
    d_subform_hardcode_items = {}
    for kvpair in l_subform_hardcode_items:
        names = kvpair.split('|')
        d_subform_hardcode_items[names[0]] = names[1]

    # excel header format
    l_subform_excel_header_format = g_config.get('delivery', 'subform_excel_header_format').split(',')
    d_subform_excel_header_format = {}
    for kvpair in l_subform_excel_header_format:
        names = kvpair.split('|')
        if names[1] == 'False':
            d_subform_excel_header_format[names[0]] = False
        elif names[1] == 'True':
            d_subform_excel_header_format[names[0]] = True
        else:
            d_subform_excel_header_format[names[0]] = names[1]

    # excel data format
    l_subform_excel_data_format = g_config.get('delivery', 'subform_excel_data_format').split(',')
    d_subform_excel_data_format = {}
    for kvpair in l_subform_excel_data_format:
        names = kvpair.split('|')
        if names[1] == 'False':
            d_subform_excel_data_format[names[0]] = False
        elif names[1] == 'True':
            d_subform_excel_data_format[names[0]] = True
        else:
            d_subform_excel_data_format[names[0]] = names[1]

    d_subform_translate = {}
    subform_cols = g_config.get('delivery', 'subform_translate').split(',')
    for kvpair in subform_cols:
        names = kvpair.split('|')
        d_subform_translate[names[0]] = names[1]

    headers = []
    for kvpair in subform_cols:
        csv_col = kvpair.split('|')[0]
        headers.append(csv_col)
            
    rows = []
    ale_rows = []

    b_hires = False
    if g_version_status == g_version_status_2k:
        b_hires = True
    
    matte_subreason = g_config.get('delivery', 'matte_subreason')
    matte_delivery_type = g_config.get('delivery', 'matte_delivery_type')
    
    for vd in g_vdlist:
        # Set the submission filename
        vd.set_subfilename(subform_filename)

        # set hard coded submission form entries
        for hc_key in d_subform_hardcode_items.keys():
            vd.set_arbitrary_version_data_item(hc_key, d_subform_hardcode_items[hc_key])

        rowdict = {}
        mattedict = {}
        ale_row_single = {}

        if g_subform_lpf:
            # add a line for the hires version if present
            if vd.version_data['b_hires']:
                for kvpair in subform_cols:
                    csv_col = kvpair.split('|')[0]
                    # handle booleans
                    if isinstance(vd.version_data[d_subform_translate[csv_col]], bool):
                        if vd.version_data[d_subform_translate[csv_col]]:
                            rowdict[csv_col] = subform_boolean_true
                        else:
                            rowdict[csv_col] = subform_boolean_false
                    else:
                        rowdict[csv_col] = vd.version_data[d_subform_translate[csv_col]]

                    if d_subform_translate[csv_col] == 'client_filename':
                        rowdict[csv_col] = vd.version_data['client_hires_filename']
                    if d_subform_translate[csv_col] == 'client_filetype':
                        rowdict[csv_col] = vd.version_data['client_hires_filetype']
                rows.append(rowdict)
            # and add a line for the lores version
            rowdict = {}
            for kvpair in subform_cols:
                csv_col = kvpair.split('|')[0]
                # handle booleans
                if isinstance(vd.version_data[d_subform_translate[csv_col]], bool):
                    if vd.version_data[d_subform_translate[csv_col]]:
                        rowdict[csv_col] = subform_boolean_true
                    else:
                        rowdict[csv_col] = subform_boolean_false
                else:
                    rowdict[csv_col] = vd.version_data[d_subform_translate[csv_col]]
                if d_subform_translate[csv_col] == 'client_filename':
                    rowdict[csv_col] = vd.version_data['client_lores_filename']
                if d_subform_translate[csv_col] == 'client_filetype':
                    rowdict[csv_col] = vd.version_data['client_lores_filetype']
            rows.append(rowdict)
        else:
            for kvpair in subform_cols:
                csv_col = kvpair.split('|')[0]
                # handle booleans
                if isinstance(vd.version_data[d_subform_translate[csv_col]], bool):
                    if vd.version_data[d_subform_translate[csv_col]]:
                        rowdict[csv_col] = subform_boolean_true
                    else:
                        rowdict[csv_col] = subform_boolean_false
                else:
                    rowdict[csv_col] = vd.version_data[d_subform_translate[csv_col]]
            if vd.version_data['b_matte'] and g_matte:
                for csv_col in d_subform_translate.keys():
                    mattedict[csv_col] = vd.version_data[d_subform_translate[csv_col]]
                    if d_subform_translate[csv_col] == 'subreason':
                        mattedict[csv_col] = matte_subreason
                    elif d_subform_translate[csv_col] == 'client_filetype':
                        mattedict[csv_col] = matte_delivery_type
                rows.append(mattedict)
            else:
                rows.append(rowdict)

        # ALE-specific stuff    
        ale_row_single['Tracks'] = 'V'
        if vd.version_data['b_hires']:
            ale_row_single['Name'] = "%s.%s"%(vd.version_data['client_version'], g_config.get('delivery', 'hires_delivery_type').lower())
        else:
            ale_row_single['Name'] = "%s.%s"%(vd.version_data['client_version'], g_config.get('delivery', 'lores_delivery_type').lower())
        ale_row_single['Tape'] = vd.version_data['client_version']
        ale_row_single['Start'] = str(vd.version_data['start_tc'])
        ale_row_single['End'] = str(vd.version_data['end_tc'])
        ale_row_single['frame_range'] = "%s-%s"%(vd.version_data['start_frame'], vd.version_data['end_frame'])
        local_slope = [str(ccval) for ccval in vd.version_data['ccdata'].slope]
        local_offset = [str(ccval) for ccval in vd.version_data['ccdata'].offset]
        local_power = [str(ccval) for ccval in vd.version_data['ccdata'].power]
        asc_sop_concat = "(%s)(%s)(%s)"%(' '.join(local_slope), ' '.join(local_offset), ' '.join(local_power))
        ale_row_single['ASC_SOP'] = asc_sop_concat
        ale_row_single['ASC_SAT'] = str(vd.version_data['ccdata'].saturation)
        ale_rows.append(ale_row_single)

        g_sub_file_path = os.path.join(delivery_path, subform_filename)

        if subform_file_format == 'csv':
            csvfile_fh = open(g_sub_file_path, 'w')
            csvfile_dw = csv.DictWriter(csvfile_fh, headers)
            csvfile_dw.writeheader()
            csvfile_dw.writerows(rows)
            csvfile_fh.close()
        elif subform_file_format == 'xlsx':
            # Write out xlsx file
            workbook = xlsxwriter.Workbook(g_sub_file_path)
            worksheet = workbook.add_worksheet(g_package_dir)
            # column width hack
            d_column_width = {}
            header_format = workbook.add_format(d_subform_excel_header_format)
            data_format = workbook.add_format(d_subform_excel_data_format)
            # write headers
            for header_idx, header_value in enumerate(headers):
                worksheet.write(0, header_idx, header_value, header_format)
                d_column_width[header_idx] = len(header_value)
            for row_idx, tmp_row_dict in enumerate(rows):
                for col_idx, header_name in enumerate(headers):
                    worksheet.write(row_idx + 1, col_idx, str(tmp_row_dict[header_name]), data_format)
                    if len(str(tmp_row_dict[header_name])) > d_column_width[col_idx]:
                        d_column_width[col_idx] = len(str(tmp_row_dict[header_name]))
            for tmp_col_idx in d_column_width.keys():
                worksheet.set_column(tmp_col_idx, tmp_col_idx, d_column_width[tmp_col_idx] + 5)
            workbook.close()
        else:
            raise Exception("Submission form file format %s not recognized."%subform_file_format)

        if g_write_ale and not g_matte:
            g_ale_file = os.path.join(delivery_path, "%s.ale"%g_package_dir)
            alefile_path = os.path.join(delivery_path, "%s.ale"%g_package_dir)
            alefile_fh = open(alefile_path, 'w')
            alefile_w = ALEWriter(alefile_fh)
            alefile_w.set_tape_name(g_package_dir)
            alefile_w.write_header(['Name', 'Tracks', 'Start', 'End', 'Tape', 'ASC_SOP', 'ASC_SAT', 'frame_range'])
            alefile_w.write_data(ale_rows)
            alefile_fh.close()
    
# this one does the heavy lifting of actually copying files into the delivery folder
# takes a VersionDelivery object as an argument
def copy_files(vd):
    global g_delivery_folder, g_package_dir, g_config, g_version_status, g_version_status_2k, g_version_status_qt, g_fileop, g_delivery_res, g_matte, g_combined
    cc_deliver = False
    if g_config.get('delivery', 'cc_deliver') in ['Yes', 'YES', 'yes', 'Y', 'y', 'True', 'TRUE', 'true']:
        cc_deliver = True
    cc_filetype = g_config.get('delivery', 'cc_filetype')
    hires_dest = g_config.get('delivery', 'hires_dest')
    matte_dest = g_config.get('delivery', 'matte_dest')
    cc_dest = g_config.get('delivery', 'cc_dest')
    avidqt_dest = g_config.get('delivery', 'avidqt_dest')
    vfxqt_dest = g_config.get('delivery', 'vfxqt_dest')
    exportqt_dest = g_config.get('delivery', 'exportqt_dest')
    output_path = os.path.join(g_delivery_folder, g_package_dir)
    if not os.path.exists(output_path):
        print "INFO: Making directory %s."%output_path
        os.makedirs(output_path)
    b_hires = False
    if g_version_status == g_version_status_2k:
        b_hires = True
    d_file_format = { 'client_version' : vd.version_data['client_version'], 
                      'pathsep' : os.path.sep, 
                      'format' : vd.version_data['hires_format'],
                      'hiresext' : 'exr',
                      'avidqtext' : 'mov',
                      'vfxqtext' : 'mov',
                      'exportqtext' : 'mov',
                      'matteext' : 'tif',
                      'frame' : '1000' }
    if b_hires or g_combined:
        # copy hires frames first
        hires_src_glob = vd.version_data['hires']
        if hires_src_glob and hires_src_glob != 'NO_HIRES_FRAMES':
            d_file_format['hiresext'] = os.path.splitext(hires_src_glob)[1].lstrip('.')
            for hr_src_file in glob.glob(hires_src_glob):
                tmp_frame = hr_src_file.split('.')[-2]
                d_file_format['frame'] = tmp_frame
                dest_file = os.path.join(output_path, hires_dest.format(**d_file_format))
                if not os.path.exists(os.path.dirname(dest_file)):
                    os.makedirs(os.path.dirname(dest_file))
                print "INFO: %s %s -> %s"%(g_fileop, hr_src_file, dest_file)
                if g_fileop == 'copy' : 
                    shutil.copyfile(hr_src_file, dest_file)
                elif g_fileop == 'hardlink' :
                    os.link(hr_src_file, dest_file)
            if cc_deliver:
                dest_file = os.path.join(output_path, cc_dest.format(**d_file_format))
                if not os.path.exists(os.path.dirname(dest_file)):
                    os.makedirs(os.path.dirname(dest_file))
                print "INFO: CC Data -> %s"%(dest_file)
                if cc_filetype == 'cc':
                    vd.version_data['ccdata'].write_cc_file(dest_file)
                elif cc_filetype == 'ccc':
                    vd.version_data['ccdata'].write_ccc_file(dest_file)
                elif cc_filetype == 'cdl':
                    vd.version_data['ccdata'].write_cdl_file(dest_file)
    if g_matte:
        if vd.version_data['b_matte']:
            matte_src_glob = vd.version_data['matte']
            d_file_format['matteext'] = os.path.splitext(matte_src_glob)[1].lstrip('.')
            for matte_src_file in glob.glob(matte_src_glob):
                tmp_frame = matte_src_file.split('.')[-2]
                d_file_format['frame'] = tmp_frame
                dest_file = os.path.join(output_path, matte_dest.format(**d_file_format))
                if not os.path.exists(os.path.dirname(dest_file)):
                    os.makedirs(os.path.dirname(dest_file))
                print "INFO: %s %s -> %s"%(g_fileop, matte_src_file, dest_file)
                if g_fileop == 'copy' : 
                    shutil.copyfile(matte_src_file, dest_file)
                elif g_fileop == 'hardlink' :
                    os.link(matte_src_file, dest_file)
    if not b_hires or g_combined:
        # copy quicktimes
        if vd.version_data['b_avidqt']:
            avidqt_src = vd.version_data['avidqt']
            avidqt_ext = os.path.splitext(avidqt_src)[1].lstrip('.')
            d_file_format['avidqtext'] = avidqt_ext
            dest_file = os.path.join(output_path, avidqt_dest.format(**d_file_format))
            if not os.path.exists(os.path.dirname(dest_file)):
                os.makedirs(os.path.dirname(dest_file))
            print "INFO: %s %s -> %s"%(g_fileop, avidqt_src, dest_file)
            if g_fileop == 'copy' : 
                shutil.copyfile(avidqt_src, dest_file)
            elif g_fileop == 'hardlink' :
                os.link(avidqt_src, dest_file)
        if vd.version_data['b_vfxqt']:
            vfxqt_src = vd.version_data['vfxqt']
            vfxqt_ext = os.path.splitext(vfxqt_src)[1].lstrip('.')
            d_file_format['vfxqtext'] = vfxqt_ext
            dest_file = os.path.join(output_path, vfxqt_dest.format(**d_file_format))
            if not os.path.exists(os.path.dirname(dest_file)):
                os.makedirs(os.path.dirname(dest_file))
            print "INFO: %s %s -> %s"%(g_fileop, vfxqt_src, dest_file)
            if g_fileop == 'copy' : 
                shutil.copyfile(vfxqt_src, dest_file)
            elif g_fileop == 'hardlink' :
                os.link(vfxqt_src, dest_file)
        if vd.version_data['b_exportqt']:
            exportqt_src = vd.version_data['exportqt']
            exportqt_ext = os.path.splitext(exportqt_src)[1].lstrip('.')
            d_file_format['exportqtext'] = exportqt_ext
            dest_file = os.path.join(output_path, exportqt_dest.format(**d_file_format))
            if not os.path.exists(os.path.dirname(dest_file)):
                os.makedirs(os.path.dirname(dest_file))
            print "INFO: %s %s -> %s"%(g_fileop, exportqt_src, dest_file)
            if g_fileop == 'copy' : 
                shutil.copyfile(exportqt_src, dest_file)
            elif g_fileop == 'hardlink' :
                os.link(exportqt_src, dest_file)

# updates status in database to delivered for each version

def set_version_delivered():

    global g_vdlist, ihdb, g_config, g_matte
    dlvr_status = g_config.get('delivery', 'db_delivered_status')
    for vd in g_vdlist:
        tmp_dbversion = vd.version_data['dbversion']
        tmp_dbversion.set_status(dlvr_status)
        tmp_dbversion.set_delivered(True)
        if g_matte:
            print "INFO: Setting matte_delivered to True on %s."%tmp_dbversion.g_version_code
            ihdb.update_version_matte_delivered(tmp_dbversion)
        else:
            print "INFO: Setting status on %s to %s."%(tmp_dbversion.g_version_code, tmp_dbversion.g_status)
            ihdb.update_version_status(tmp_dbversion)

# builds a playlist in the database for all current versions
def build_playlist():

    global ihdb, g_package_dir, g_version_list
    # create a playlist in the database based on this submission
    dbplaylist = ihdb.fetch_playlist(g_package_dir)
    if not dbplaylist:
        dbplaylist = DB.Playlist(g_package_dir, [], -1)
    dbplaylist.g_playlist_versions = g_version_list
    ihdb.create_playlist(dbplaylist)
    print "INFO: Created playlist %s in database."%(g_package_dir)
        
def execute_shell(m_interactive=False, m_2k=False, send_email=True, m_matte=False, m_combined=False, m_playlistonly=False, m_deliveryonly=False):
    global g_version_list, g_version_status, g_package_dir, g_vdlist, g_delivery_folder, g_delivery_package, g_matte, \
        g_combined, g_playlistonly, g_deliveryonly, g_playlists, g_playlist_age_days, g_package_dir, \
        g_internal_approval_status

    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt
        
    if m_matte:
        g_matte = True
        
    if m_combined:
        g_combined = True

    g_playlistonly = m_playlistonly
    g_deliveryonly = m_deliveryonly

    if not g_deliveryonly:
        if m_interactive and not m_2k:
            if g_matte:
                sys.stdout.write("Proceed with matte delivery? (y|n) ")
                input = sys.stdin.readline()
                if 'n' in input or 'N' in input:
                    print "Program will now exit."
                    return
            else:
                sys.stdout.write("Proceed with low-resolution (Quicktime) delivery? \nAnswering no will switch to high-resolution (2k) delivery: (y|n) ")
                input = sys.stdin.readline()
                if 'n' in input or 'N' in input:
                    print "INFO: Switching to high-resolution delivery."
                    g_version_status = g_version_status_2k

        if m_interactive and m_2k:
            sys.stdout.write("Proceed with high-resolution (2K) delivery? (y|n) ")
            input = sys.stdin.readline()
            if 'n' in input or 'N' in input:
                print "Program will now exit."
                return

        if m_interactive and m_combined:
            sys.stdout.write("Proceed with combined delivery? (y|n) ")
            input = sys.stdin.readline()
            if 'n' in input or 'N' in input:
                print "Program will now exit."
                return

        if g_matte:
            load_versions_with_mattes()
        else:
            load_versions_for_status(g_version_status)

        version_names = []
        for version in g_version_list:
            version_names.append(version.g_version_code)

        print("INFO: List of versions matching status %s:" % g_version_status)
        print("")
        for count, version_name in enumerate(version_names, 1):
            print("%2d. %s" % (count, version_name))

        print("")
        if len(version_names) == 0:
            print("WARNING: No versions in the database for status %s!" % g_version_status)
            print("Program will now exit.")

        if m_interactive:
            sys.stdout.write("Remove any versions from the delivery?\nInput a comma-separated list of version index numbers: ")
            input = sys.stdin.readline()
            versions_rm = []
            for idx in input.split(','):
                i_idx = 0
                try:
                    i_idx = int(idx)
                except ValueError:
                    print("ERROR: %s is not a valid number." % idx)
                    continue
                if i_idx > 0 and i_idx <= len(version_names):
                    versions_rm.append(i_idx - 1)
                else:
                    print("ERROR: %s is not a valid index number." % idx)
                    continue
            new_version_list = []
            for count, version in enumerate(g_version_list):
                if count in versions_rm:
                    print("INFO: Removing version %s from delivery list." % version.g_version_code)
                else:
                    new_version_list.append(version)
            g_version_list = new_version_list

    else:
        g_playlistonly = False
        o_hero_playlist = None
        if m_interactive:
            sys.stdout.write("Proceed with delivery only? (y|n) ")
            input = sys.stdin.readline()
            if 'n' in input or 'N' in input:
                print("Program will now exit.")
                return

        # retrieve the list of available playlists from the database
        load_playlists()
        playlist_names = []
        for playlist in g_playlists:
            playlist_names.append(playlist.g_playlist_name)

        print("INFO: Playlists created within the last %d days:"%g_playlist_age_days)
        print("")
        for count, playlist_name in enumerate(playlist_names, 1):
            print("%2d. %s" % (count, playlist_name))

        print("")
        if len(playlist_names) == 0:
            print("WARNING: No playlists have been created in the database in the last %d days!" % g_playlist_age_days)
            print("Program will now exit.")
            return

        if m_interactive:
            while (True):
                sys.stdout.write("Please enter the number for the playlist you would like to deliver to production: ")
                input = sys.stdin.readline()
                i_idx = 0
                try:
                    i_idx = int(input)
                    o_hero_playlist = g_playlists[i_idx - 1]
                    break
                except ValueError:
                    print("ERROR: %s is not a valid number." % input)
                except IndexError:
                    print("ERROR: There is no playlist number %s." % input)
        else:
            print("INFO: Not running in interactive mode. Will choose playlist #1 above.")
            o_hero_playlist = g_playlists[0]

        print("INFO: Setting package name equal to playlist name: %s"%o_hero_playlist.g_playlist_name)
        g_package_dir = o_hero_playlist.g_playlist_name
        print("INFO: Will deliver all versions with %s status from playlist %s."%(g_internal_approval_status,o_hero_playlist.g_playlist_name))
        load_versions_from_playlist(o_hero_playlist)

    file_list = []
    try:
        get_delivery_directory()
        print "INFO: Delivery package initialized to %s."%g_delivery_package
        vd_list_from_versions()
        if len(g_vdlist) == 0:
            raise RuntimeError("There are no versions available to send to production! Please select at least one in order to proceed.")
        else:
            print "INFO: Retrieved all information from database."
        if not g_playlistonly:
            for tmp_vd in g_vdlist:
                print "INFO: Copying files for version %s to package."%tmp_vd.version_data['dbversion'].g_version_code
                file_list.append(tmp_vd.version_data['client_filename'])
                copy_files(tmp_vd)

            print "INFO: Building Submission Form and ALE Files."
            print "INFO: %s Location: %s.%s"%(g_subform_file_format.upper(), os.path.join(g_delivery_package, g_package_dir), g_subform_file_format.lower())
            print "INFO: ALE Location: %s.ale"%os.path.join(g_delivery_package, g_package_dir)
            build_subform()
            print "INFO: Setting status of all versions in submission to Delivered."
            set_version_delivered()
        if not g_deliveryonly:
            print "INFO: Building a playlist in the database."
            build_playlist()
        if send_email and not g_playlistonly:
            print "INFO: Spawning a sync child processs to copy files to production. Email notification will be sent upon completion."
            handle_sync_and_send_email(os.path.join(g_delivery_folder, g_package_dir), file_list)
        print "INFO: Delivery is complete."
    except:
        e = sys.exc_info()
        etype = e[0].__name__
        emsg = e[1]
        print "ERROR: Caught exception of type %s!"%etype
        print "  MSG: %s"%emsg
        print traceback.format_exc(e[2])
        

    
class CheckBoxDelegate(QItemDelegate):
    """
    A delegate that places a fully functioning QCheckBox cell of the column to which it's applied.
    """
    def __init__(self, parent):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        """
        Important, otherwise an editor is created if the user clicks in this cell.
        """
        return None

    def paint(self, painter, option, index):
        """
        Paint a checkbox without the label.
        """
        self.drawCheck(painter, option, option.rect, Qt.Unchecked if int(index.data()) == 0 else Qt.Checked)

    def editorEvent(self, event, model, option, index):
        '''
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton and this cell is editable. Otherwise do nothing.
        '''
        #         if not int(index.flags() & Qt.ItemIsEditable) > 0:
        #             print 'Item not editable'
        #             return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # Change the checkbox-state
            self.setModelData(None, model, index)
            return True

        return False


    def setModelData (self, editor, model, index):
        '''
        The user wanted to change the old state in the opposite.
        '''
        # print "INFO: Inside setModelData() for CheckBoxDelegate"
        # print "INFO: index.data() = %s"%index.data()
        model.setData(index, True if int(index.data()) == 0 else False, Qt.EditRole)

class PublishDeliveryWindow(QMainWindow):
    def __init__(self, m_2k=False, send_email=True, m_matte=False, m_combined=False, m_playlistonly=False):
        super(PublishDeliveryWindow, self).__init__()
        self.b_send_email = send_email
        self.b_playlistonly = m_playlistonly
        self.setWindowTitle('Publish Delivery')
        self.setMinimumSize(1024,768)
    
        # central widget
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
    
        self.layout_top = QHBoxLayout()
        self.delivery_label = QLabel()
        self.delivery_label.setText("Choose a delivery type:")
    
        self.layout_top.addWidget(self.delivery_label)
    
        # ComboBox to select Quicktime or High-resolution delivery
        self.delivery_cbox = QComboBox()
        self.delivery_cbox.addItems(["Avid/VFX Quicktime", "High Resolution (DPX/EXR)", "DI Matte", "Combined MOV/Hi-Res"])
        if m_2k:
            self.delivery_cbox.setCurrentIndex(1)
        else:
            if m_matte:
                self.delivery_cbox.setCurrentIndex(2)
            if m_combined:
                self.delivery_cbox.setCurrentIndex(3)
                
        self.delivery_cbox.currentIndexChanged.connect(self.delivery_type_change)
    
        self.layout_top.addWidget(self.delivery_cbox)
    
        self.layout.addLayout(self.layout_top)
        
        self.layout_mid = QHBoxLayout()

        # Let's try this with a QTableView
        self.table_model = DeliveryTableModel(self, self.table_data(), self.table_header())
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.resizeColumnsToContents()
        self.table_view.setSortingEnabled(True)
        delegate = CheckBoxDelegate(None)
        self.table_view.setItemDelegateForColumn(0, delegate)          
        self.layout_mid.addWidget(self.table_view)
        self.layout.addLayout(self.layout_mid)

        # buttons at the bottom        
        self.layout_bottom = QHBoxLayout()
        self.buttons = QDialogButtonBox(self)
        self.buttons.setOrientation(Qt.Horizontal)
        self.buttons.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)     
        self.layout_bottom.addWidget(self.buttons)
        self.layout.addLayout(self.layout_bottom)

        self.results_window = PublishDeliveryResultsWindow(self)
        
    def reject(self):
        global g_cancel
        g_cancel = True
        print "INFO: User has cancelled operation."
        QCoreApplication.instance().quit()

    def process_delivery(self):
        global g_package_dir, g_delivery_package, g_delivery_folder, g_vdlist, g_matte, g_version_list
        file_list = []
        self.hide()
        self.results_window.show()
        try:
            # first, get delivery directory
            get_delivery_directory()
            self.results_window.delivery_results.appendPlainText("INFO: Delivery package initialized to %s."%g_delivery_package)
            QApplication.processEvents()
            # get detailed version delivery list from list of database versions
            vd_list_from_versions()
            for tmp_vd in g_vdlist:
                print "INFO: Proceeding with delivery for client version %s."%tmp_vd.version_data['client_version']
            if len(g_vdlist) == 0:
                raise RuntimeError("There are no versions selected to send to production! Please select at least one in order to proceed.")
            else:
                self.results_window.delivery_results.appendPlainText("INFO: Retrieved all information from database.")
            QApplication.processEvents()
            if not self.b_playlistonly:
                for tmp_vd in g_vdlist:
                    self.results_window.delivery_results.appendPlainText("INFO: Copying files for version %s to package."%tmp_vd.version_data['dbversion'].g_version_code)
                    file_list.append(tmp_vd.version_data['client_filename'])
                    QApplication.processEvents()
                    copy_files(tmp_vd)
                self.results_window.delivery_results.appendPlainText("INFO: Building Submission Form and ALE Files.")
                self.results_window.delivery_results.appendPlainText("INFO: CSV Location: %s.csv"%os.path.join(g_package_dir, g_delivery_package))
                if not g_matte:
                    self.results_window.delivery_results.appendPlainText("INFO: ALE Location: %s.ale"%os.path.join(g_package_dir, g_delivery_package))
                QApplication.processEvents()
                build_subform()
                self.results_window.delivery_results.appendPlainText("INFO: Setting status of all versions in submission to Delivered.")
                QApplication.processEvents()
                set_version_delivered()
                QApplication.processEvents()
            self.results_window.delivery_results.appendPlainText("INFO: Building playlist %s in the database."%g_package_dir)
            if not g_matte:
                build_playlist()
            QApplication.processEvents()
            if self.b_send_email and not self.b_playlistonly:
                self.results_window.delivery_results.appendPlainText("INFO: Spawning a sync child processs to copy files to production. Email notification will be sent upon completion.")
                QApplication.processEvents()
                handle_sync_and_send_email(os.path.join(g_delivery_folder, g_package_dir), file_list)
            self.results_window.delivery_results.appendPlainText("INFO: Delivery is complete.")
            QApplication.processEvents()
        except:
            e = sys.exc_info()
            etype = e[0].__name__
            emsg = e[1]
            self.results_window.delivery_results.appendPlainText("ERROR: Caught exception of type %s!"%etype)
            self.results_window.delivery_results.appendPlainText("  MSG: %s"%emsg)
            self.results_window.delivery_results.appendPlainText(traceback.format_exc(e[2]))
            QApplication.processEvents()
        self.results_window.close_button.setEnabled(True)
    
    def accept(self):
        global g_version_list
        tmp_version_list = []
        print "INFO: Proceeding with delivery publish."
        for index, row in enumerate(self.table_model.mylist):
            if not row[0]:
                print "INFO: User requested removal of %s from delivery."%row[2]
            else:
                for dbversion in g_version_list:
                    if dbversion.g_version_code == row[2]:
                        print "INFO: Version %s will be included in delivery."%row[2]
                        tmp_version_list.append(dbversion)
        g_version_list = tmp_version_list
        self.process_delivery()

    def table_data(self):
        global g_matte
        version_table_ret = []
        global g_version_list
        for version in g_version_list:
            if g_matte:
                version_table_ret.append([True, version.g_dbid, version.g_version_code, version.g_shot.g_shot_code, version.g_artist.g_full_name, version.g_path_to_matte_frames])
            else:
                version_table_ret.append([True, version.g_dbid, version.g_version_code, version.g_shot.g_shot_code, version.g_artist.g_full_name, version.g_path_to_frames])
        return version_table_ret
        
    def table_header(self):
        version_header_ret = ['Include?', 'Database ID', 'Version Name', 'Shot Name', 'Artist Name', 'Path to Frames']
        return version_header_ret

    def delivery_type_change(self, idx):
        global g_version_status, g_version_list, g_combined
    
        if idx == 0:
            print "INFO: Switching delivery type to Avid/VFX Quicktime."
            g_version_status = g_version_status_qt
            load_versions_for_status(g_version_status)
        elif idx == 1:
            print "INFO: Switching delivery type to High Resolution (DPX/EXR)."
            g_version_status = g_version_status_2k
            load_versions_for_status(g_version_status)
        elif idx == 2:
            print "INFO: Switching delivery type to DI Matte."
            g_version_status = g_version_status_2k
            load_versions_with_mattes()
        elif idx == 3:
            print "INFO: Switching delivery type to Combined."
            g_version_status = g_version_status_qt
            g_combined = True
            load_versions_for_status(g_version_status)
        
        self.table_model.updateModel(self.table_data())
        self.table_view.setModel(self.table_model)
        self.table_view.update()

class DeliveryTableModel(QAbstractTableModel):
    def __init__(self, parent, mylist, header, *args):
        super(DeliveryTableModel, self).__init__()
        self.mylist = mylist
        self.header = header
    def updateModel(self, mylist):
        self.mylist = mylist
    def rowCount(self, parent):
        return len(self.mylist)
    def columnCount(self, parent):
        return len(self.header)
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def setData(self, index, value, role=Qt.DisplayRole):
        if index.column() == 0:
            print "INFO: Setting checkbox value to %s"%value
            self.mylist[index.row()][0] = value
            return value
        return value

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self, col, order):
        """sort table by given column number col"""
        self.layoutAboutToBeChanged.emit()
        self.mylist = sorted(self.mylist,
            key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.layoutChanged.emit()
        
class PublishDeliveryResultsWindow(QMainWindow):
    def __init__(self, parent):
        super(PublishDeliveryResultsWindow, self).__init__(parent)
        self.setWindowTitle('Publish Delivery')
        self.setMinimumSize(640,480)
    
        # central widget
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
    
        self.layout_top = QHBoxLayout()
        self.delivery_results = QPlainTextEdit()
    
        self.layout_top.addWidget(self.delivery_results)
        self.layout.addLayout(self.layout_top)
        # buttons at the bottom        
        self.layout_bottom = QHBoxLayout()
        self.close_button = QPushButton("Close", self)
        # self.close_button.setOrientation(Qt.Horizontal)
        # self.close_button.setStandardButtons(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.close_button.clicked.connect(self.window_close)
        self.close_button.setEnabled(False)
        self.layout_bottom.addWidget(self.close_button)
        self.layout.addLayout(self.layout_bottom)


    def window_close(self):
        QCoreApplication.instance().quit()

def display_window(m_2k=False, send_email=True, m_matte=False, m_combined=False, m_playlistonly=False, m_deliveryonly=False):
    global g_version_list, g_version_status, g_vdlist, g_matte, g_combined, g_playlistonly, g_deliveryonly
    g_combined = m_combined
    g_playlistonly = m_playlistonly
    g_deliveryonly = m_deliveryonly
    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt

    if m_matte:
        g_matte = True
        load_versions_with_mattes()
    else:
        g_matte = False
        load_versions_for_status(g_version_status)
        
    # Create a Qt application
    app = QApplication(sys.argv)
 
    # Our main window will be a QListView
    window = PublishDeliveryWindow(m_2k, send_email, g_matte, g_combined, g_playlistonly)
    window.show()
    app.exec_()
    

    
