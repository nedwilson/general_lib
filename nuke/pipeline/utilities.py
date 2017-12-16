#!/usr/bin/python

import os
import nuke
import nukescripts
import glob
import subprocess
import datetime
import xml.etree.ElementTree as etree
import shutil
import xml.dom.minidom as minidom
import socket
import re
import threading
import math
import sys
import pwd
import ConfigParser
import tempfile
import traceback
from operator import itemgetter
import time
from stat import S_ISREG, S_ISDIR, ST_MTIME, ST_MODE

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
        rval = pwd.getpwuid(os.getuid()).pw_gecos
    except:
        pass
    return rval


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


# creates a read node from a write node.

def read_from_write():
    sel = None
    file_path = ""
    start_frame = 1000
    end_frame = 1001
    node = None
    xpos = 0
    ypos = 0
    try:
        sel = nuke.selectedNodes()
    except:
        print "INFO: No nodes selected."
        return
    for nd in sel:
        if nd.Class() != "Write":
            continue
        file_path = nd.knob("file").value()
        file_type = nd.knob("file_type").value()
        read_node = nuke.createNode("Read", "file {" + file_path + "}", inpanel=True)
        if os.path.exists(os.path.dirname(file_path)):
            if not file_type == "mov":
                image_ar = sorted(glob.glob(file_path.replace('%04d', '*')))
                if (len(image_ar) == 0):
                    start_frame = int(nuke.root().knob("first_frame").value())
                    end_frame = int(nuke.root().knob("last_frame").value())
                else:
                    start_frame = int(image_ar[0].split('.')[1])
                    end_frame = int(image_ar[-1].split('.')[1])
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
    dir = os.path.dirname(file)
    osdir = nuke.callbacks.filenameFilter(dir)
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
    config = ConfigParser.ConfigParser()
    config.read(os.environ['IH_SHOW_CFG_PATH'])
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
    config = ConfigParser.ConfigParser()
    config.read(os.environ['IH_SHOW_CFG_PATH'])
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
    config = ConfigParser.ConfigParser()
    config.read(os.environ['IH_SHOW_CFG_PATH'])
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
    config = ConfigParser.ConfigParser()
    config.read(os.environ['IH_SHOW_CFG_PATH'])
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
        
    # get all pdf files in the count sheet directory w/ modification times, sort by modification time descending
    l_countsheets = [os.path.join(s_count_sheet_dir, fn) for fn in os.listdir(s_count_sheet_dir) if fn.endswith('.pdf')]
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

#
# create_thumbnail takes one argument: the path of an image to make a thumbnail from. 
# it requires that environment variable IH_SHOW_CFG_PATH be defined, and that config
# file must have a thumb_template section.
#
# it writes the thumbnail out to the data/thumbnails directory of the shot.
# 
    
def create_thumbnail(m_source_path):

    if not os.path.exists(m_source_path):
        raise IOError("File not found: %s"%m_source_path)
    
    show_cfg_path = None
    show_root = None
    show_code = None
    
    try:    
        show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
    except KeyError:
        raise EnvironmentError("Required environment variable IH_SHOW_CFG_PATH is not defined.")

    try:    
        show_root = os.environ['IH_SHOW_ROOT']
    except KeyError:
        raise EnvironmentError("Required environment variable IH_SHOW_ROOT is not defined.")

    try:    
        show_code = os.environ['IH_SHOW_CODE']
    except KeyError:
        raise EnvironmentError("Required environment variable IH_SHOW_CODE is not defined.")
        
    config = ConfigParser.ConfigParser()
    config.read(show_cfg_path)
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
    dest_path = dest_path_format.format(**format_dict)
    
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

    if b_deliver_cdl:    
        # open up the cdl and extract the cccid
        cdltext = open(s_cdl_src, 'r').read()
        cccid_re_str = r'<ColorCorrection id="([A-Za-z0-9-_]+)">'
        cccid_re = re.compile(cccid_re_str)
        cccid_match = cccid_re.search(cdltext)
        s_cccid = cccid_match.group(1)
    
        # slope
        slope_re_str = r'<Slope>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Slope>'
        slope_re = re.compile(slope_re_str)
        slope_match = slope_re.search(cdltext)
        slope_r = slope_match.group(1)
        slope_g = slope_match.group(2)
        slope_b = slope_match.group(3)

        # offset
        offset_re_str = r'<Offset>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Offset>'
        offset_re = re.compile(offset_re_str)
        offset_match = offset_re.search(cdltext)
        offset_r = offset_match.group(1)
        offset_g = offset_match.group(2)
        offset_b = offset_match.group(3)
    
        # power
        power_re_str = r'<Power>([0-9.-]+) ([0-9.-]+) ([0-9.-]+)</Power>'
        power_re = re.compile(power_re_str)
        power_match = power_re.search(cdltext)
        power_r = power_match.group(1)
        power_g = power_match.group(2)
        power_b = power_match.group(3)
    
        # saturation
        saturation_re_str = r'<Saturation>([0-9.-]+)</Saturation>'
        saturation_re = re.compile(saturation_re_str)
        saturation_match = saturation_re.search(cdltext)
        saturation = saturation_match.group(1)
    
    
    fh_nukepy, s_nukepy = tempfile.mkstemp(suffix='.py')
    
    print "INFO: Temporary Python script: %s"%s_nukepy
    os.write(fh_nukepy, "#!/usr/bin/python\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "import nuke\n")
    os.write(fh_nukepy, "import os\n")
    os.write(fh_nukepy, "import sys\n")
    os.write(fh_nukepy, "import traceback\n")
    os.write(fh_nukepy, "\n")
    os.write(fh_nukepy, "nuke.scriptOpen(\"%s\")\n"%thumb_template)
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
        os.write(fh_nukepy, "nuke.toNode('OCIOCDLTransform1').knob('file').setValue(\"%s\")\n"%s_cdl_src)
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

