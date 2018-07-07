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
g_csv_file = None
g_ale_file = None

# copy/paste from goosebumps2_delivery

g_distro_list_to = None
g_distro_list_cc = None
g_mail_from = None
g_mail_from_address = None
g_write_ale = False
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

def globals_from_config():
    global ihdb, g_ih_show_cfg_path, g_ih_show_root, g_ih_show_code, g_config, g_version_status, g_version_status_2k, g_version_status_qt, g_project_code, g_vendor_code, g_vendor_name, g_delivery_folder, g_fileop, g_delivery_res
    global g_distro_list_to, g_distro_list_cc, g_mail_from, g_write_ale, g_shared_root, g_credentials_dir, g_client_secret, g_gmail_creds, g_application_name, g_email_text, g_rsync_enabled, g_rsync_filetypes, g_rsync_dest
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
        
        g_distro_list_to = g_config.get('email', 'distro_list_to')
        g_distro_list_cc = g_config.get('email', 'distro_list_cc')
        g_mail_from = g_config.get('email', 'mail_from')
        if g_config.get(g_ih_show_code, 'write_ale') == 'yes':
            g_write_ale = True
    
        g_shared_root = g_config.get('shared_root', sys.platform)
        credentials_dir_dict = { 'pathsep' : os.path.sep, 'shared_root' : g_shared_root }
        g_credentials_dir = g_config.get('email', 'credentials_dir').format(**credentials_dir_dict)
        g_client_secret = g_config.get('email', 'client_secret')
        g_gmail_creds = g_config.get('email', 'gmail_creds')
        g_gmail_scopes = g_config.get('email', 'gmail_scopes')
        g_application_name = g_config.get('email', 'application_name')
        g_email_text = g_config.get('email', 'email_text')
        g_rsync_enabled = True if g_config.get(g_ih_show_code, 'delivery_rsync_enabled') == 'yes' else False
        g_rsync_filetypes = g_config.get(g_ih_show_code, 'delivery_rsync_filetypes').split(',')
        g_rsync_dest = g_config.get(g_ih_show_code, 'delivery_rsync_dest')
        
        
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

def handle_rsync(m_source_folder):
    global g_rsync_filetypes, g_rsync_dest
    rsync_cmd = ['rsync',
                 '-auv',
                 '--prune-empty-dirs',
                 '--include="*/"']
    for valid_ext in g_rsync_filetypes:
        rsync_cmd.append('--include="*.%s"'%valid_ext)
    rsync_cmd.append('--exclude="*"')    
    rsync_cmd.append(m_source_folder.rstrip('/'))
    rsync_cmd.append(g_rsync_dest)
    print "INFO: Executing command: %s"%" ".join(rsync_cmd)
    subprocess.Popen(" ".join(rsync_cmd), shell=True)
            
def get_credentials():
    global g_credentials_dir, g_gmail_greds, g_application_name, g_client_secret, g_gmail_scopes
    if not os.path.exists(g_credentials_dir):
        print "WARNING: Credentials directory in config file %s does not exist. Creating."%g_credentials_dir
        os.makedirs(g_credentials_dir)
    credential_path = os.path.join(g_credentials_dir, g_gmail_creds)
    print "INFO: Searching for credential: %s"%credential_path
    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(g_client_secret, g_gmail_scopes)
        flow.user_agent = g_application_name
        credentials = tools.run_flow(flow, store)
        print('INFO: Storing credentials to ' + credential_path)
    return credentials

def SendMessage(sender, to, cc, subject, msgHtml, msgPlain, attachmentFile=None):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    if attachmentFile:
        message1 = createMessageWithAttachment(sender, to, cc, subject, msgHtml, msgPlain, attachmentFile)
    else: 
        message1 = CreateMessageHtml(sender, to, cc, subject, msgHtml, msgPlain)
    result = SendMessageInternal(service, "me", message1)
    return result

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('INFO: Message send complete, message ID: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('ERROR: Caught HttpError: %s' % error)
        return "Error"
    return "OK"

def CreateMessageHtml(sender, to, cc, subject, msgHtml, msgPlain):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg['Cc'] = cc
    msg.attach(MIMEText(msgPlain, 'plain'))
    msg.attach(MIMEText(msgHtml, 'html'))
    return {'raw': base64.urlsafe_b64encode(msg.as_string())}

def createMessageWithAttachment(
    sender, to, cc, subject, msgHtml, msgPlain, attachmentFile):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      msgHtml: Html message to be sent
      msgPlain: Alternative plain text message for older email clients          
      attachmentFile: The path to the file to be attached.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['cc'] = cc
    message['from'] = sender
    message['subject'] = subject

    print "Email Message: %s"%msgPlain
    message.attach(MIMEText(msgPlain))

    print("create_message_with_attachment: file: %s" % attachmentFile)
    content_type, encoding = mimetypes.guess_type(attachmentFile)

    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    if main_type == 'text':
        fp = open(attachmentFile, 'rb')
        msg = MIMEText(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'image':
        fp = open(attachmentFile, 'rb')
        msg = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'audio':
        fp = open(attachmentFile, 'rb')
        msg = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(attachmentFile, 'rb')
        msg = MIMEBase(main_type, sub_type)
        msg.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(attachmentFile)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_string())}

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

# builds the body of the email message
def send_email(delivery_directory, file_list, shot_count):

    global g_rsync_dest, g_email_text, g_mail_from, g_distro_list_to, g_distro_list_cc, g_config
    formatted_list= "\n".join(file_list)

    final_destination_dir = os.path.join(g_rsync_dest, os.path.split(delivery_directory)[-1])
    	
    d_email_text = {'shot_count' : shot_count, 'delivery_folder' : final_destination_dir, 'shot_list' : formatted_list}
    msg = g_email_text.format(**d_email_text).replace('\\r', '\r')
    csvfiles = glob.glob(os.path.join(delivery_directory, '*.csv'))
    d_email_subject = {'package' : os.path.split(delivery_directory)[-1]}
    s_subject = g_config.get('email', 'subject').format(**d_email_subject)
    
    if len(csvfiles) > 0:
        SendMessage(g_mail_from, g_distro_list_to, g_distro_list_cc, s_subject, msg, msg, csvfiles[0])
    else:
        SendMessage(g_mail_from, g_distro_list_to, g_distro_list_cc, s_subject, msg, msg)
        
    return msg

def get_delivery_directory():
    global g_version_status, g_version_status_qt, g_version_status_2k, g_ih_show_code, g_project_code, g_vendor_code, g_vendor_name, g_package_dir, g_batch_id, g_delivery_folder, g_delivery_package
    dt_hires = g_config.get('delivery', 'hires_delivery_type')
    dt_lores = g_config.get('delivery', 'lores_delivery_type')
    delivery_type = dt_lores
    if g_version_status == g_version_status_2k:
        delivery_type = dt_hires
        
    b_use_global_serial = False
    if g_config.get('delivery', 'use_global_serial') in ['Yes', 'yes', 'YES', 'Y', 'y', 'True', 'TRUE', 'true']:
        b_use_global_serial = True
        
    
    delivery_serial = int(g_config.get('delivery', 'serial_start'))
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
                    if int(folder_match_dict['serial']) > max_serial:
                        max_serial = int(folder_match_dict['serial'])
                else:
                    if folder_match_dict['date'] == today:
                        if int(folder_match_dict['serial']) > max_serial:
                            max_serial = int(folder_match_dict['serial'])
    d_folder_format = {'vendor_code' : g_vendor_code, 'project_code' : g_project_code, 'date' : today, 'serial' : str(max_serial + 1), 'delivery_type' : delivery_type}
    g_package_dir = g_config.get('delivery', 'package_directory').format(**d_folder_format)
    g_batch_id = g_config.get('delivery', 'batch_id').format(**d_folder_format)
    g_delivery_package = os.path.join(g_delivery_folder, g_package_dir)

def vd_list_from_versions():
    global g_version_list, g_vdlist
    global g_config, g_ih_show_code, g_vendor_code, g_vendor_name, g_batch_id, g_package_dir, g_version_status, g_version_status_2k, g_version_status_qt
    version_separator = g_config.get(g_ih_show_code, 'version_separator')
    ftu = g_config.get('delivery', 'fields_to_uppercase').split(',')
    element_type_re = re.compile(g_config.get('delivery', 'element_type_regexp'))
    client_version_fmt = g_config.get('delivery', 'client_version_format')
    subform_date_format = g_config.get('delivery', 'subform_date_format')
    client_filename_format = g_config.get('delivery', 'client_filename')
    for dbversion in g_version_list:
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
        for vd_tmp_key in vd_tmp.version_data.keys():
            if vd_tmp_key in ftu:
                tmp_str = vd_tmp.version_data[vd_tmp_key].upper()
                vd_tmp.version_data[vd_tmp_key] = tmp_str
        d_cv_fmt = { 'shot' : vd_tmp.version_data['shot'], 'version_separator' : version_separator, 'version_number' : str(vd_tmp.version_data['version_number']), 'element_type' : vd_tmp.version_data['element_type'] }
        vd_tmp.set_client_version(client_version_fmt.format(**d_cv_fmt))
        vd_tmp.set_subdate(datetime.date.today().strftime(subform_date_format))
        if vd_tmp.version_data['b_hires']:
            vd_tmp.set_subreason(g_config.get('delivery', 'hires_subreason'))
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
            vd_tmp.set_client_filetype(vd_tmp.version_data['lores_ext'])
            d_client_fname_fmt['fileext'] = vd_tmp.version_data['lores_ext'].lower()
        vd_tmp.set_client_filename(client_filename_format.format(**d_client_fname_fmt))
        g_vdlist.append(vd_tmp)
    
def load_versions_for_status(m_status):
    global g_version_list
    g_version_list = ihdb.fetch_versions_with_status(m_status)

# build the submission form
def build_subform():
    
    global g_vdlist, g_version_status, g_version_status_2k, g_version_status_qt, g_delivery_folder, g_delivery_package, g_config, g_csv_file, g_ale_file
    
    delivery_path = os.path.join(g_delivery_folder, g_package_dir)
    
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
        rowdict = {}
        mattedict = {}
        ale_row_single = {}

        for kvpair in subform_cols:
            csv_col = kvpair.split('|')[0]
            rowdict[csv_col] = vd.version_data[d_subform_translate[csv_col]]
        
        rows.append(rowdict)
        if vd.version_data['b_matte'] and b_hires:
            for csv_col in d_subform_translate.keys():
                mattedict[csv_col] = vd.version_data[d_subform_translate[csv_col]]
                if d_subform_translate[csv_col] == 'subreason':
                    mattedict[csv_col] = matte_subreason
                elif d_subform_translate[csv_col] == 'client_filetype':
                    mattedict[csv_col] = matte_delivery_type
            rows.append(mattedict)

        # ALE-specific stuff    
        ale_row_single['Tracks'] = 'V'
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

        g_csv_file = os.path.join(delivery_path, "%s.csv"%g_package_dir)
        csvfile_path = os.path.join(delivery_path, "%s.csv"%g_package_dir)
        csvfile_fh = open(csvfile_path, 'w')
        csvfile_dw = csv.DictWriter(csvfile_fh, headers)
        csvfile_dw.writeheader()
        csvfile_dw.writerows(rows)
        csvfile_fh.close()        
        
        if g_write_ale:
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
    global g_delivery_folder, g_package_dir, g_config, g_version_status, g_version_status_2k, g_version_status_qt, g_fileop, g_delivery_res
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
    if b_hires:
        # copy hires frames first
        hires_src_glob = vd.version_data['hires']
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
    else:
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

    global g_vdlist, ihdb, g_config
    dlvr_status = g_config.get('delivery', 'db_delivered_status')
    for vd in g_vdlist:
        tmp_dbversion = vd.version_data['dbversion']
        tmp_dbversion.set_status(dlvr_status)
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
        
def execute_shell(m_interactive=False, m_2k=False):
    global g_version_list, g_version_status, g_package_dir, g_vdlist, g_delivery_folder, g_delivery_package

    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt
    
    if m_interactive and not m_2k:
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

    load_versions_for_status(g_version_status)
    version_names = []
    for version in g_version_list:
        version_names.append(version.g_version_code)
    
    print "INFO: List of versions matching status %s:"%g_version_status
    print ""
    for count, version_name in enumerate(version_names, 1):
        print "%2d. %s"%(count, version_name)
    
    print ""
    if len(version_names) == 0:
        print "WARNING: No versions in the database for status %s!"%g_version_status
        print "Program will now exit."
        
    if m_interactive:
        sys.stdout.write("Remove any versions from the delivery?\nInput a comma-separated list of version index numbers: ")
        input = sys.stdin.readline()
        versions_rm = []
        for idx in input.split(','):
            i_idx = 0
            try:
                i_idx = int(idx)
            except ValueError:
                print "ERROR: %s is not a valid number."%idx
                continue
            if i_idx > 0 and i_idx <= len(version_names):
                versions_rm.append(i_idx - 1)
            else:
                print "ERROR: %s is not a valid index number."%idx
                continue
        new_version_list = []
        for count, version in enumerate(g_version_list):
            if count in versions_rm:
                print "INFO: Removing version %s from delivery list."%version.g_version_code
            else:
                new_version_list.append(version)
        g_version_list = new_version_list

    file_list = []    
    get_delivery_directory()
    print "INFO: Delivery package initialized to %s."%g_package_dir
    vd_list_from_versions()
    print "INFO: Retrieved all information from database."
    for tmp_vd in g_vdlist:
        print "INFO: Copying files for version %s to package."%tmp_vd.version_data['dbversion'].g_version_code
        file_list.append(tmp_vd.version_data['client_filename'])
        copy_files(tmp_vd)
        
    print "INFO: Building Submission Form and ALE Files."
    print "INFO: CSV Location: %s.csv"%os.path.join(g_package_dir, g_delivery_package)
    print "INFO: ALE Location: %s.ale"%os.path.join(g_package_dir, g_delivery_package)
    build_subform()
    print "INFO: Setting status of all versions in submission to Delivered."
    set_version_delivered()
    print "INFO: Building a playlist in the database."
    build_playlist()
    print "INFO: Spawning a rsync child processs to copy files to production."
    handle_rsync(os.path.join(g_delivery_folder, g_package_dir))
    print "INFO: Sending email indicating that the process is complete."
    send_email(os.path.join(g_delivery_folder, g_package_dir), file_list, len(file_list))
    print "INFO: Delivery is complete."
    
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
        model.setData(index, True if int(index.data()) == 0 else False, Qt.EditRole)

class PublishDeliveryWindow(QMainWindow):
    def __init__(self, m_2k=False):
        super(PublishDeliveryWindow, self).__init__()
        self.setWindowTitle('Publish Delivery')
        self.setMinimumSize(640,480)
    
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
        self.delivery_cbox.addItems(["Avid/VFX Quicktime", "High Resolution (DPX/EXR)"])
        if m_2k:
            self.delivery_cbox.setCurrentIndex(1)
    
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
        global g_package_dir, g_delivery_package, g_delivery_folder, g_vdlist
        file_list = []
        self.hide()
        self.results_window.show()
        get_delivery_directory()
        self.results_window.delivery_results.appendPlainText("INFO: Delivery package initialized to %s."%g_package_dir)
        QApplication.processEvents()
        vd_list_from_versions()
        self.results_window.delivery_results.appendPlainText("INFO: Retrieved all information from database.")
        QApplication.processEvents()
        for tmp_vd in g_vdlist:
            self.results_window.delivery_results.appendPlainText("INFO: Copying files for version %s to package."%tmp_vd.version_data['dbversion'].g_version_code)
            file_list.append(tmp_vd.version_data['client_filename'])
            QApplication.processEvents()
            copy_files(tmp_vd)
        self.results_window.delivery_results.appendPlainText("INFO: Building Submission Form and ALE Files.")
        self.results_window.delivery_results.appendPlainText("INFO: CSV Location: %s.csv"%os.path.join(g_package_dir, g_delivery_package))
        self.results_window.delivery_results.appendPlainText("INFO: ALE Location: %s.ale"%os.path.join(g_package_dir, g_delivery_package))
        QApplication.processEvents()
        build_subform()
        self.results_window.delivery_results.appendPlainText("INFO: Setting status of all versions in submission to Delivered.")
        QApplication.processEvents()
        set_version_delivered()
        QApplication.processEvents()
        self.results_window.delivery_results.appendPlainText("INFO: Building playlist %s in the database."%g_package_dir)
        build_playlist()
        self.results_window.delivery_results.appendPlainText("INFO: Spawning a rsync child processs to copy files to production.")
        QApplication.processEvents()
        handle_rsync(os.path.join(g_delivery_folder, g_package_dir))
        self.results_window.delivery_results.appendPlainText("INFO: Sending email indicating that the process is complete.")
        QApplication.processEvents()
        send_email(os.path.join(g_delivery_folder, g_package_dir), file_list, len(file_list))
        self.results_window.delivery_results.appendPlainText("INFO: Delivery is complete.")
        QApplication.processEvents()
        self.results_window.close_button.setEnabled(True)
    
    def accept(self):
        global g_version_list
        tmp_version_list = []
        # print "INFO: Proceeding with delivery publish."
        for index, row in enumerate(self.table_model.mylist):
            if not row[0]:
                print "INFO: User requested removal of %s from delivery."%row[2]
            else:
                tmp_version_list.append(g_version_list[index])
        g_version_list = tmp_version_list
        self.process_delivery()

    def table_data(self):
        version_table_ret = []
        global g_version_list
        for version in g_version_list:
            version_table_ret.append([True, version.g_dbid, version.g_version_code, version.g_shot.g_shot_code, version.g_artist.g_full_name, version.g_path_to_frames])
        return version_table_ret
        
    def table_header(self):
        version_header_ret = ['Include?', 'Database ID', 'Version Name', 'Shot Name', 'Artist Name', 'Path to Frames']
        return version_header_ret

    def delivery_type_change(self, idx):
        global g_version_status, g_version_list
    
        if idx == 0:
            print "INFO: Switching delivery type to Avid/VFX Quicktime."
            g_version_status = g_version_status_qt
        elif idx == 1:
            print "INFO: Switching delivery type to High Resolution (DPX/EXR)."
            g_version_status = g_version_status_2k

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

def display_window(m_2k=False):
    global g_version_list, g_version_status, g_vdlist
    if m_2k:
        g_version_status = g_version_status_2k
    else:
        g_version_status = g_version_status_qt

    load_versions_for_status(g_version_status)
        
    # Create a Qt application
    app = QApplication(sys.argv)
 
    # Our main window will be a QListView
    window = PublishDeliveryWindow(m_2k)
    window.show()
    app.exec_()
    

    
