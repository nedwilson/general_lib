#!/usr/bin/python

import ConfigParser
import os
import sys
import re
import tempfile
import subprocess

# global config objects
g_config = None

# method that returns a config file object, or throws an exception if we are not launched in the In-House pipeline
def get_config():
    global g_config
    if g_config == None:
        g_config = ConfigParser.ConfigParser()
        show_config_path = None
        try:
            show_config_path = os.environ['IH_SHOW_CFG_PATH']
        except KeyError:
            raise RuntimeError("This system does not have an IH_SHOW_CFG_PATH environment variable defined.")
        if not os.path.exists(show_config_path):
            raise RuntimeError("The IH_SHOW_CFG_PATH environment variable is defined on this system with value %s, but no file exists at that location."%show_config_path)
        try:
            g_config.read(show_config_path)
        except:
            raise
        return g_config
    else:
        return g_config

#
# create_thumbnail takes one argument: the path of an image to make a thumbnail from. 
# it requires that environment variable IH_SHOW_CFG_PATH be defined, and that config
# file must have a thumb_template section.
#
# it writes the thumbnail out to the data/thumbnails directory of the shot.
# 
    
def create_thumbnail(m_source_path, b_applycc=True):

    if sys.platform == 'win32':
        print "Platform is windows, outputting debugging information."
        print 'm_source_path : %s'%m_source_path
        
    if not os.path.exists(m_source_path):
        raise IOError("File not found: %s"%m_source_path)
    
    show_cfg_path = None
    show_root = None
    show_code = None

    config = get_config()
    
    show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
    show_root = os.environ['IH_SHOW_ROOT']
    show_code = os.environ['IH_SHOW_CODE']
        
    shot_regexp = config.get(show_code, 'shot_regexp')
    shot_dir_format = config.get(show_code, 'shot_dir_format')
    cdl_dir_format = config.get(show_code, 'cdl_dir_format')
    write_frame_format = config.get(show_code, 'write_frame_format')
    cdl_ext = config.get(show_code, 'cdl_file_ext')
    shot_lut_path = config.get('color', 'shot_lut_file_path_%s'%sys.platform)
    thumb_template = config.get('thumbnails', 'template_%s'%sys.platform)
    thumb_dir = config.get('thumbnails', 'shot_thumb_dir')
    nuke_exe_path = config.get('nuke_exe_path', sys.platform)

    # color transform nodes
    s_colorspace_node = None
    s_cdl_node = None
    s_lut_node = None

    try:
        tmp_colorspace_node = config.get('thumbnails', 'colorspace_node')
        tmp_cdl_node = config.get('thumbnails', 'cdl_node')
        tmp_lut_node = config.get('thumbnails', 'lut_node')
        if len(tmp_colorspace_node) > 0:
            s_colorspace_node = tmp_colorspace_node
        if len(tmp_cdl_node) > 0:
            s_cdl_node = tmp_cdl_node
        if len(tmp_lut_node) > 0:
            s_lut_node = tmp_lut_node
    except ConfigParser.NoOptionError as e:
        print("ERROR: Show config file %s is missing some options!"%show_cfg_path)
        print(e.message)
        raise e

    filename_re = re.compile(r'(?P<head>[\\\/A-Za-z \._\-0-9]+)\.(?P<frame>[0-9]+)\.(?P<ext>[a-zA-Z0-9]+)$')
    shot_re = re.compile(shot_regexp)
    
    match_obj = filename_re.search(m_source_path)
    head = match_obj.group('head')
    frame = match_obj.group('frame')
    ext = match_obj.group('ext')
    
    if not head or not frame or not ext:
        raise ValueError("Image path provided to create_thumbnail, %s, does not appear to be part of an image sequence."%m_source_path)
        
    match_obj = shot_re.search(head)
    
    shot = match_obj.group('shot')
    seq = match_obj.group('sequence')
    
    if not shot or not seq:
        raise ValueError("Image path provided to create_thumbnail, %s, does not match the shot naming convention for show %s."%(m_source_path, show_code))
    
    base = os.path.basename(head)
    dest_path_format = "%s{pathsep}%s{pathsep}%s_thumb.{framepad}.png"%(shot_dir_format, thumb_dir, base)
    format_dict = { 'pathsep' : os.path.sep, 'show_root' : show_root, 'sequence' : seq, 'shot' : shot, 'framepad' : write_frame_format  }
    dest_path = dest_path_format.format(**format_dict).replace('\\', '/')
    
    format_dict['framepad'] = write_frame_format%int(frame)
    dest_path_frame = dest_path_format.format(**format_dict)
    
    print "INFO: Thumbnail path: %s"%dest_path

    # try to locate the CDL for the shot, if it exists

    lut_format_dict = {'sequence': seq, 'shot': shot, 'ext': cdl_ext}

    b_deliver_cdl = True

    s_cdl_src = shot_lut_path.format(**lut_format_dict)

    # do we have a specific CDL for this image sequence?
    if not os.path.exists(s_cdl_src):
        b_deliver_cdl = False

    s_cccid = None

    if not b_applycc:
        b_deliver_cdl = False

    if b_deliver_cdl and cdl_ext in ['cc', 'ccc', 'cdl']:
        # open up the cdl and extract the cccid
        print "INFO: Using color correction file at %s."%s_cdl_src
        cdltext = open(s_cdl_src, 'r').read()
        cccid_re_str = r'<ColorCorrection id="([A-Za-z0-9-_]+)">'
        cccid_re = re.compile(cccid_re_str)
        cccid_match = cccid_re.search(cdltext)
        if cccid_match:
            s_cccid = cccid_match.group(1)
    
        # slope
        slope_re_str = r'<Slope>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Slope>'
        slope_re = re.compile(slope_re_str)
        slope_match = slope_re.search(cdltext)
        if slope_match:
            slope_r = slope_match.group(1)
            slope_g = slope_match.group(2)
            slope_b = slope_match.group(3)
        else:
            slope_r = 1.0
            slope_g = 1.0
            slope_b = 1.0

        # offset
        offset_re_str = r'<Offset>([0-9.-e]+) ([0-9.-e]+) ([0-9.-e]+)</Offset>'
        offset_re = re.compile(offset_re_str)
        offset_match = offset_re.search(cdltext)
        if offset_match:
            offset_r = offset_match.group(1)
            offset_g = offset_match.group(2)
            offset_b = offset_match.group(3)
        else:
            offset_r = 0.0
            offset_g = 0.0
            offset_b = 0.0
            
        # power
        power_re_str = r'<Power>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Power>'
        power_re = re.compile(power_re_str)
        power_match = power_re.search(cdltext)
        if power_match:
            power_r = power_match.group(1)
            power_g = power_match.group(2)
            power_b = power_match.group(3)
        else:
            power_r = 1.0
            power_g = 1.0
            power_b = 1.0
            
        # saturation
        saturation_re_str = r'<Saturation>([0-9.-]+)</Saturation>'
        saturation_re = re.compile(saturation_re_str)
        saturation_match = saturation_re.search(cdltext)
        if saturation_match:
            saturation = saturation_match.group(1)
        else:
            saturation = 1.0
    
    
    fh_nukepy, s_nukepy = tempfile.mkstemp(suffix='.py')
    
    print "INFO: Temporary Python script: %s"%s_nukepy
    os.write(fh_nukepy, "#!/usr/bin/python\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "import nuke\n")
    os.write(fh_nukepy, "import os\n")
    os.write(fh_nukepy, "import sys\n")
    os.write(fh_nukepy, "import traceback\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "nuke.scriptOpen(\"%s\")\n"%thumb_template.replace('\\', '/'))
    os.write(fh_nukepy, "nd_root = root = nuke.root()\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "# set root frame range\n")
    os.write(fh_nukepy, "nd_root.knob('first_frame').setValue(%d)\n"%int(frame))
    os.write(fh_nukepy, "nd_root.knob('last_frame').setValue(%d)\n"%int(frame))
    os.write(fh_nukepy, "nd_read = nuke.toNode('SRC_READ')\n")
    os.write(fh_nukepy, "nd_read.knob('file').setValue(\"%s\")\n"%m_source_path)
    os.write(fh_nukepy, "nd_read.knob('first').setValue(%d)\n"%int(frame))
    os.write(fh_nukepy, "nd_read.knob('last').setValue(%d)\n"%int(frame))

    if not b_deliver_cdl:
        if s_colorspace_node:
            os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%s_colorspace_node)
        if s_cdl_node:
            os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%s_cdl_node)
        if s_lut_node:
            os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%s_lut_node)
    else:
        if cdl_ext in [ 'cc', 'ccc', 'cdl' ]:
            if s_cdl_node:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue(\"%s\")\n"%(s_cdl_node, s_cdl_src))
                if s_cccid:
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('cccid').setValue(\"%s\")\n"%(s_cdl_node, s_cccid))
                os.write(fh_nukepy, "nuke.toNode('%s').knob('read_from_file').setValue(False)\n"%s_cdl_node)
                os.write(fh_nukepy, "nuke.toNode('%s').knob('slope').setValue([%s, %s, %s])\n"%(s_cdl_node, slope_r, slope_g, slope_b))
                os.write(fh_nukepy, "nuke.toNode('%s').knob('offset').setValue([%s, %s, %s])\n"%(s_cdl_node, offset_r, offset_g, offset_b))
                os.write(fh_nukepy, "nuke.toNode('%s').knob('power').setValue([%s, %s, %s])\n"%(s_cdl_node, power_r, power_g, power_b))
                os.write(fh_nukepy, "nuke.toNode('%s').knob('saturation').setValue(%s)\n"%(s_cdl_node, saturation))
        else:
            if s_lut_node:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue(\"%s\")\n" % (s_lut_node, s_cdl_src))

    os.write(fh_nukepy, "nuke.toNode('THUMB_WRITE').knob('file').setValue('%s')\n"%dest_path)            
    os.write(fh_nukepy, "print \"INFO: About to execute render...\"\n")
    os.write(fh_nukepy, "try:\n")
    os.write(fh_nukepy, "    nuke.execute(nuke.toNode(\"%s\"),%d,%d,1,)\n"%('THUMB_WRITE', int(frame), int(frame)))
    os.write(fh_nukepy, "except:\n")
    os.write(fh_nukepy, "    print \"ERROR: Exception caught!\\n%s\"%traceback.format_exc()\n")
    os.close(fh_nukepy)
    
    s_pyscript = s_nukepy
    s_windows_addl = ""
    s_cmd = ""
    if sys.platform == 'win32':
        l_win32_netpath_transforms = config.get(show_code, 'win32_netpath_transforms').split('|')
        s_windows_addl = ' --remap "%s,%s"'%(l_win32_netpath_transforms[0], l_win32_netpath_transforms[1])
        s_cmd = "\"%s\" -i -V 2%s -c 2G -t %s" % (nuke_exe_path, s_windows_addl, s_pyscript)
    else:
        s_cmd = "%s -i -V 2 -c 2G -t %s" % (nuke_exe_path, s_pyscript)

    s_err_ar = []
    print "INFO: Thumbnail render command: %s" % s_cmd
    proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, shell=True)
    while proc.poll() is None:
        try:
            s_out = proc.stdout.readline()
            s_err_ar.append(s_out.rstrip())
        except IOError:
            print "ERROR: IOError Caught!"
            var = traceback.format_exc()
            print var
    if proc.returncode != 0:
        s_errmsg = ""
        s_err = proc.stderr.read()
        s_errmsg = "Error(s) have occurred. Details:\n%s" % s_err
        print(s_errmsg)
        if s_errmsg.find('FOUNDRY LICENSE ERROR REPORT') != -1:
            raise Exception('Nuke is unable to get a license!\nDetails:\n%s' % s_err)
        else:
            raise Exception('The thumbnail creation process did not complete successfully!\nDetails:\n%s' % s_err)
    else:
        print("INFO: Successfully completed thumbnail render.")

    return dest_path_frame

def create_thumbnail_from_movie(m_source_path, m_frame_number):

    if not os.path.exists(m_source_path):
        raise IOError("File not found: %s"%m_source_path)
    
    show_cfg_path = None
    show_root = None
    show_code = None

    config = get_config()
    
    show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
    show_root = os.environ['IH_SHOW_ROOT']
    show_code = os.environ['IH_SHOW_CODE']
        
    shot_regexp = config.get(show_code, 'shot_regexp')
    shot_dir_format = config.get(show_code, 'shot_dir_format')
    cdl_dir_format = config.get(show_code, 'cdl_dir_format')
    write_frame_format = config.get(show_code, 'write_frame_format')
    cdl_ext = config.get(show_code, 'cdl_file_ext')
    thumb_template = config.get('thumbnails', 'template_movie_%s'%sys.platform)
    thumb_dir = config.get('thumbnails', 'shot_thumb_dir')
    nuke_exe_path = config.get('nuke_exe_path', sys.platform)
    
    filename_re = re.compile(r'(?P<head>[\\\/A-Za-z \._\-0-9]+)\.(?P<ext>[a-zA-Z0-9]+)$')
    shot_re = re.compile(shot_regexp)
    
    match_obj = filename_re.search(m_source_path)
    head = match_obj.group('head')
    frame = m_frame_number
    ext = match_obj.group('ext')
    
    if not head or not frame or not ext:
        print "Head: %s"%head
        print "Ext: %s"%ext
        print "Frame: %s"%frame
        print "About to raise ValueError exception."
        print "Source path: %s"%m_source_path
        raise ValueError("Movie path provided to create_thumbnail, %s, appears to be invalid."%m_source_path)
        
    match_obj = shot_re.search(head)
    
    shot = match_obj.group('shot')
    seq = match_obj.group('sequence')
    
    if not shot or not seq:
        raise ValueError("Movie path provided to create_thumbnail, %s, does not match the shot naming convention for show %s."%(m_source_path, show_code))
    
    base = os.path.basename(head)
    dest_path_format = "%s{pathsep}%s{pathsep}%s_movie_thumb.{framepad}.png"%(shot_dir_format, thumb_dir, base)
    format_dict = { 'pathsep' : os.path.sep, 'show_root' : show_root, 'sequence' : seq, 'shot' : shot, 'framepad' : write_frame_format  }
    dest_path = dest_path_format.format(**format_dict).replace('\\', '/')
    
    format_dict['framepad'] = "%04d"%int(frame)
    dest_path_frame = dest_path_format.format(**format_dict)
    
    print "INFO: Thumbnail path: %s"%dest_path
    
    # try to locate the CDL for the shot, if it exists
    
    fh_nukepy, s_nukepy = tempfile.mkstemp(suffix='.py')
    
    print "INFO: Temporary Python script: %s"%s_nukepy
    os.write(fh_nukepy, "#!/usr/bin/python\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "import nuke\n")
    os.write(fh_nukepy, "import os\n")
    os.write(fh_nukepy, "import sys\n")
    os.write(fh_nukepy, "import traceback\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "nuke.scriptOpen(\"%s\")\n"%thumb_template.replace('\\', '/'))
    os.write(fh_nukepy, "nd_root = root = nuke.root()\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "# set root frame range\n")
    os.write(fh_nukepy, "nd_root.knob('first_frame').setValue(%d)\n"%int(frame))
    os.write(fh_nukepy, "nd_root.knob('last_frame').setValue(%d)\n"%int(frame))
    os.write(fh_nukepy, "nd_read = nuke.toNode('SRC_READ')\n")
    os.write(fh_nukepy, "nd_read.knob('file').setValue(\"%s\")\n"%m_source_path)
    # os.write(fh_nukepy, "nd_read.knob('first').setValue(%d)\n"%int(frame))
    # os.write(fh_nukepy, "nd_read.knob('last').setValue(%d)\n"%int(frame))

    os.write(fh_nukepy, "nuke.toNode('THUMB_WRITE').knob('file').setValue('%s')\n"%dest_path)            
    os.write(fh_nukepy, "print \"INFO: About to execute render...\"\n")
    os.write(fh_nukepy, "try:\n")
    os.write(fh_nukepy, "    nuke.execute(nuke.toNode(\"%s\"),%d,%d,1,)\n"%('THUMB_WRITE', int(frame), int(frame)))
    os.write(fh_nukepy, "except:\n")
    os.write(fh_nukepy, "    print \"ERROR: Exception caught!\\n%s\"%traceback.format_exc()\n")
    os.close(fh_nukepy)
    
    s_pyscript = s_nukepy
    s_windows_addl = ""
    s_cmd = ""
    if sys.platform == 'win32':
        l_win32_netpath_transforms = config.get(show_code, 'win32_netpath_transforms').split('|')
        s_windows_addl = ' --remap "%s,%s"'%(l_win32_netpath_transforms[0], l_win32_netpath_transforms[1])
        s_cmd = r'"%s" -i -V 2%s -c 2G -t %s' % (nuke_exe_path, s_windows_addl, s_pyscript)
    else:
        s_cmd = r'%s -i -V 2 -c 2G -t %s' % (nuke_exe_path, s_pyscript)


    print("INFO: Thumbnail render command: %s" % s_cmd)
    s_stdout_ar = []
    proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    while proc.poll() is None:
        try:
            s_out = proc.stdout.readline()
            s_stdout_ar.append(s_out.rstrip())
        except IOError:
            print("ERROR: IOError Caught!")
            var = traceback.format_exc()
            print(var)
    if proc.returncode != 0:
        s_errmsg = ""
        s_err = proc.stderr.read()
        s_errmsg = "Error(s) have occurred. Details:\n%s" % s_err
        print(s_errmsg)
        if s_errmsg.find('FOUNDRY LICENSE ERROR REPORT') != -1:
            raise Exception('Nuke is unable to get a license!\nDetails:\n%s' % s_err)
        else:
            raise Exception('The thumbnail creation process did not complete successfully!\nDetails:\n%s' % s_err)
    else:
        print("INFO: Successfully completed thumbnail render.")

    return dest_path_frame
