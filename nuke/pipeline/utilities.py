#!/usr/bin/python

import getpass
import glob
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import xml.dom.minidom as minidom
import xml.etree.ElementTree as etree
from operator import attrgetter
from operator import itemgetter
from stat import ST_MTIME

import ConfigParser
import nukescripts

import nuke

if not sys.platform == 'win32':
    import pwd
    import OpenEXR

import db_access as DB

from thumbnails import create_thumbnail
from thumbnails import create_thumbnail_from_movie

# global config objects
g_config = None
g_ihdb = None

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

# method checks to see if global DBAccess variable is None, and if so, create a new DBAccess object
def get_ihdb():
    global g_ihdb
    if not g_ihdb:
        g_ihdb = DB.DBAccessGlobals.get_db_access()            
    
def quickLabel():
    sel = nuke.selectedNodes()[0]
    sel['label'].setValue(nuke.getInput('Enter Label Text'))

def getPixDir():
    script_name = nuke.root().knob('name').value()
    script_dir = os.path.dirname(script_name)
    pix = os.path.join(os.path.dirname(script_dir), "pix", "plates")
    return (pix)

def getRenderDir():
    script_name = nuke.root().knob('name').value()
    script_dir = os.path.dirname(script_name)
    pix = os.path.join(os.path.dirname(script_dir), "pix", "comp")
    return (pix)

def copyReadToShot():
    s = nuke.selectedNodes()
    for node in s:
        if node.Class() == "Read":

            file = node['file'].getValue()
            base = os.path.basename(file).split('.')[0] + "*" + os.path.splitext(file)[1]

            fileList = glob.glob(os.path.join(os.path.dirname(file), base))
            print fileList
            dest = os.path.join(getPixDir(), os.path.basename(file).split('.')[0])
            while os.path.exists(dest):
                dest += "_1"
                print dest
            os.mkdir(dest)
            print dest
            task = nuke.ProgressTask("Copying Read To Shot Tree")
            fileCount = len(fileList)

            for count, imgfile in enumerate(fileList):
                task.setMessage("copying file: %d of %d" % (count, fileCount))
                task.setProgress(int(100 * (count / float(fileCount))))
                shutil.copy(imgfile, dest)
            node['file'].setValue(os.path.join(dest, os.path.basename(file)))

def copyRenderToShot():
    s = nuke.selectedNodes()
    for node in s:
        if node.Class() == "Write":

            file = node['file'].getValue()
            base = os.path.basename(file).split('.')[0] + "*" + os.path.splitext(file)[1]

            fileList = glob.glob(os.path.join(os.path.dirname(file), base))

            dest = os.path.join(getRenderDir(), os.path.basename(file).split('.')[0])
            if not os.path.exists(dest):
                os.mkdir(dest)
            task = nuke.ProgressTask("Copying Files")

            for count, imgfile in enumerate(fileList):
                shutil.copy(imgfile, dest)
                task.setProgress(int(count / float(len(fileList)) * 100))
            node['file'].setValue(os.path.join(dest, os.path.basename(file)))
        else:
            nuke.message("Selected write nodes will copy to the delivery folder for the shot")

def setup_luts():
    nuke.root()['defaultViewerLUT'].setValue("OCIO LUTs")
    nuke.root()['OCIO_config'].setValue("custom")

def copyFiles(render_path, exr_dest_fulldir):
    task = nuke.ProgressTask("Copy Files")
    task.setMessage("Copying files")
    fileList = glob.glob(os.path.join(os.path.dirname(render_path), r'*.exr'))

    for count, exrfile in enumerate(fileList):
        shutil.copy(exrfile, exr_dest_fulldir)
        if task.isCancelled():
            nuke.executeInMainThread(nuke.message, args=("Copy Cancelled!"))
            break;
        task.setProgress(float(count) / float(len(fileList)))

## makeSad() tells you how many roto/paint layers you have.
def makeSad():
    count = 0
    for sel in nuke.allNodes():
        if sel.Class() in ("RotoPaint", "Roto"):
            rt = sel['curves'].rootLayer
            count += len(rt)

    nuke.message("You have used %d paint strokes for only %d frames! You should feel very proud." % (
    count, (nuke.root()['last_frame'].getValue() - nuke.root()['first_frame'].getValue())))

# returns the full name of the current user
def user_full_name(str_host_name=None):
    rval = "IH Artist"
    try:
        # no windows support at this time
        if sys.platform == 'win32':
            return rval
        else:
            rval = pwd.getpwuid(os.getuid()).pw_gecos
    except ImportError:
        print "Error: Looks like you're running Windows, and do not have pyad installed."
        print "       To install, run pip install pyad"
        raise
    except:
        pass
    return rval

def get_login():
    rval = 'ned'
    try:
        rval = getpass.getuser()
    except:
        pass
    return rval

# class that defines a PrecompPanel
class PrecompPanel(nukescripts.panels.PythonPanel):
    def __init__(self, m_existing_precomps):
        nukescripts.PythonPanel.__init__(self, 'Create a Precomp')
        self.existing_pc_knob = nuke.Enumeration_Knob('existing_pc', 'Use Existing Precomp?', m_existing_precomps)
        self.new_pc_knob = nuke.String_Knob('new_pc', 'New Precomp Name:')
        self.addKnob(self.existing_pc_knob)
        self.addKnob(self.new_pc_knob)

# makes a precomp write node. Prompts the user to either select from an existing precomp or make a new one 
def precomp_write():
    print "INFO: Entering utilities.py method precomp_write()."
    m_precomp_dir = None
    config = get_config()
    m_shot_dir = None
    m_version_sep = '_v'
    m_version_start = 1
    m_version_format = '%03d'
    m_write_frame_format = '%04d'
    m_write_extension = 'exr'
    
    # first, check to be sure that we have been launched inside a valid in-house shot:
    try:
        m_shot_dir = os.environ['SHOT_PATH']
    except KeyError:
        raise RuntimeError("Make Precomp Write must be executed with a valid, In-House Nuke script open.")
    
    # figure out the path to the precomp directory    
    try:
        d_format = { 'pathsep' : os.path.sep }
        m_precomp_dir = os.path.join(m_shot_dir, config.get('shot_structure', 'precomp_dir').format(**d_format))
    except:
        print "WARNING: show-level config file at %s does not contain an entry for shot_structure : precomp_dir. Using default."%os.environ['IH_SHOW_CFG_PATH']
        m_precomp_dir = os.path.join(m_shot_dir, 'pix', 'precomp')

    try:
        m_version_sep = config.get(os.environ['IH_SHOW_CODE'], 'version_separator')
        m_version_start = int(config.get(os.environ['IH_SHOW_CODE'], 'version_start'))
        m_version_format = config.get(os.environ['IH_SHOW_CODE'], 'version_format')
        m_write_frame_format = config.get(os.environ['IH_SHOW_CODE'], 'write_frame_format')
        m_write_extension = config.get(os.environ['IH_SHOW_CODE'], 'write_extension')
    except:
        pass
    

    # make directory, if necessary
    if not os.path.exists(m_precomp_dir):
        os.makedirs(m_precomp_dir)
        
    shot = os.environ['SHOT']
    element_name_re = re.compile('%s(.*)%s([0-9]+)'%(shot, m_version_sep))
    existing_precomps = {}
    for pc_dir in glob.glob(os.path.join(m_precomp_dir, '*')):
        dir_name = os.path.basename(pc_dir)
        element_match = element_name_re.search(dir_name)
        if element_match:
            element_name = element_match.group(1).lstrip('_')
            try:
                version_list = existing_precomps[element_name]
                version_list.append(element_match.group(2))
            except:
                existing_precomps[element_name] = [element_match.group(2)]
                
    # display the precomp creation panel
    gui_list = existing_precomps.keys()
    gui_list.insert(0, 'Create New')
    precomp_panel = PrecompPanel(gui_list)
    
    new_dir = None
    new_dir_format = '%s_%s%s' + m_version_format
        
    if precomp_panel.showModalDialog():
        existing_pc = precomp_panel.existing_pc_knob.value()
        new_pc = None
        if existing_pc == 'Create New':
            new_pc = precomp_panel.new_pc_knob.value()
            if not new_pc:
                nuke.message("If you wish to create a new precomp, please enter in a name for the element in the dialog box.")
                return
            else:
                new_dir = new_dir_format%(shot, new_pc, m_version_sep, int(m_version_start))
        else:
            new_dir = new_dir_format%(shot, existing_pc, m_version_sep, int(sorted(existing_precomps[existing_pc])[-1]) + 1)
    else:
        print "INFO: User cancelled operation."
        
    os.makedirs(os.path.join(m_precomp_dir, new_dir))
    full_precomp_path = os.path.join(m_precomp_dir, new_dir, '%s.%s.%s'%(new_dir, m_write_frame_format, m_write_extension))
    write_node = nuke.createNode("Write", "file %s file_type %s channels all"%(full_precomp_path, m_write_extension), inpanel=False)
    print "INFO: Successfully created Write node with file path: %s"%full_precomp_path
    return
    
# overrides nukescripts.version_up(). will make a directory for versioned up write nodes
# if one does not exist.
def version_up_mkdir():
    nukescripts.version_up()
    n = nuke.selectedNodes()
    for i in n:
        _class = i.Class()
        if _class == "Write":
            _dirname = os.path.dirname(i.knob("file").value())
            if not os.path.exists(_dirname):
                print "INFO: Making directory %s." % _dirname
                os.makedirs(_dirname)

def os_path_sub(m_source_path):
    try:
        config = get_config()
        cfg_sr_darwin = config.get('show_root', 'darwin')
        cfg_sr_thishost = config.get('show_root', sys.platform)

        newfile = ""

        if sys.platform == 'win32':
            newfile = m_source_path.replace(cfg_sr_darwin, cfg_sr_thishost)
            m_source_path = newfile
    except:
        raise
    return m_source_path

# creates a read node from a write node.

def read_from_write():
    sel = None
    file_path = ""
    start_frame = 1000
    end_frame = 1001
    node = None
    xpos = 0
    ypos = 0
    re_frame_txt = r'(\.|_| )(?P<frame>[0-9]+)\.'
    re_frame = re.compile(re_frame_txt)
    try:
        sel = nuke.selectedNodes()
    except:
        print "INFO: No nodes selected."
        return
    for nd in sel:
        if nd.Class() != "Write":
            continue
        file_path = nd.knob("file").value()
        
        # convert the show root if necessary for a specific platform
        config = get_config()
        cfg_sr_darwin = config.get('show_root', 'darwin')
        cfg_sr_thishost = config.get('show_root', sys.platform)
    
        newfile = ""
    
        if sys.platform == 'win32':
            newfile = file_path.replace(cfg_sr_darwin, cfg_sr_thishost)
            file_path = newfile

        file_type = nd.knob("file_type").value()
        read_node = nuke.createNode("Read", "file {" + file_path + "}", inpanel=True)
        if os.path.exists(os.path.dirname(file_path)):
            if not file_type == "mov":
                image_ar = sorted(glob.glob(file_path.replace('%04d', '*')))
                if (len(image_ar) == 0):
                    match_obj = re_frame.search(file_path)
                    start_file_path = file_path

                    if match_obj:
                        start_frame = int(match_obj.group('frame'))
                        end_frame = int(match_obj.group('frame'))
                    else:
                        start_frame = 1
                        end_frame = 1
                else:
                    start_file_path = image_ar[0]
                    start_frame = int(image_ar[0].split('.')[1])
                    end_frame = int(image_ar[-1].split('.')[1])

            if not sys.platform == "win32":
                start_file = OpenEXR.InputFile(start_file_path)
                dwindow_header = start_file.header()['displayWindow']
                width = dwindow_header.max.x - dwindow_header.min.x + 1
                height = dwindow_header.max.y - dwindow_header.min.y + 1
                format_obj = None
                for fmt in nuke.formats():
                    if int(width) == int(fmt.width()) and int(height) == int(fmt.height()):
                        format_obj = fmt
                if not format_obj:
                    fstring = '%d %d Unknown Image Format'%(width, height)
                    format_obj = nuke.addFormat(fstring)
                
                read_node.knob("format").setValue(format_obj)        

            read_node.knob("first").setValue(start_frame)
            read_node.knob("origfirst").setValue(start_frame)
            read_node.knob("last").setValue(end_frame)
            read_node.knob("origlast").setValue(end_frame)
            read_node.knob("colorspace").setValue(re.search(r"(?:default \()?([\w\d]+)\)?",nd.knob("colorspace").value()).group(1))
            read_node.knob("raw").setValue(nd.knob("raw").value())
        xpos = nd.knob("xpos").value()
        ypos = nd.knob("ypos").value()
        read_node.knob("xpos").setValue(xpos)
        read_node.knob("ypos").setValue(ypos + 100)
        # make sure that the format actually reflects the resolution of the frames on disk
        read_node.knob("reload").execute()
        return read_node

# makes a file path from a selected write node if it does not exist. bound to F8

def make_dir_path():
    file = ""
    # are we being called interactively, by the user hitting Ctrl+F8?
    if nuke.thisNode() == nuke.root():
        sel = None
        try:
            sel = nuke.selectedNodes()[0]
        except:
            print "WARNING: No nodes selected."
            return
        file = nuke.filename(sel)
    else:
        # nuke.filename(nuke.thisNode()) occasionally throws a RuntimeError exception when ran from the addBeforeRender() callback.
        # catch the exception and do not proceed when the exception is thrown.
        # added by Ned, 2016-01-27
        try:
            file = nuke.filename(nuke.thisNode())
        except RuntimeError as re:
            return
        except ValueError as ve:
            return
    
    
    config = get_config()
    cfg_sr_darwin = config.get('show_root', 'darwin')
    cfg_sr_thishost = config.get('show_root', sys.platform)
    
    newfile = ""
    
    if sys.platform == 'win32':
        newfile = file.replace(cfg_sr_darwin, cfg_sr_thishost).replace('/', '\\')
        file = newfile

    dir = os.path.dirname(file)
    osdir = dir
    
    # does NOT work if we are called from the command line
    # osdir = nuke.callbacks.filenameFilter(dir)
    if not os.path.exists(osdir):
        print "INFO: Creating directory at: %s" % osdir
        try:
            os.makedirs(osdir)
        except OSError as e:
            print "ERROR: os.makedirs() threw exception: %d" % e.errno
            print "ERROR: Filename: %s" % e.filename
            print "ERROR: Error String: %s" % e.strerror

# reveals the currently selected read or write node in the finder
# Tested and functional in Linux, 2016-10-01
# Not sure about Windows.

def reveal_in_finder():
    sel = None
    try:
        sel = nuke.selectedNode()
    except:
        print "WARN: No nodes selected."
        return
    if not sel.Class() == "Write" and not sel.Class() == "Read":
        print "WARN: Please select either a read or a write node."
        return
    file_path = sel.knob("file").evaluate()
    reveal_path = os.path.dirname(file_path)
    if os.path.splitext(file_path)[1] == ".mov":
        reveal_path = file_path
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", "-R", reveal_path])
    elif sys.platform == "linux2":
        subprocess.Popen(["/usr/bin/nautilus", "--browser", reveal_path])
    else:
        subprocess.Popen(["C:/Windows/explorer.exe", reveal_path])

class TimeCode():
    # no drop frame supported yet
    fps = 24.0
    hours = 0
    minutes = 0
    seconds = 0
    frames = 0
    frameno = 0

    def __init__(self, inputvalue, inputfps=None):
        if not inputfps == None:
            self.fps = float(inputfps)
        # looks like we are a frame number
        if isinstance(inputvalue, int) or isinstance(inputvalue, float):
            floatinputvalue = float(inputvalue)
            self.hours = int(floatinputvalue / 3600 / self.fps)
            self.minutes = int((floatinputvalue - (self.hours * 3600 * self.fps)) / 60 / self.fps)
            self.seconds = int(
                (floatinputvalue - (self.hours * 3600 * self.fps) - (self.minutes * 60 * self.fps)) / self.fps)
            self.frames = int(floatinputvalue - (self.hours * 3600 * self.fps) - (self.minutes * 60 * self.fps) - (
            self.seconds * self.fps))
            self.frameno = int(floatinputvalue)
        else:
            if inputvalue == "" or inputvalue == None:
                raise ValueError("TimeCode: Error: Timecode provided to constructor may not be blank or null.")
            input_list = inputvalue.split(':')
            if len(input_list) > 4:
                raise ValueError("TimeCode: Error: Timecode provided to constructor must be of the format HH:MM:SS:FF.")
            elif len(input_list) == 4:
                if int(input_list[3]) >= self.fps or int(input_list[3]) < 0:
                    raise ValueError(
                        "TimeCode: Error: Frames provided must not be greater than FPS rate of %d or less than zero." % self.fps)
                if int(input_list[2]) > 59 or int(input_list[2]) < 0:
                    raise ValueError("TimeCode: Error: Seconds provided must not be greater than 59 or less than zero.")
                if int(input_list[1]) > 59 or int(input_list[1]) < 0:
                    raise ValueError("TimeCode: Error: Minutes provided must not be greater than 59 or less than zero.")
                if int(input_list[0]) > 23 or int(input_list[0]) < 0:
                    raise ValueError("TimeCode: Error: Hours provided must not be greater than 23 or less than zero.")
                self.hours = int(input_list[0])
                self.minutes = int(input_list[1])
                self.seconds = int(input_list[2])
                self.frames = int(input_list[3])
            elif len(input_list) == 3:
                if int(input_list[2]) >= self.fps or int(input_list[2]) < 0:
                    raise ValueError(
                        "TimeCode: Error: Frames provided must not be greater than FPS rate of %d or less than zero." % self.fps)
                if int(input_list[1]) > 59 or int(input_list[1]) < 0:
                    raise ValueError("TimeCode: Error: Seconds provided must not be greater than 59 or less than zero.")
                if int(input_list[0]) > 59 or int(input_list[0]) < 0:
                    raise ValueError("TimeCode: Error: Minutes provided must not be greater than 59 or less than zero.")
                self.minutes = int(input_list[0])
                self.seconds = int(input_list[1])
                self.frames = int(input_list[2])
            elif len(input_list) == 2:
                if int(input_list[1]) >= self.fps or int(input_list[1]) < 0:
                    raise ValueError(
                        "TimeCode: Error: Frames provided must not be greater than FPS rate of %d or less than zero." % self.fps)
                if int(input_list[0]) > 59 or int(input_list[0]) < 0:
                    raise ValueError("TimeCode: Error: Seconds provided must not be greater than 59 or less than zero.")
                self.seconds = int(input_list[0])
                self.frames = int(input_list[1])
            elif len(input_list) == 1:
                if int(input_list[0]) >= self.fps or int(input_list[0]) < 0:
                    raise ValueError(
                        "TimeCode: Error: Frames provided must not be greater than FPS rate of %d or less than zero." % self.fps)
                self.frames = int(input_list[0])
            self.frameno = (self.hours * 3600 * self.fps) + (self.minutes * 60 * self.fps) + (
            self.seconds * self.fps) + self.frames

    def __str__(self):
        return "%02d:%02d:%02d:%02d" % (self.hours, self.minutes, self.seconds, self.frames)

    def __repr__(self):
        return "TimeCode(\"%02d:%02d:%02d:%02d\", inputfps=%d)" % (
        self.hours, self.minutes, self.seconds, self.frames, self.fps)

    def frame_number(self):
        return self.frameno

    def time_code(self):
        return "%02d:%02d:%02d:%02d" % (self.hours, self.minutes, self.seconds, self.frames)

    def __add__(self, inputobject):
        inttco = None
        if isinstance(inputobject, TimeCode):
            inttco = inputobject
        else:
            inttco = TimeCode(inputobject)
        newframeno = self.frameno + inttco.frameno
        numdays = int(newframeno / (24 * 3600 * inttco.fps))
        if numdays > 0:
            newframeno = newframeno - (numdays * 24 * 3600 * inttco.fps)
        rettco = TimeCode(newframeno)
        return rettco

    def __sub__(self, inputobject):
        inttco = None
        if isinstance(inputobject, TimeCode):
            inttco = inputobject
        else:
            inttco = TimeCode(inputobject)
        newframeno = self.frameno - inttco.frameno
        numdays = abs(int(newframeno / (24 * 3600 * inttco.fps)))
        if numdays > 0:
            newframeno = newframeno + (numdays * 24 * 3600 * inttco.fps)
        if newframeno < 0:
            newframeno = newframeno + (24 * 3600 * inttco.fps)
        rettco = TimeCode(newframeno)
        return rettco

def shot_from_script():
    script_name = nuke.root().knob('name').value()
    script_base = os.path.basename(script_name)
    shot = '_'.join(script_base.split('_')[0:2])
    return (shot)

def shot_from_nuke_path(str_path):
    config = get_config()
    cfg_shot_regexp = config.get(os.environ['IH_SHOW_CODE'], 'shot_regexp')

    rval = ""
    lst_path = str_path.split(os.path.sep)
    re_pattern = r'^%s$'%cfg_shot_regexp
    for path_component in lst_path:
        mo = re.search(re_pattern, path_component)
        if not mo == None:
            rval = path_component
    return rval

def cdl_file_from_nuke_path(str_path):
    config = get_config()
    cfg_shot_regexp = config.get(os.environ['IH_SHOW_CODE'], 'shot_regexp')
    rval = ""
    shot = shot_from_nuke_path(str_path)
    lst_path = str_path.split(os.path.sep)
    re_pattern = r'^%s$'%cfg_shot_regexp
    path_idx = 0
    for path_component in lst_path:
        path_idx += 1
        mo = re.search(re_pattern, path_component)
        if not mo == None:
            break
    return_path_lst = lst_path[0:path_idx]
    return_path_lst.extend(['data', 'cdl', '%s.cdl' % shot])
    rval = os.path.join(return_path_lst)
    return rval

def get_show_lut(str_path):
    config = get_config()
    cfg_lut = config.get(os.environ['IH_SHOW_CODE'], 'lut')

    rval = ""
    s_show_root = os.environ['IH_SHOW_ROOT']
    rval = os.path.join(s_show_root, "SHARED", "lut", cfg_lut)
    return rval

# The next two methods are designed to package Nuke scripts for stereo conversion.
# The first is designed to run in a separate thread so that it will not lock up the interface.
# The next should be referenced from within menu.py

def package_execute_threaded(s_nuke_script_path):

    progress_bar = nuke.ProgressTask("Packaging Script")
    progress_bar.setMessage("Initializing...")
    progress_bar.setProgress(0)
    
    s_nuke_exe_path = nuke.env['ExecutablePath']
    # package_script.py has NOT been cleaned of show-specific code and hard-coded paths. 
    # To-Do as of 2016-10-28.
    s_pyscript = os.path.join(os.path.dirname(os.environ['IH_SHOW_ROOT']), "SHARED", "lib", "nuke", "nuke_pipeline", "package_script.py")

    s_cmd = "%s -i -V 2 -t %s %s" % (s_nuke_exe_path, s_pyscript, s_nuke_script_path)
    s_err_ar = []
    f_progress = 0.0
    print "INFO: Beginning: %s" % s_cmd
    proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    while proc.poll() is None:
        try:
            s_out = proc.stdout.readline()
            print s_out.rstrip()
            s_err_ar.append(s_out.rstrip())
            if not s_out.find("INFO: copying file") == -1:
                s_line_ar = s_out.split(" ")
                (f_frame_cur, f_frame_tot, f_source_cur, f_source_tot) = (
                float(s_line_ar[3]), float(s_line_ar[5]), float(s_line_ar[8]), float(s_line_ar[10]))
                f_progress = ((f_frame_cur / f_frame_tot) * (1 / f_source_tot)) + ((f_source_cur - 1) / f_source_tot)
                progress_bar.setMessage("Copying: %s" % s_line_ar[-1])
                progress_bar.setProgress(int(f_progress * 100))
        except IOError:
            print "IOError Caught!"
            var = traceback.format_exc()
            print var
    if proc.returncode != 0:
        s_errmsg = ""
        s_err = '\n'.join(s_err_ar)
        if s_err.find("FOUNDRY LICENSE ERROR REPORT") != -1:
            s_errmsg = "Unable to obtain a license for Nuke! Package execution fails, will not proceed!"
        else:
            s_errmsg = "An unknown error has occurred. Please check the STDERR log above for more information."
        nuke.critical(s_errmsg)
    else:
        print "INFO: Successfully completed script packaging."

# add this one to menu.py
def menu_package_script():
    nuke.scriptSave()
    s_script_name = "%s" % nuke.scriptName()
    threading.Thread(target=package_execute_threaded, args=[s_script_name]).start()

def hsvToRGB(h, s, v):
    """Convert HSV color space to RGB color space
    @param h: Hue
    @param s: Saturation
    @param v: Value
    return (r, g, b)
    """
    hi = math.floor(h / 60.0) % 6
    f = (h / 60.0) - math.floor(h / 60.0)
    p = v * (1.0 - s)
    q = v * (1.0 - (f * s))
    t = v * (1.0 - ((1.0 - f) * s))
    return {
        0: (v, t, p),
        1: (q, v, p),
        2: (p, v, t),
        3: (p, q, v),
        4: (t, p, v),
        5: (v, p, q),
    }[hi]

def rgbToHSV(r, g, b):
    """Convert RGB color space to HSV color space
    @param r: Red
    @param g: Green
    @param b: Blue
    return (h, s, v)
    """
    maxc = max(r, g, b)
    minc = min(r, g, b)
    colorMap = {
        id(r): 'r',
        id(g): 'g',
        id(b): 'b'
    }
    if colorMap[id(maxc)] == colorMap[id(minc)]:
        h = 0
    elif colorMap[id(maxc)] == 'r':
        h = 60.0 * ((g - b) / (maxc - minc)) % 360.0
    elif colorMap[id(maxc)] == 'g':
        h = 60.0 * ((b - r) / (maxc - minc)) + 120.0
    elif colorMap[id(maxc)] == 'b':
        h = 60.0 * ((r - g) / (maxc - minc)) + 240.0

    v = maxc
    if maxc == 0.0:
        s = 0.0
    else:
        s = 1.0 - (minc / maxc)
    return (h, s, v)

def backdropColorOCD():
    nd_ar = []

    for nd in nuke.allNodes("BackdropNode"):
        nd_ar.append({'ypos': nd.knob("ypos").value(), 'node': nd})
    nd_ar_sorted = sorted(nd_ar, key=itemgetter('ypos'))
    hue_inc = 1.0 / (float(len(nd_ar_sorted)))
    hue_start = 0.0

    for nd in nd_ar_sorted:
        (a, b, c) = hsvToRGB((hue_start * 255), .5, .7)
        hx = "%02x%02x%02x%02x" % (a * 255, b * 255, c * 255, 255)
        nd['node'].knob("tile_color").setValue(int(hx, 16))
        # nd['node'].knob("note_font_size").setValue(100)
        hue_start += hue_inc
        
def build_cc_nodes():
    show_root = os.environ['IH_SHOW_ROOT']
    config = get_config()
    cfg_shot_regexp = config.get(os.environ['IH_SHOW_CODE'], 'shot_regexp')
    cfg_sequence_regexp = config.get(os.environ['IH_SHOW_CODE'], 'sequence_regexp')
    cfg_lut = config.get(os.environ['IH_SHOW_CODE'], 'lut')

    show_lut = os.path.join(show_root, "SHARED", "lut", cfg_lut)
    shot_re = re.compile(cfg_shot_regexp)
    seq_re = re.compile(cfg_seq_regexp)
    active_node = nuke.selectedNode()
    if active_node == None:
        nuke.critical("Please select either a Read or a Write node.")
        return
    if not active_node.Class() in ['Read', 'Write']:
        nuke.critical("Please select either a Read or a Write node.")
        return
    io_path = active_node.knob('file').value()
    
    c_shot_match = shot_re.search(io_path)
    c_shot = None
    if c_shot_match:
        c_shot = c_shot_match.group(0)
    else:
        nuke.critical("Can not find a valid shot name in file path for selected node.")
        return
    c_seq = seq_re.search(c_shot).group(0)
    cdl_path = os.path.join(show_root, c_seq, c_shot, "data", "cdl", "%s.cdl"%c_shot)
    if not os.path.exists(cdl_path):
        nuke.critical("Can not find a CDL file at %s."%cdl_path)
        return

    # create cdl nodes
    nd_cs1 = nuke.nodes.OCIOColorSpace()
    nd_cs1.knob("out_colorspace").setValue("AlexaV3LogC")
    nd_cs1.connectInput(0, active_node)
    nd_cdl = nuke.nodes.OCIOCDLTransform()
    nd_cdl.knob("read_from_file").setValue(True)
    nd_cdl.knob("file").setValue("%s"%cdl_path)
    nd_cdl.connectInput(0, nd_cs1)
    nd_lut = nuke.nodes.OCIOFileTransform()
    nd_lut.knob("file").setValue("%s"%show_lut)
    nd_lut.connectInput(0, nd_cdl)
    nd_cs2 = nuke.nodes.OCIOColorSpace()
    nd_cs2.knob("in_colorspace").setValue("rec709")
    nd_cs2.connectInput(0, nd_lut)

# method opens a count sheet for a shot.
# requires the following:
# * environment variable IH_SHOW_ROOT is defined
# * Nuke has an open script, which has txt_ih_seq and txt_ih_shot defined in the root
# * count sheets must be placed inside a shot folder in the data/count_sheet subfolder
    
def open_count_sheet():

    # method variables
    s_show_root = None
    s_seq = None
    s_shot = None
    
    # determine if we have a valid IH pipeline script open, and we are being executed within the IH pipeline.
    # basically, the environment variable IH_SHOW_ROOT must be defined, and the Nuke script must have txt_ih_seq
    # and txt_ih_shot defined in the root.
    try:
        s_show_root = os.environ['IH_SHOW_ROOT']
        s_seq = nuke.root().knob('txt_ih_seq').value()
        s_shot = nuke.root().knob('txt_ih_shot').value()
    except:
        nuke.critical('Method open_count_sheet() must be run while an In-House Nuke script is loaded.')
        return
    
    # build the count sheet directory based on values in the Nuke script and the system environment
    s_count_sheet_dir = os.path.join(s_show_root, s_seq, s_shot, "data", "count_sheets")
    print "INFO: Likely count sheet directory: %s"%s_count_sheet_dir
    if not os.path.exists(s_count_sheet_dir):
        nuke.critical("Count sheet directory at %s does not exist!"%s_count_sheet_dir)
        return
        
    # get all pdf files in the count sheet directory w/ modification times
    l_countsheets = [os.path.join(s_count_sheet_dir, fn) for fn in os.listdir(s_count_sheet_dir) if fn.endswith('.pdf')]
    
    # no count sheets exist? warn the user and exit.
    if len(l_countsheets) == 0:
        nuke.critical("No count sheets exist on the filesystem in directory %s."%s_count_sheet_dir)
        return
        
    # sort count sheets by modification time, descending
    l_counts_mtimes = [(os.stat(path)[ST_MTIME], path) for path in l_countsheets]
    l_counts_mtimes_sorted = sorted(l_counts_mtimes)
    
    # return the latest count sheet, based on file modification time
    s_latest_count_sheet = l_counts_mtimes_sorted[-1][1]
    print "INFO: Latest count sheet appears to be %s."%s_latest_count_sheet

    # finally, call the platform-specific method to open and display a count sheet in the GUI
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", s_latest_count_sheet])
    elif sys.platform == "linux2":
        subprocess.Popen(["/usr/bin/xdg-open", s_latest_count_sheet])
    else:
        subprocess.Popen(["START", "Count Sheet for shot %s"%s_shot, s_latest_count_sheet])

#### REMOVING ALL SHOW-SPECIFIC CODE FROM DELIVERIES

def get_client_version(db_version_name):
    global g_config
    show = os.environ['IH_SHOW_CODE']
    vsep = g_config.get(show, 'version_separator')
    cvformat = g_config.get('delivery', 'client_version_format')
    ret_string = None
    filename_re = re.compile(g_config.get(show, 'filename_regexp').replace('VERSION_SEPARATOR', vsep))
    filename_match = filename_re.search(db_version_name)
    if filename_match:
        filename_gd = filename_match.groupdict()
        ret_string = cvformat.format(shot = filename_gd['shot'], version_separator = vsep, version_number = filename_gd['version_number'], element_type = filename_gd['element_type'])
        return ret_string
    else:
        return None

# class displays a GUI asking the user for deliverable type selection and slate notes
class DeliveryNotesPanel(nukescripts.panels.PythonPanel):
    def __init__(self, review_notes='For Review'):
        nukescripts.PythonPanel.__init__(self, 'In-House Review Submission')
        self.cvn_knob = nuke.Multiline_Eval_String_Knob('cvn_', 'current version notes', review_notes)
        self.addKnob(self.cvn_knob)
        self.cc_knob = nuke.Boolean_Knob('cc_', 'CC', True)
        self.cc_knob.setFlag(nuke.STARTLINE)
        self.addKnob(self.cc_knob)
        self.avidqt_knob = nuke.Boolean_Knob('avidqt_', 'Avid Movie', True)
        self.addKnob(self.avidqt_knob)
        self.vfxqt_knob = nuke.Boolean_Knob('vfxqt_', 'VFX Movie', True)
        self.addKnob(self.vfxqt_knob)
        self.hires_knob = nuke.Boolean_Knob('hires_', 'Hi-Res', True)
        self.addKnob(self.hires_knob)
        self.burnin_knob = nuke.Boolean_Knob('burnin_', 'Movie Burnin', True)
        self.burnin_knob.setFlag(nuke.STARTLINE)
        self.addKnob(self.burnin_knob)
        self.matte_knob = nuke.Boolean_Knob('matte_', 'Matte', False)
        self.addKnob(self.matte_knob)
        self.export_knob = nuke.Boolean_Knob('export_', 'Export Movie', False)
        self.addKnob(self.export_knob)

# render a delivery in the background
def render_delivery_background(ms_python_script, d_db_thread_helper, start_frame, end_frame, md_filelist):
    global g_config, g_ihdb
    get_config()
    get_ihdb()
    str_show_code = os.environ['IH_SHOW_CODE']
    
    progress_bar = nuke.ProgressTask("Building Delivery")
    progress_bar.setMessage("Initializing...")
    progress_bar.setProgress(0)

    s_nuke_exe_path = g_config.get('nuke_exe_path', sys.platform)
    s_pyscript = ms_python_script
    s_windows_addl = ""
    l_win32_netpath_transforms = g_config.get(str_show_code, 'win32_netpath_transforms').split('|')
    if sys.platform == 'win32':
        s_windows_addl = ' --remap "%s,%s"'%(l_win32_netpath_transforms[0], l_win32_netpath_transforms[1])
    
    s_cmd = "%s -i -V 2%s -c 2G -t %s" % (s_nuke_exe_path, s_windows_addl, s_pyscript)
    s_cmd_ar = [s_nuke_exe_path, '-i', '-V', '2']
    if sys.platform == 'win32':
        s_cmd_ar.append('--remap')
        l_win32_netpath_transforms = g_config.get(str_show_code, 'win32_netpath_transforms').split('|')
        s_cmd_ar.append('"%s,%s"')%(l_win32_netpath_transforms[0], l_win32_netpath_transforms[1])

    s_cmd_ar.append('-c')
    s_cmd_ar.append('2G')
    s_cmd_ar.append('-t')
    s_cmd_ar.append(s_pyscript)
            
    s_err_ar = []
    f_progress = 0.0
    frame_match_txt = r'^Rendered frame (?P<frameno>[0-9]{1,}) of (?P<filebase>[a-zA-Z0-9-_]+)\.[0-9]*\.?[a-z]{3,4}\.$'
    frame_match_re = re.compile(frame_match_txt)
    print "INFO: Beginning: %s" % s_cmd
    proc = None

    if sys.platform == 'win32':
        print 'Windows detected. Passing array of command arguments and shell=False'
        proc = subprocess.Popen(s_cmd_ar, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        proc = subprocess.Popen(s_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    
    progress_bar.setMessage("Beginning Render.")
    b_kill = False
    while proc.poll() is None:
        if progress_bar.isCancelled():
            b_kill = True
            progress_bar.setMessage("Cancelling...")
            break
        try:
            s_out = proc.stdout.readline()
            s_err_ar.append(s_out.rstrip())
            matchobject = frame_match_re.search(s_out)
            if matchobject:
                s_hires_frame = matchobject.groupdict()['frameno']
                s_file_name = matchobject.groupdict()['filebase'].replace('_avid', '').replace('_vfx', '').replace('_export', '').replace('_matte', '')
                i_hires_frame = int(s_hires_frame)
                f_duration = float(end_frame - start_frame + 1)
                f_progress = (float(i_hires_frame) - float(start_frame) + 1.0)/f_duration
                progress_bar.setMessage("Rendering frame %d of %s..."%(i_hires_frame,s_file_name))
                progress_bar.setProgress(int(f_progress * 98))
        except IOError:
            print "ERROR: IOError Caught!"
            var = traceback.format_exc()
            nuke.critical(var)
            print var
            b_kill = True
    if b_kill:
        proc.kill()
        del progress_bar
        print "WARNING: User cancelled render operation."
        return
        
    if proc.returncode != 0:
        s_errmsg = ""
        s_err = '\n'.join(s_err_ar)
        l_err_verbose = []
        b_intrace = False
        for err_line in s_err_ar:
            if len(err_line) == 0:
                b_intrace = False
                continue
            if err_line.find("Traceback") != -1:
                b_intrace = True
            if err_line.find("ERROR") != -1:
                b_intrace = True
            if b_intrace:
                l_err_verbose.append(err_line)
        if s_err.find("FOUNDRY LICENSE ERROR REPORT") != -1:
            s_errmsg = "Unable to obtain a license for Nuke! Package execution fails, will not proceed!"
        else:
            s_errmsg = "Error(s) have occurred. Details:\n%s"%'\n'.join(l_err_verbose)
        nuke.critical(s_errmsg)
        print('Errors have occurred.')
        print(s_errmsg)
        del progress_bar
        return
    else:
        print "INFO: Successfully completed delivery render."

    mov_file = d_db_thread_helper['mov_src']
    thumb_file = d_db_thread_helper['exr_src'].replace('*', '%04d'%int(((int(end_frame) - int(start_frame))/2) + int(start_frame)))
    src_imgseq_path = d_db_thread_helper['exr_src'].replace('*', '%04d')
            
    # copy the files
    d_expanded_list = {}
    for s_src in md_filelist:
        if s_src.find('*') != -1:
            src_imgseq_path = s_src.replace('*', '%04d')
            l_imgseq = glob.glob(s_src)
            for s_img in l_imgseq:
                d_expanded_list[s_img] = os.path.join(md_filelist[s_src], os.path.basename(s_img))
        else:
            d_expanded_list[s_src] = md_filelist[s_src]
            
    i_len = len(d_expanded_list.keys())
    # copy all of the files to the destination volume.
    # alert the user if anything goes wrong.
    try:
        for i_count, source_file in enumerate(d_expanded_list.keys(), start=1):
            progress_bar.setMessage("Copying: %s"%os.path.basename(source_file))
            if not os.path.exists(os.path.dirname(d_expanded_list[source_file])):
                os.makedirs(os.path.dirname(d_expanded_list[source_file]))
            shutil.copy(source_file, d_expanded_list[source_file])
            f_progress = float(i_count)/float(i_len)
            progress_bar.setProgress(98 + int(f_progress * 98))
    except:
        nuke.critical(traceback.format_exc())
    else:
        # add a new version to the database
        progress_bar.setProgress(99)
        progress_bar.setMessage("Creating new Version record in the database...")
        
        # fetch the shot from the thread helper dictionary
        dbshot = d_db_thread_helper['dbshot']
        
        # fetch the artist from the thread helper dictionary
        dbartist = d_db_thread_helper['dbartist']

        # get a name for the version, will use this to find the right comp task
        tmp_version_name = os.path.basename(thumb_file).split('.')[0]

        # is this a temp version?
        tmp_re = re.compile(g_config.get(str_show_code, 'temp_element_regexp'))
        b_istemp = False
        if tmp_re.search(tmp_version_name):
            b_istemp = True

        # fetch a list of tasks for the shot
        dbtasks = g_ihdb.fetch_tasks_for_shot(dbshot)
        # If no tasks have been created for this shot, use a blank task
        dbtask = DB.Task("Blank Task", dbartist, 'wtg', dbshot, -1)
        temp_task_name = g_config.get('scan_ingest', 'temp_comp_task_name')
        final_task_name = g_config.get('scan_ingest', 'final_comp_task_name')
        tmptask = None
        finaltask = None
        for tmp_dbtask in dbtasks:
            print "DEBUG: Got task for shot: %s"%tmp_dbtask.g_task_name
            if tmp_dbtask.g_task_name == temp_task_name:
                tmptask = tmp_dbtask
            elif tmp_dbtask.g_task_name == final_task_name:
                finaltask = tmp_dbtask

        if b_istemp:
            if tmptask:
                print "DEBUG: Assigning task for version: %s"%tmptask.g_task_name
                dbtask = tmptask
        else:
            if finaltask:
                print "DEBUG: Assigning task for version: %s"%finaltask.g_task_name
                dbtask = finaltask

        # create a thumbnail
        b_apply_cc = True
        if b_istemp:
            b_apply_cc = False

        thumb_file_gen = os_path_sub(create_thumbnail(thumb_file, b_applycc=b_apply_cc))
        
        # does the version already exist?
        print "Thread: %s Fetching version for %s, for shot %s"%(threading.current_thread().getName(), tmp_version_name, d_db_thread_helper['shot'])
        dbversion = g_ihdb.fetch_version(tmp_version_name, dbshot)
        
        # clean up notes
        l_notes = d_db_thread_helper['notes']
        clean_notes = []
        for l_note in l_notes:
            if len(l_note) > 0:
                clean_notes.append(l_note)
        if not dbversion:
            print "Thread: %s Creating version for %s, for shot %s"%(threading.current_thread().getName(), tmp_version_name, d_db_thread_helper['shot'])
            dbversion = DB.Version(tmp_version_name, 
                                     -1, 
                                     '\n'.join(clean_notes), 
                                     int(start_frame), 
                                     int(end_frame), 
                                     int(end_frame) - int(start_frame) + 1, 
                                     d_db_thread_helper['hires_dest'], 
                                     d_db_thread_helper['mov_dest'],
                                     dbshot,
                                     dbartist,
                                     dbtask)
            dbversion.set_status(g_config.get('delivery', 'version_status_qt'))
            dbversion.set_delivered(False)
            dbversion.set_client_code(get_client_version(tmp_version_name))
            if d_db_thread_helper['matte_dest']:
                dbversion.set_path_to_matte_frames(d_db_thread_helper['matte_dest'])
                dbversion.set_matte_ready(True)
                dbversion.set_matte_only(d_db_thread_helper['matte_only'])
                dbversion.set_matte_delivered(False)
            g_ihdb.create_version(dbversion)
            print "Successfully created version %s in database with DBID %d."%(dbversion.g_version_code, int(dbversion.g_dbid))
        else:
            dbversion_upd = DB.Version(tmp_version_name, 
                                     dbversion.g_dbid, 
                                     '\n'.join(clean_notes), 
                                     int(start_frame), 
                                     int(end_frame), 
                                     int(end_frame) - int(start_frame) + 1, 
                                     d_db_thread_helper['hires_dest'], 
                                     d_db_thread_helper['mov_dest'],
                                     dbshot,
                                     dbartist,
                                     dbtask)
            dbversion_upd.set_status(g_config.get('delivery', 'version_status_qt'))
            dbversion_upd.set_delivered(False)
            dbversion_upd.set_client_code(get_client_version(tmp_version_name))
            if d_db_thread_helper['matte_dest']:
                dbversion_upd.set_path_to_matte_frames(d_db_thread_helper['matte_dest'])
                dbversion_upd.set_matte_ready(True)
                dbversion_upd.set_matte_only(d_db_thread_helper['matte_only'])
                dbversion_upd.set_matte_delivered(False)
                dbversion.set_path_to_matte_frames(d_db_thread_helper['matte_dest'])
                dbversion.set_matte_ready(True)
                dbversion.set_matte_only(d_db_thread_helper['matte_only'])
                dbversion.set_matte_delivered(False)
            dbversion.set_status(g_config.get('delivery', 'version_status_qt'))
            dbversion.set_delivered(False)
            dbversion.set_client_code(get_client_version(tmp_version_name))
            g_ihdb.update_version(dbversion_upd)
            print "Successfully updated version %s in database with DBID %d."%(dbversion.g_version_code, int(dbversion.g_dbid))
        
        if not d_db_thread_helper['matte_only']:    
            g_ihdb.upload_thumbnail('Version', dbversion, thumb_file_gen)
            # should we upload a movie file for this version? Check in the config to see...
            b_upload_movie = False
            try:
                upload_movie_from_config = g_config.get('delivery', 'upload_movie')
                if upload_movie_from_config in ['Yes', 'YES', 'Y', 'y', 'True', 'TRUE', 'true']:
                    b_upload_movie = True
            except ConfigParser.NoOptionError as e:
                print "ERROR: Config File is missing an option!"
                print e.message
                nuke.message("The show configuration file is missing an option! Specifically:\n%s"%e.message)
            if b_upload_movie:
                print "INFO: About to upload: %s"%d_db_thread_helper['export_dest']
                if os.path.exists(d_db_thread_helper['export_dest']):
                    g_ihdb.upload_movie('Version', dbversion, d_db_thread_helper['export_dest'])
                else:
                    print("Warning: delivery : upload_movie is set to True in the config file, but movie file %s does not exist."%d_db_thread_helper['export_dest'])
                print "INFO: Done."
            g_ihdb.upload_thumbnail('Shot', dbshot, thumb_file_gen)
            dbtask.g_status = g_config.get('delivery', 'version_status_qt')
            print "Thread: %s Setting task status for task %s, shot %s to %s"%(threading.current_thread().getName(), dbtask.g_task_name, d_db_thread_helper['shot'], dbtask.g_status)
            g_ihdb.update_task_status(dbtask)
            progress_bar.setMessage("Publishing Nuke Script and Hi-Res Frames to Database...")

            dbpublish = None
            # call the publish method from the DBAccess class...
            dbpublish = g_ihdb.publish_for_shot(dbshot, d_db_thread_helper['hires_dest'], clean_notes)
            if dbpublish:
                g_ihdb.upload_thumbnail('PublishedFile', dbshot, thumb_file_gen, altid = dbpublish['id'])
        
            s_nuke_script_path = d_db_thread_helper['nuke_script_path']
            if not s_nuke_script_path == 'UNKNOWN':
                dbpublishnk = g_ihdb.publish_for_shot(dbshot, s_nuke_script_path, clean_notes)
                if dbpublishnk:
                    g_ihdb.upload_thumbnail('PublishedFile', dbshot, thumb_file_gen, altid = dbpublishnk['id'])
        progress_bar.setProgress(100)
        progress_bar.setMessage("Done!")

    del progress_bar

# send a shot for review
def send_for_review(cc=True, current_version_notes=None, b_method_avidqt=True, b_method_vfxqt=True, b_method_burnin=True, b_method_hires=True, b_method_export=False, b_method_matte=False, b_method_artist=None):

    global g_config, g_ihdb
    if g_config == None:
        get_config()
    get_ihdb()
    
    oglist = []
    vfxqt_delivery = b_method_vfxqt

    s_show_root = os.environ['IH_SHOW_ROOT']
    s_show = os.environ['IH_SHOW_CODE']
    # win32 path replacement
    tmp_path_repl = g_config.get(s_show, 'win32_netpath_transforms')
    d_path_repl = { 'posixpath' : tmp_path_repl.split('|')[0], 'win32path' : tmp_path_repl.split('|')[1] }
    
    # use plate TimeCode?
    b_use_platetc = True
    if g_config.get(s_show, 'use_plate_timecode') in ['no', 'NO', 'No', 'N', 'n', 'False', 'FALSE', 'false']:
        b_use_platetc = False

    s_delivery_fileext = g_config.get('delivery', 'file_format')

    for nd in nuke.selectedNodes():
        nd.knob('selected').setValue(False)
        oglist.append(nd)

    start_frame = nuke.root().knob('first_frame').value()
    end_frame = nuke.root().knob('last_frame').value()
    
    global_width = nuke.root().knob('format').value().width()
    global_height = nuke.root().knob('format').value().height()

    for und in oglist:
        created_list = []
        write_list = []
        render_path = ""
        md_host_name = None
        first_frame_tc_str = ""
        last_frame_tc_str = ""
        first_frame_tc = None
        last_frame_tc = None
        slate_frame_tc = None

        if und.Class() == "Read":
            print "INFO: Located Read Node."
            und.knob('selected').setValue(True)
            render_path = und.knob('file').value()
            start_frame = und.knob('first').value()
            end_frame = und.knob('last').value()
            global_width = und.knob('format').value().width()
            global_height = und.knob('format').value().height()
            startNode = und
        elif und.Class() == "Write":
            print "INFO: Located Write Node."
            # make sure this Write node has been rendered
            write_file_path = und.knob('file').value()
            write_path_list = write_file_path.split('.')
            norender = False
            if not os.path.exists(os.path.dirname(write_file_path)):
                norender = True
            if len(write_path_list) > 2:
                frame_num = write_path_list[-2]
                glob_path = write_file_path.replace(frame_num, '*')
                write_frames = glob.glob(glob_path)
                if len(write_frames) == 0:
                    norender = True
            else:
                if not os.path.exists(write_file_path):
                    norender = True

            if norender:
                nuke.critical('The Write node you selected has not been rendered yet.')
                return
                
                
            und.knob('selected').setValue(True)
            global_width = und.knob('format').value().width()
            global_height = und.knob('format').value().height()
            new_read = read_from_write()
            render_path = new_read.knob('file').value()
            start_frame = new_read.knob('first').value()
            end_frame = new_read.knob('last').value()
            created_list.append(new_read)
            startNode = new_read
        else:
            print "Please select either a Read or Write node"
            break
        if sys.platform == "win32":
            render_path = render_path.replace(d_path_repl['posixpath'], d_path_repl['win32path'])
        
        first_frame_tc_str = None
        last_frame_tc_str = None
        if b_use_platetc:
            # timecode from start frame (1001 = 00:00:41:17) and end frame
            first_frame_tc_str = startNode.metadata("input/timecode", float(start_frame))
            last_frame_tc_str = startNode.metadata("input/timecode", float(end_frame))
        else:
            # timecode from start frame (1001 = 00:00:41:17) and end frame
            first_frame_tc_str = str(TimeCode(start_frame))
            last_frame_tc_str = str(TimeCode(end_frame))
            
        if first_frame_tc_str == None:
            first_frame_tc = TimeCode(start_frame)
        else:
            first_frame_tc = TimeCode(first_frame_tc_str)
        slate_frame_tc = first_frame_tc - 1
        if last_frame_tc_str == None:
            last_frame_tc = TimeCode(end_frame) + 1
        else:
            last_frame_tc = TimeCode(last_frame_tc_str) + 1

        # grab the shot from the filename and database
        s_shot = None
        s_sequence = None
        
        g_shot_regexp = g_config.get(s_show, 'shot_regexp')
        matchobject = re.search(g_shot_regexp, render_path)
        # make sure this file matches the shot pattern
        if not matchobject:
            print "ERROR: somehow render path %s doesn't actually contain a shot!"%render_path
            continue
        else:
            s_shot = matchobject.groupdict()['shot']
            s_sequence = matchobject.groupdict()['sequence']
        
        d_shot_path = { 'show_root' : s_show_root, 'sequence' : s_sequence, 'shot' : s_shot, 'pathsep' : os.path.sep }
        s_shot_path = g_config.get(s_show, 'shot_dir_format').format(**d_shot_path)
        s_seq_path = g_config.get(s_show, 'seq_dir_format').format(**d_shot_path)
        # create the panel to ask for notes
        def_note_text = "For review"
        path_dir_name = os.path.dirname(render_path)
        version_int = 0
        try:
            version_int = int(path_dir_name.split(g_config.get(s_show, 'version_separator'))[-1])
        except ValueError:
            pass
        if version_int == int(g_config.get(s_show, 'version_start')) - 1:
            def_note_text = "Scan Verification."

        dbshot = g_ihdb.fetch_shot(s_shot)
            
        b_execute_overall = False
        b_matte_only = False
        cc_delivery = False
        burnin_delivery = False
        export_delivery = False
        tmp_versions = g_ihdb.fetch_versions_for_shot(dbshot)
        versions_list = sorted(tmp_versions, key=attrgetter('g_version_code'))
        if versions_list and len(versions_list) > 0:
            def_note_text = versions_list[-1].g_description

        # are we running this from a Python console?
        if current_version_notes is not None:
            cvn_txt = current_version_notes
            avidqt_delivery = b_method_avidqt
            vfxqt_delivery = b_method_vfxqt
            burnin_delivery = b_method_burnin
            hires_delivery = b_method_hires
            matte_delivery = b_method_matte
            export_delivery = b_method_export
            cc_delivery = cc
            b_execute_overall = True
        else:
            pnl = DeliveryNotesPanel()
            pnl.knobs()['cvn_'].setValue(def_note_text)
            pnl.knobs()['cc_'].setValue(cc)
            pnl.knobs()['avidqt_'].setValue(b_method_avidqt)
            pnl.knobs()['vfxqt_'].setValue(b_method_vfxqt)
            pnl.knobs()['burnin_'].setValue(b_method_burnin)
            pnl.knobs()['hires_'].setValue(b_method_hires)
            pnl.knobs()['matte_'].setValue(b_method_matte)
            pnl.knobs()['export_'].setValue(b_method_export)
            
            if pnl.showModalDialog():
                cvn_txt = pnl.knobs()['cvn_'].value()
                cc_delivery = pnl.knobs()['cc_'].value()
                avidqt_delivery = pnl.knobs()['avidqt_'].value()
                vfxqt_delivery = pnl.knobs()['vfxqt_'].value()
                burnin_delivery = pnl.knobs()['burnin_'].value()
                hires_delivery = pnl.knobs()['hires_'].value()
                matte_delivery = pnl.knobs()['matte_'].value()
                export_delivery = pnl.knobs()['export_'].value()
                b_execute_overall = True

        if b_execute_overall:
        
            if matte_delivery and not avidqt_delivery and not vfxqt_delivery and not hires_delivery and not export_delivery:
                b_matte_only = True
                
            # submission reason
            submission_reason = "For Review"
            if hires_delivery:
                submission_reason = g_config.get('delivery', 'hires_subreason')
            else:
                if avidqt_delivery:
                    submission_reason = g_config.get('delivery', 'lores_subreason')
                else:
                    if matte_delivery:
                        submission_reason = g_config.get('delivery', 'matte_subreason')
                        
            # project FPS
            s_project_fps = g_config.get(s_show, 'write_fps')
            # delivery template
            s_delivery_template = g_config.get('delivery', 'nuke_template_%s'%sys.platform)

            s_filename = os.path.basename(render_path).split('.')[0]
            s_client_version = get_client_version(s_filename)
            for tmp_dbv in versions_list:
                tmp_cv = tmp_dbv.g_client_code
                if not tmp_cv:
                    tmp_cv = get_client_version(tmp_dbv.g_version_code)
                if tmp_cv == None:
                    print('Warning: Unable to retrieve a client version name for database version %s. This means that the version name does not match the approved naming convention for the show.'%tmp_dbv.g_version_code)
                else:
                    if tmp_cv == s_client_version and tmp_dbv.g_delivered:
                        nuke.critical("This version has already been delivered to production as %s! Please upversion your Nuke script, re-render, and resubmit."%s_client_version)
                        return
            s_cdl_file_ext = g_config.get(s_show, 'cdl_file_ext')
            

            # new delivery folder: $SHOT/delivery
            s_delivery_folder = os.path.join(s_shot_path, g_config.get(s_show, 'shot_delivery_dir'), s_filename)
            s_likely_nuke_script_path = os.path.join(s_shot_path, g_config.get(s_show, 'shot_scripts_dir'), '%s.nk'%s_filename)
            s_nuke_script_path = 'UNKNOWN'
            if os.path.exists(s_likely_nuke_script_path):
                s_nuke_script_path = s_likely_nuke_script_path
            
            # allow version number to have arbitrary text after it, such as "_matte" or "_temp"
            s_version = s_filename.split(g_config.get(s_show, 'version_separator'))[-1].split('_')[0]
            s_artist_name = None
            s_artist_login = get_login()
            
            if b_method_artist:
                s_artist_login = b_method_artist


            dbartist = g_ihdb.fetch_artist_from_username(s_artist_login)
            s_artist_name = dbartist.g_full_name
            
            # this will vary based on camera format, so, pull the default from the config file, and then try and get the right one from the read node
            s_format = g_config.get(s_show, 'delivery_resolution')
            tmp_width = startNode.knob('format').value().width()
            tmp_height = startNode.knob('format').value().height()
            s_format = "%sx%s"%(tmp_width, tmp_height)
            
            # notes
            l_notes = ["", "", "", "", ""]
            for idx, s_note in enumerate(cvn_txt.split('\n'), start=0):
                if idx >= len(l_notes):
                    break
                l_notes[idx] = s_note
                
            b_deliver_cdl = True

            # exr source: the rendered comp
            s_exr_src = os.path.join(os.path.dirname(render_path), "%s.*.exr"%s_filename).replace('\\', '/')
            s_delivery_package = 'NOPKG'
            
            # various destinations
            s_avidqt_dest = os.path.join(s_delivery_folder, 'mov', '%s_avid.mov'%s_filename)
            s_vfxqt_dest = os.path.join(s_delivery_folder, 'mov', '%s_vfx.mov'%s_filename)
            s_exportqt_dest = os.path.join(s_delivery_folder, 'mov', '%s_export.mov'%s_filename)
            s_dpx_dest = os.path.join(s_delivery_folder, 'dpx', "%s.*.dpx"%s_filename)
            s_exr_dest = os.path.join(s_delivery_folder, 'exr', "%s.*.exr"%s_filename)
            # matte file extension - some shows don't use TIFF
            s_matte_fileext = g_config.get('delivery', 'matte_file_format')
            s_matte_dest = os.path.join(s_delivery_folder, 'matte', "%s_matte.*.%s"%(s_filename, s_matte_fileext))
            s_xml_dest = os.path.join(s_delivery_folder, 'support_files', "%s.xml"%s_filename)
            all_dests = [s_avidqt_dest, s_vfxqt_dest, s_exportqt_dest, s_xml_dest]
            if hires_delivery:
                if s_delivery_fileext == 'exr':
                    all_dests.append(s_exr_dest)
                elif s_delivery_fileext == 'dpx':
                    all_dests.append(s_dpx_dest)
            if matte_delivery:
                all_dests.append(s_matte_dest)
            for dest in all_dests:
                dir = os.path.dirname(dest)
                if not os.path.exists(dir):
                    os.makedirs(dir)
           
            d_db_thread_helper = {}
            d_db_thread_helper['exr_src'] = s_exr_src
            d_db_thread_helper['mov_src'] = s_avidqt_dest
            d_db_thread_helper['mov_dest'] = s_avidqt_dest
            d_db_thread_helper['export_dest'] = s_exportqt_dest
            d_db_thread_helper['dbartist'] = dbartist
            d_db_thread_helper['dbshot'] = dbshot
            d_db_thread_helper['nuke_script_path'] = s_nuke_script_path
            d_db_thread_helper['matte_only'] = b_matte_only
            if matte_delivery:
                d_db_thread_helper['matte_dest'] = s_matte_dest
            else:
                d_db_thread_helper['matte_dest'] = None
 
            if s_delivery_fileext == 'dpx':
                d_db_thread_helper['hires_dest'] = s_dpx_dest.replace('*', '%04d')
            else:
                d_db_thread_helper['hires_dest'] = s_exr_dest.replace('*', '%04d')
            
            d_db_thread_helper['shot'] = s_shot
            d_db_thread_helper['notes'] = l_notes
            
            
            d_files_to_copy = {}
            
            # copy CDL file into delivery folder
            s_cdl_dir = g_config.get(s_show, 'cdl_dir_format').format(pathsep = os.path.sep)
            s_cdl_src = os.path.join(s_shot_path, s_cdl_dir, "%s.%s"%(s_shot,s_cdl_file_ext))
            s_cdl_dest = os.path.join(s_delivery_folder, 'support_files', "%s.%s"%(s_shot,s_cdl_file_ext))
            b_shot_lut_is_cdl = False
            if s_cdl_file_ext.lower() in ['cc','ccc','cdl']:
                b_shot_lut_is_cdl = True

            if not os.path.exists(s_cdl_src):
                print "WARNING: Unable to locate %s file at: %s"%(s_cdl_file_ext.upper(), s_cdl_src)
                b_deliver_cdl = False
                cc_delivery = False
            else:
                # only do this if the CC file is a CDL,CC,CCC
                if b_shot_lut_is_cdl:
                    # open up the cdl and extract the cccid
                    cdltext = open(s_cdl_src, 'r').read()
                    cccid_re_str = r'<ColorCorrection id="([A-Za-z0-9-_]+)">'
                    cccid_re = re.compile(cccid_re_str)
                    cccid_match = cccid_re.search(cdltext)
                    if cccid_match:
                        s_cccid = cccid_match.group(1)
                    else:
                        s_cccid = s_shot

                    # slope
                    slope_re_str = r'<Slope>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Slope>'
                    slope_re = re.compile(slope_re_str)
                    slope_match = slope_re.search(cdltext)
                    if slope_match:
                        slope_r = slope_match.group(1)
                        slope_g = slope_match.group(2)
                        slope_b = slope_match.group(3)
                    else:
                        nuke.critical("Unable to locate <Slope> tag inside CDL.")
                        return

                    # offset
                    offset_re_str = r'<Offset>([0-9.-]+e?[0-9-]*) ([0-9.-]+e?[0-9-]*) ([0-9.-]+e?[0-9-]*)</Offset>'
                    offset_re = re.compile(offset_re_str)
                    offset_match = offset_re.search(cdltext)
                    if offset_match:
                        offset_r = offset_match.group(1)
                        offset_g = offset_match.group(2)
                        offset_b = offset_match.group(3)
                    else:
                        nuke.critical("Unable to locate <Offset> tag inside CDL.")
                        return

                    # power
                    power_re_str = r'<Power>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Power>'
                    power_re = re.compile(power_re_str)
                    power_match = power_re.search(cdltext)
                    if power_match:
                        power_r = power_match.group(1)
                        power_g = power_match.group(2)
                        power_b = power_match.group(3)
                    else:
                        nuke.critical("Unable to locate <Power> tag inside CDL.")
                        return

                    # saturation
                    saturation_re_str = r'<Saturation>([0-9.-]+)</Saturation>'
                    saturation_re = re.compile(saturation_re_str)
                    saturation_match = saturation_re.search(cdltext)
                    if saturation_match:
                        saturation = saturation_match.group(1)
                    else:
                        nuke.critical("Unable to locate <Saturation> tag inside CDL.")
                        return
            
            # print out python script to a temp file
            fh_nukepy, s_nukepy = tempfile.mkstemp(suffix='.py')
            
            os.write(fh_nukepy, "#!/usr/bin/python\n")
            os.write(fh_nukepy, "\n")
            os.write(fh_nukepy, "import nuke\n")
            os.write(fh_nukepy, "import os\n")
            os.write(fh_nukepy, "import sys\n")
            os.write(fh_nukepy, "import traceback\n")
            os.write(fh_nukepy, "\n")
            if sys.platform == 'win32':
                s_delivery_template = s_delivery_template.replace('\\', '\\\\')
            os.write(fh_nukepy, "nuke.scriptOpen(\"%s\")\n"%s_delivery_template)
            os.write(fh_nukepy, "nd_root = root = nuke.root()\n")
            os.write(fh_nukepy, "\n")
            os.write(fh_nukepy, "# set root frame range\n")
            os.write(fh_nukepy, "nd_root.knob('first_frame').setValue(%d)\n"%start_frame)
            os.write(fh_nukepy, "nd_root.knob('last_frame').setValue(%d)\n"%end_frame)
            
            # set the format in both the read node and the project settings
            fstring = '%d %d Submission Format'%(tmp_width, tmp_height)
            os.write(fh_nukepy, "fobj = nuke.addFormat('%s')\n"%fstring)
            os.write(fh_nukepy, "nuke.root().knob('format').setValue(fobj)\n")
            os.write(fh_nukepy, "nuke.root().knob('format').setValue(fobj)\n")

            # allow user to disable color correction, usually for temps
            if not cc_delivery:
                os.write(fh_nukepy, "nd_root.knob('nocc').setValue(True)\n")
            else:
                os.write(fh_nukepy, "nd_root.knob('nocc').setValue(False)\n")

            os.write(fh_nukepy, "\n")
            os.write(fh_nukepy, "nd_read = nuke.toNode('%s')\n"%g_config.get('delivery', 'exr_read_node'))
            os.write(fh_nukepy, "nd_read.knob('file').setValue(\"%s\")\n"%render_path)
            os.write(fh_nukepy, "nd_read.knob('first').setValue(%d)\n"%start_frame)
            os.write(fh_nukepy, "nd_read.knob('last').setValue(%d)\n"%end_frame)
            os.write(fh_nukepy, "nd_read.knob('format').setValue(fobj)\n")

            os.write(fh_nukepy, "nd_root.knob('ti_ih_file_name').setValue(\"%s\")\n"%s_filename)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_sequence').setValue(\"%s\")\n"%s_sequence)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_shot').setValue(\"%s\")\n"%s_shot)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_version').setValue(\"%s\")\n"%s_version)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_vendor').setValue(\"%s\")\n"%s_artist_name)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_format').setValue(\"%s\")\n"%s_format)
            os.write(fh_nukepy, "nd_root.knob('ti_submission_reason').setValue(\"%s\")\n"%submission_reason)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_notes_1').setValue(\"%s\")\n"%l_notes[0].replace(r'"', r'\"'))
            os.write(fh_nukepy, "nd_root.knob('ti_ih_notes_2').setValue(\"%s\")\n"%l_notes[1].replace(r'"', r'\"'))
            os.write(fh_nukepy, "nd_root.knob('ti_ih_notes_3').setValue(\"%s\")\n"%l_notes[2].replace(r'"', r'\"'))
            os.write(fh_nukepy, "nd_root.knob('ti_ih_notes_4').setValue(\"%s\")\n"%l_notes[3].replace(r'"', r'\"'))
            os.write(fh_nukepy, "nd_root.knob('ti_ih_notes_5').setValue(\"%s\")\n"%l_notes[4].replace(r'"', r'\"'))
            if sys.platform == 'win32':
                s_delivery_folder = s_delivery_folder.replace('\\', '/')
                s_show_root = s_show_root.replace('\\', '/')
                s_seq_path = s_seq_path.replace('\\', '/')
                s_shot_path = s_shot_path.replace('\\', '/')
            os.write(fh_nukepy, "nd_root.knob('ti_ih_delivery_folder').setValue(\"%s\")\n"%s_delivery_folder)
            os.write(fh_nukepy, "nd_root.knob('ti_ih_delivery_package').setValue(\"%s\")\n"%s_delivery_package)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_show').setValue(\"%s\")\n"%s_show)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_show_path').setValue(\"%s\")\n"%s_show_root)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_seq').setValue(\"%s\")\n"%s_sequence)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_seq_path').setValue(\"%s\")\n"%s_seq_path)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_shot').setValue(\"%s\")\n"%s_shot)
            os.write(fh_nukepy, "nd_root.knob('txt_ih_shot_path').setValue(\"%s\")\n"%s_shot_path)
            # encode with proper timecode
            for tcnode in g_config.get('delivery', 'timecode_nodes').split(','):
                if len(tcnode) > 0:
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('startcode').setValue(\"%s\")\n"%(tcnode, first_frame_tc_str))
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('frame').setValue(%s)\n"%(tcnode, start_frame))
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('fps').setValue(%s)\n"%(tcnode, s_project_fps))

            if not burnin_delivery:
                os.write(fh_nukepy, "nd_root.knob('noburnin').setValue(True)\n")

            if export_delivery:
                os.write(fh_nukepy, "nd_root.knob('exportburnin').setValue(True)\n")

            if not cc_delivery:
                for csnode in g_config.get('delivery', 'colorspace_nodes').split(','):
                    if len(csnode) > 0:
                        os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%csnode)
                for cdlnode in g_config.get('delivery', 'cdl_nodes').split(','):
                    if len(cdlnode) > 0:
                        os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%cdlnode)
                for lutnode in g_config.get('delivery', 'lut_nodes').split(','):
                    if len(lutnode) > 0:
                        os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%lutnode)
                for shotlutnode in g_config.get('delivery', 'shot_lut_nodes').split(','):
                    if len(shotlutnode) > 0:
                        os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n" % shotlutnode)
                for otherccnode in g_config.get('delivery', 'other_cc_nodes').split(','):
                    if len(otherccnode) > 0:
                        os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n" % otherccnode)
            else:
                # hard code cdl values
                if sys.platform == 'win32':
                    s_cdl_src = s_cdl_src.replace('\\', '/')
                    tmp_lut = os.environ['IH_SHOW_CFG_LUT'].replace('\\', '/')
                    for lutnode in g_config.get('delivery', 'lut_nodes').split(','):
                        if len(lutnode) > 0:
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('vfield_file').setValue(\"%s\")\n"%(lutnode, tmp_lut))
                if b_shot_lut_is_cdl:
                    for cdlnode in g_config.get('delivery', 'cdl_nodes').split(','):
                        if len(cdlnode) > 0:
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue(\"%s\")\n"%(cdlnode, s_cdl_src))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('cccid').setValue(\"%s\")\n"%(cdlnode, s_cccid))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('read_from_file').setValue(False)\n"%(cdlnode))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('slope').setValue([%s, %s, %s])\n"%(cdlnode, slope_r, slope_g, slope_b))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('offset').setValue([%s, %s, %s])\n"%(cdlnode, offset_r, offset_g, offset_b))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('power').setValue([%s, %s, %s])\n"%(cdlnode, power_r, power_g, power_b))
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('saturation').setValue(%s)\n"%(cdlnode, saturation))
                else:
                    for shotlutnode in g_config.get('delivery', 'shot_lut_nodes').split(','):
                        if len(shotlutnode) > 0:
                            os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue(\"%s\")\n" % (shotlutnode, s_cdl_src))
            
            l_exec_nodes = []
            s_hires_node = None
            
            if not avidqt_delivery:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%g_config.get('delivery', 'avid_write_node'))
            else:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'avid_write_node'), s_avidqt_dest))
                l_exec_nodes.append(g_config.get('delivery', 'avid_write_node'))
            
            if not vfxqt_delivery or sys.platform == 'win32':
                os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%g_config.get('delivery', 'vfx_write_node'))
            else:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'vfx_write_node'), s_vfxqt_dest))
                l_exec_nodes.append(g_config.get('delivery', 'vfx_write_node'))

            if not export_delivery:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%g_config.get('delivery', 'export_write_node'))
            else:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'export_write_node'), s_exportqt_dest))
                l_exec_nodes.append(g_config.get('delivery', 'export_write_node'))
            
            if not hires_delivery:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%g_config.get('delivery', 'hires_write_node'))
                b_deliver_cdl = False
            else:
                if s_delivery_fileext == 'exr':
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'hires_write_node'), s_exr_dest.replace('*', '%04d')))
                if s_delivery_fileext == 'dpx':
                    os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'hires_write_node'), s_dpx_dest.replace('*', '%04d')))
                l_exec_nodes.append(g_config.get('delivery', 'hires_write_node'))

            if not matte_delivery:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('disable').setValue(True)\n"%g_config.get('delivery', 'matte_write_node'))
            else:
                os.write(fh_nukepy, "nuke.toNode('%s').knob('file').setValue('%s')\n"%(g_config.get('delivery', 'matte_write_node'), s_matte_dest.replace('*', '%04d')))
                l_exec_nodes.append(g_config.get('delivery', 'matte_write_node'))
            
            s_exec_nodes = (', '.join('nuke.toNode("' + write_node + '")' for write_node in l_exec_nodes))
            os.write(fh_nukepy, "print \"INFO: About to execute render...\"\n")
            os.write(fh_nukepy, "try:\n")
            if len(l_exec_nodes) == 1:
                os.write(fh_nukepy, "    nuke.execute(nuke.toNode(\"%s\"),%d,%d,1,)\n"%(l_exec_nodes[0], start_frame - 1, end_frame))
            else:
                os.write(fh_nukepy, "    nuke.executeMultiple((%s),((%d,%d,1),))\n"%(s_exec_nodes, start_frame - 1, end_frame))
            os.write(fh_nukepy, "except:\n")
            os.write(fh_nukepy, "    print \"ERROR: Exception caught!\\n%s\"%traceback.format_exc()\n")
            os.close(fh_nukepy)

            # generate the xml file
            new_submission = etree.Element('DailiesSubmission')
            sht_se = etree.SubElement(new_submission, 'Shot')
            sht_se.text = s_shot

            if avidqt_delivery:
                fname_se = etree.SubElement(new_submission, 'AvidQTFileName')
                fname_se.text = os.path.basename(s_avidqt_dest)
            if vfxqt_delivery:
                vfxname_se = etree.SubElement(new_submission, 'VFXQTFileName')
                vfxname_se.text = os.path.basename(s_vfxqt_dest)
            if export_delivery:
                exportname_se = etree.SubElement(new_submission, 'ExportQTFileName')
                exportname_se.text = os.path.basename(s_exportqt_dest)
            if hires_delivery or matte_delivery:
                hires_format_se = etree.SubElement(new_submission, 'HiResFormat')
                hires_format_se.text = s_format
            if hires_delivery:
                if s_delivery_fileext == 'exr':
                    hires_fname_se = etree.SubElement(new_submission, 'EXRFileName')
                    hires_fname_se.text = os.path.basename(s_exr_dest)
                if s_delivery_fileext == 'dpx':
                    hires_fname_se = etree.SubElement(new_submission, 'DPXFileName')
                    hires_fname_se.text = os.path.basename(s_dpx_dest)
            if matte_delivery:
                matte_fname_se = etree.SubElement(new_submission, 'MatteFileName')
                matte_fname_se.text = os.path.basename(s_matte_dest)
            sframe_se = etree.SubElement(new_submission, 'StartFrame')
            sframe_se.text = "%d" % (start_frame - 1)
            eframe_se = etree.SubElement(new_submission, 'EndFrame')
            eframe_se.text = "%d" % end_frame
            stc_se = etree.SubElement(new_submission, 'StartTimeCode')
            stc_se.text = "%s" % slate_frame_tc
            etc_se = etree.SubElement(new_submission, 'EndTimeCode')
            etc_se.text = "%s" % last_frame_tc
            artist_se = etree.SubElement(new_submission, 'Artist')
            artist_se.text = s_artist_name
            notes_se = etree.SubElement(new_submission, 'SubmissionNotes')
            notes_se.text = cvn_txt

            # write out xml file to disk

            prettyxml = minidom.parseString(etree.tostring(new_submission)).toprettyxml(indent="  ")
            xml_ds = open(s_xml_dest, 'w')
            xml_ds.write(prettyxml)
            xml_ds.close()

            # copy CDL file if we are delivering hi-res frames
            if b_deliver_cdl:
                d_files_to_copy[s_cdl_src] = s_cdl_dest

            # render all frames - in a background thread
            threading.Thread(target=render_delivery_background, args=[s_nukepy, d_db_thread_helper, start_frame, end_frame, d_files_to_copy]).start()

        for all_nd in nuke.allNodes():
            if all_nd in oglist:
                all_nd.knob('selected').setValue(True)
            else:
                all_nd.knob('selected').setValue(False)
