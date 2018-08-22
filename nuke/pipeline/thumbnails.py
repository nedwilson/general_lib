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
    
def create_thumbnail(m_source_path):

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
    thumb_template = config.get('thumbnails', 'template_%s'%sys.platform)
    thumb_dir = config.get('thumbnails', 'shot_thumb_dir')
    nuke_exe_path = config.get('nuke_exe_path', sys.platform)
    
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
    
    format_dict['framepad'] = "%04d"%int(frame)
    dest_path_frame = dest_path_format.format(**format_dict)
    
    print "INFO: Thumbnail path: %s"%dest_path
    
    # try to locate the CDL for the shot, if it exists
    
    cdl_format_dict = { 'pathsep' : os.path.sep, 'show_root' : show_root, 'sequence' : seq, 'shot' : shot }
    cdl_dir = ("%s{pathsep}%s"%(shot_dir_format, cdl_dir_format)).format(**cdl_format_dict)

    b_deliver_cdl = True
    
    s_cdl_src = os.path.join(cdl_dir, "%s.%s"%(base, cdl_ext))
   
    # do we have a specific CDL for this image sequence?
    if not os.path.exists(s_cdl_src):
        # try to find a generic one for the shot
        s_cdl_src = os.path.join(cdl_dir, "%s.%s"%(shot, cdl_ext))
        if not os.path.exists(s_cdl_src):
            print "WARNING: Unable to locate CDL file at: %s"%s_cdl_src
            b_deliver_cdl = False

    s_cccid = None
    if b_deliver_cdl:    
        # open up the cdl and extract the cccid
        print "INFO: Using CDL file at %s."%s_cdl_src
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
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('disable').setValue(True)\n")
    else:
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('file').setValue(\"%s\")\n"%s_cdl_src.replace('\\', '/'))
        if s_cccid:
            os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('cccid').setValue(\"%s\")\n"%s_cccid)
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('read_from_file').setValue(False)\n")
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('slope').setValue([%s, %s, %s])\n"%(slope_r, slope_g, slope_b))
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('offset').setValue([%s, %s, %s])\n"%(offset_r, offset_g, offset_b))
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('power').setValue([%s, %s, %s])\n"%(power_r, power_g, power_b))
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('saturation').setValue(%s)\n"%saturation)

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
        s_windows_addl = ' --remap "/Volumes/raid_vol01,Y:"'
        s_cmd = "\"%s\" -i -V 2%s -c 2G -t %s" % (nuke_exe_path, s_windows_addl, s_pyscript)
    else:
        s_cmd = "%s -i -V 2 -c 2G -t %s" % (nuke_exe_path, s_pyscript)

    
    s_err_ar = []
    print "INFO: Thumbnail render command: %s" % s_cmd
    proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
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
        if sys.platform == 'win32':
            s_err_ar = proc.stdout.read().split('\n')
        s_err = '\n'.join(s_err_ar)
        l_err_verbose = []
        for err_line in s_err_ar:
            if err_line.find("ERROR") != -1:
                l_err_verbose.append(err_line)
        if s_err.find("FOUNDRY LICENSE ERROR REPORT") != -1:
            s_errmsg = "Unable to obtain a license for Nuke! Package execution fails, will not proceed!"
        else:
            s_errmsg = "Error(s) have occurred. Details:\n%s"%'\n'.join(l_err_verbose)
        print s_errmsg
    else:
        print "INFO: Successfully completed thumbnail render."
    
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
        s_windows_addl = ' --remap "/Volumes/raid_vol01,Y:"'
        s_cmd = "\"%s\" -i -V 2%s -c 2G -t %s" % (nuke_exe_path, s_windows_addl, s_pyscript)
    else:
        s_cmd = "%s -i -V 2 -c 2G -t %s" % (nuke_exe_path, s_pyscript)

    
    s_err_ar = []
    print "INFO: Thumbnail render command: %s" % s_cmd
    proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
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
        if sys.platform == 'win32':
            s_err_ar = proc.stdout.read().split('\n')
        s_err = '\n'.join(s_err_ar)
        l_err_verbose = []
        for err_line in s_err_ar:
            if err_line.find("ERROR") != -1:
                l_err_verbose.append(err_line)
        if s_err.find("FOUNDRY LICENSE ERROR REPORT") != -1:
            s_errmsg = "Unable to obtain a license for Nuke! Package execution fails, will not proceed!"
        else:
            s_errmsg = "Error(s) have occurred. Details:\n%s"%'\n'.join(l_err_verbose)
        print s_errmsg
    else:
        print "INFO: Successfully completed thumbnail render."
    
    return dest_path_frame
