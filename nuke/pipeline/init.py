#!/usr/bin/python

import nuke
import re
import os
import sys
import nukescripts.ViewerProcess
import ConfigParser
import shlex

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


# function attempts to determine show, sequence, and shot from the nuke script name.
# does nothing if the path does not produce a match to the shot regular expression
def init_shot_env():
    if not nuke.env['gui']:
        return
    script_path = os.path.normpath(nuke.root().name())
    script_path_lst = script_path.split(os.path.sep)
    path_idx = 0
    str_show_code = None
    str_shot = None
    str_seq = None
    try:
        str_show_code = os.environ['IH_SHOW_CODE']
    except KeyError:
        print "WARNING: IH_SHOW_CODE environment variable not defined. Proceeding without environment."
        return

    str_show_root = None
    try:
        str_show_root = os.environ['IH_SHOW_ROOT']
    except KeyError:
        print "WARNING: IH_SHOW_ROOT environment variable not defined. Proceeding without environment."
        return
    
    if not os.path.exists(str_show_root):
        print "WARNING: Show root directory does not exist at %s."%str_show_root
        return
    
    str_show_cfg_path = None
    try:
        str_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
    except KeyError:
        print "WARNING: IH_SHOW_CFG_PATH environment variable not defined. Proceeding without environment."
        return
    
    if not os.path.exists(str_show_cfg_path):
        print "WARNING: Show configuration file does not exist at %s."%str_show_cfg_path
        return
        
    config = ConfigParser.ConfigParser()
    config.read(str_show_cfg_path)
    cfg_shot_dir = config.get(str_show_code, 'shot_dir')
    cfg_shot_regexp = config.get(g_ih_show_code, 'shot_regexp')
    cfg_seq_regexp = config.get(g_ih_show_code, 'sequence_regexp')
    

    if not script_path.startswith(str_show_root):
    	print "WARNING: Unable to match show root directory with Nuke script path. Skipping init_shot_env()."
    	return
    
    matchobject = re.search(cfg_shot_regexp, script_path)
    # make sure this file matches the shot pattern
    if not matchobject:
        print "WARNING: This script name does not match the shot regular expression pattern for the show."
        return
    else:
        str_shot = matchobject.group(0)
        str_seq = re.search(cfg_seq_regexp, str_shot).group(0)
        
    str_seq_path = ""
    str_shot_path = ""
    str_show_path = str_show_root

    str_shot_path = cfg_shot_dir.replace('/', os.path.sep).replace("SHOW_ROOT", str_show_root).replace("SEQUENCE", str_seq).replace("SHOT", str_shot)
    
    # show uses subdirectories for sequence
    if 'SEQUENCE' in cfg_shot_dir:
        str_seq_path = cfg_shot_dir.replace('/', os.path.sep).replace("SHOW_ROOT", str_show_root).replace("SEQUENCE", str_seq).replace("SHOT", '')
    	
    str_show = str_show_code
    
    print "INFO: Located show %s, path %s"%(str_show, str_show_path)
    print "INFO: Located sequence %s, path %s"%(str_seq, str_seq_path)
    print "INFO: Located shot %s, path %s"%(str_shot, str_shot_path)

    os.environ['SHOW'] = str_show
    os.environ['SHOW_PATH'] = str_show_path
    os.environ['SEQ'] = str_seq
    os.environ['SEQ_PATH'] = str_seq_path
    os.environ['SHOT'] = str_shot
    os.environ['SHOT_PATH'] = str_shot_path

    # add knobs to root, if they don't exist already
    root_knobs_dict = nuke.root().knobs()
    k_ih_tab = None
    k_ih_show = None
    k_ih_show_path = None
    k_ih_seq = None
    k_ih_seq_path = None
    k_ih_shot = None
    k_ih_shot_path = None
    try:
        k_ih_tab = root_knobs_dict['tab_inhouse']
    except KeyError:
        k_ih_tab = nuke.Tab_Knob('tab_inhouse', 'In-House')
        nuke.root().addKnob(k_ih_tab)
    try:
        k_ih_show = root_knobs_dict['txt_ih_show']
    except KeyError:
        k_ih_show = nuke.String_Knob('txt_ih_show', 'show')
        nuke.root().addKnob(k_ih_show)
    try:
        k_ih_show_path = root_knobs_dict['txt_ih_show_path']
    except KeyError:
        k_ih_show_path = nuke.String_Knob('txt_ih_show_path', 'show path')
        nuke.root().addKnob(k_ih_show_path)
    try:
        k_ih_seq = root_knobs_dict['txt_ih_seq']
    except KeyError:
        k_ih_seq = nuke.String_Knob('txt_ih_seq', 'sequence')
        nuke.root().addKnob(k_ih_seq)
    try:
        k_ih_seq_path = root_knobs_dict['txt_ih_seq_path']
    except KeyError:
        k_ih_seq_path = nuke.String_Knob('txt_ih_seq_path', 'sequence path')
        nuke.root().addKnob(k_ih_seq_path)
    try:
        k_ih_shot = root_knobs_dict['txt_ih_shot']
    except KeyError:
        k_ih_shot = nuke.String_Knob('txt_ih_shot', 'shot')
        nuke.root().addKnob(k_ih_shot)
    try:
        k_ih_shot_path = root_knobs_dict['txt_ih_shot_path']
    except KeyError:
        k_ih_shot_path = nuke.String_Knob('txt_ih_shot_path', 'shot path')
        nuke.root().addKnob(k_ih_shot_path)
    k_ih_show.setValue(str_show)
    k_ih_show_path.setValue(str_show_path)
    k_ih_seq.setValue(str_seq)
    k_ih_seq_path.setValue(str_seq_path)
    k_ih_shot.setValue(str_shot)
    k_ih_shot_path.setValue(str_shot_path)
    
    # remove old favorite directories if they exist
    nuke_prefs_file = os.path.join(os.path.expanduser("~"), '.nuke', 'FileChooser_Favorites.pref')
    if os.path.exists(nuke_prefs_file):
        with open(nuke_prefs_file) as npf:
            for line in npf:
                if line.startswith('add_favorite_dir'):
                    line_array = shlex.split(line)
                    fav_name = line_array[1]
                    if fav_name.startswith('SHOW') or fav_name.startswith('SEQ') or fav_name.startswith('SHOT'):
                        nuke.removeFavoriteDir(fav_name)
                                
    # add favorite directories in file browser
    nuke.addFavoriteDir("SHOW", '[getenv IH_SHOW_ROOT]')
    if os.path.exists(os.path.join(str_show_root, 'SHARED')):
        nuke.addFavoriteDir("SHOW/SHARED", os.path.join('[getenv IH_SHOW_ROOT]', 'SHARED'))
    if os.path.exists(os.path.join(str_show_root, 'ref')):
        nuke.addFavoriteDir("SHOW/ref", os.path.join('[getenv IH_SHOW_ROOT]', 'ref'))
    if 'SEQUENCE' in cfg_shot_dir:
        nuke.addFavoriteDir("SEQ", '[getenv SEQ_PATH]')
        if os.path.exists(os.path.join(str_seq_path, 'SHARED')):
            nuke.addFavoriteDir("SEQ/SHARED", os.path.join('[getenv SEQ_PATH]', 'SHARED'))
        if os.path.exists(os.path.join(str_seq_path, 'ref')):
            nuke.addFavoriteDir("SEQ/ref", os.path.join('[getenv SEQ_PATH]', 'ref'))
    nuke.addFavoriteDir("SHOT", '[getenv SHOT_PATH]')
    nuke.addFavoriteDir("SHOT/plates", os.path.join('[getenv SHOT_PATH]', 'pix', 'plates'))
    nuke.addFavoriteDir("SHOT/comp", os.path.join('[getenv SHOT_PATH]', 'pix', 'comp'))
    nuke.addFavoriteDir("SHOT/precomp", os.path.join('[getenv SHOT_PATH]', 'pix', 'precomp'))
    nuke.addFavoriteDir("SHOT/nuke", os.path.join('[getenv SHOT_PATH]', 'nuke'))
    nuke.addFavoriteDir("SHOT/ref", os.path.join('[getenv SHOT_PATH]', 'ref'))
    
	

# custom formats
nuke.load("formats.tcl")

# attempt to populate environment variables

if nuke.env['gui']:
   nuke.addOnScriptLoad(init_shot_env)

if nuke.NUKE_VERSION_MAJOR > 8:
    nuke.knobDefault("Read.mov.mov64_decode_video_levels", "Video Range")

# add callback to auto-create directory path for write nodes
nuke.addBeforeRender(make_dir_path, nodeClass = 'Write')

