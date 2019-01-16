#!/usr/bin/python

import nuke
import re
import os
import sys
import nukescripts.ViewerProcess
import ConfigParser
import shlex
import logging
import traceback

if sys.platform == 'win32':
    print 'Windows detected. Adding C:/Python27/Lib/site-packages to PYTHONPATH'
    sys.path.append('C:/Python27/Lib/site-packages')
else:
    sys.path.append('/Volumes/raid_vol01/shows/SHARED/lib/python')
    sys.path.append('/Volumes/raid_vol01/shows/goosebumps2/SHARED/shotgun/install/core/python')
    sys.path.append('/Library/Python/2.7/site-packages')
    sys.path.append('/usr/local/lib/python2.7/site-packages')
    
# if sys.platform == 'win32':
#     nuke.pluginAddPath('Y:\\shows\\SHARED\\lib\\rvnuke')
# else:
#     nuke.pluginAddPath('/Volumes/raid_vol01/shows/SHARED/lib/rvnuke')
    
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

# Prints "Rendered frame N of example.mov." Useful when rendering Quicktimes in non-interactive mode.
# Not in use currently. Will be adding code to the after each frame knob of the DNXHD Quicktime Write
# node in the template.
def print_render_frame():
    file = os.path.basename(nuke.thisNode()['file'].evaluate())
    frame = nuke.frame()
    print "Rendered frame %s of %s."%(frame, file)


# function attempts to determine show, sequence, and shot from the nuke script name.
# does nothing if the path does not produce a match to the shot regular expression
def init_shot_env():
    homedir = os.path.expanduser('~')
    logfile = ""
    if sys.platform == 'win32':
        logfile = os.path.join(homedir, 'AppData', 'Local', 'IHPipeline', 'nuke_launch.log')
    elif sys.platform == 'darwin':
        logfile = os.path.join(homedir, 'Library', 'Logs', 'IHPipeline', 'nuke_launch.log')
    elif sys.platform == 'linux2':
        logfile = os.path.join(homedir, 'Logs', 'IHPipeline', 'nuke_launch.log')
    if not os.path.exists(os.path.dirname(logfile)):
        os.makedirs(os.path.dirname(logfile))
    logFormatter = logging.Formatter("%(asctime)s:[%(threadName)s]:[%(levelname)s]:%(message)s")
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    log.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    log.addHandler(consoleHandler)    

    script_path = os.path.normpath(nuke.root().name())
    script_path_lst = script_path.split(os.path.sep)
    path_idx = 0
    str_show_code = None
    str_shot = None
    str_seq = None
    
    try:
        str_show_code = os.environ['IH_SHOW_CODE']
    except KeyError:
        log.warning("IH_SHOW_CODE environment variable not defined. Proceeding without environment.")
        return

    str_show_root = None
    try:
        str_show_root = os.environ['IH_SHOW_ROOT']
    except KeyError:
        log.warning("IH_SHOW_ROOT environment variable not defined. Proceeding without environment.")
        return
    
    if not os.path.exists(str_show_root):
        log.warning("Show root directory does not exist at %s."%str_show_root)
        return
    
    str_show_cfg_path = None
    try:
        str_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
    except KeyError:
        log.warning("IH_SHOW_CFG_PATH environment variable not defined. Proceeding without environment.")
        return
    
    if not os.path.exists(str_show_cfg_path):
        log.warning("Show configuration file does not exist at %s."%str_show_cfg_path)
        return
        
    config = ConfigParser.ConfigParser()
    config.read(str_show_cfg_path)
    cfg_shot_dir = config.get(str_show_code, 'shot_dir')
    cfg_shot_regexp = config.get(str_show_code, 'shot_regexp')
    cfg_seq_regexp = config.get(str_show_code, 'sequence_regexp')
    
    # were we called from within shotgun?
    b_shotgun = False
    b_shotgun_res = False
    engine = None
    ctx = None
    entity = None
    for envvar in os.environ.keys():
        log.debug('ENVIRONMENT - %s: %s'%(envvar, os.environ[envvar]))
        
    try:
        toolkit_engine = os.environ['TANK_ENGINE']
        b_shotgun = True
        log.info('Setting b_shotgun to True, os.environ[\'TANK_ENGINE\'] exists.')
    except:
        pass

    if not script_path.startswith(str_show_root):
        log.warning("Unable to match show root directory with Nuke script path.")
        b_shotgun_res = True

    matchobject = re.search(cfg_shot_regexp, script_path)
    # make sure this file matches the shot pattern
    if not matchobject:
        log.warning("This script name does not match the shot regular expression pattern for the show.")
        b_shotgun_res = True
    else:
        str_shot = matchobject.group(0)
        str_seq = re.search(cfg_seq_regexp, str_shot).group(0)

    if b_shotgun:        
        log.info("Nuke executed from within Shotgun Desktop Integration.")
        ctx = None
        try:
            import sgtk
            ctx = sgtk.Context.deserialize(os.environ['TANK_CONTEXT'])
        except KeyError:
            log.error("Envionrment variable TANK_CONTEXT not found.")
        except ImportError:
            log.error("Unable to import sgtk.")
        if ctx == None:
            log.warning("Nuke executed within Shotgun, but the context associated with the current engine is None.")
        else:
            log.info("Shotgun Toolkit Context Object:")
            log.info(ctx)
            entity = ctx.entity
            if entity == None:
                log.warning("Nuke executed within Shotgun, but the entity associated with the current context is None.")
            else:
                if entity['type'] != 'Shot':
                    log.warning("Nuke executed within Shotgun, but not in the context of a specific shot.")
                else:
                    if b_shotgun_res:
                        log.info("Nuke executed within Shotgun, but no active script available. Setting sequence and shot from current engine context.")
                        try:
                            str_shot = entity['name']
                            str_seq = re.search(cfg_seq_regexp, str_shot).group(0)
                        except KeyError:
                            log.error("For some reason, context provided by Shotgun to Nuke is %s. Unable to proceed."%ctx)
                            str_shot = None
    
    if str_shot == None:
        log.warning("Could not determine current shot from script name, or from database. Exiting init_shot_env().")
        return
        
    str_seq_path = ""
    str_shot_path = ""
    str_show_path = str_show_root

    str_shot_path = cfg_shot_dir.replace('/', os.path.sep).replace("SHOW_ROOT", str_show_root).replace("SEQUENCE", str_seq).replace("SHOT", str_shot)
    
    # show uses subdirectories for sequence
    if 'SEQUENCE' in cfg_shot_dir:
        str_seq_path = cfg_shot_dir.replace('/', os.path.sep).replace("SHOW_ROOT", str_show_root).replace("SEQUENCE", str_seq).replace("SHOT", '')
    	
    str_show = str_show_code
    
    log.info("Located show %s, path %s"%(str_show, str_show_path))
    log.info("Located sequence %s, path %s"%(str_seq, str_seq_path))
    log.info("Located shot %s, path %s"%(str_shot, str_shot_path))

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
    # TODO: pull these values out of the show config file
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

    # shot directories
    try:
        l_nukescript_dir = config.get('shot_structure', 'nukescript_dir').split('{pathsep}')
        l_plate_dir = config.get('shot_structure', 'plate_dir').split('{pathsep}')
        l_precomp_dir = config.get('shot_structure', 'precomp_dir').split('{pathsep}')
        l_rendercomp_dir = config.get('shot_structure', 'rendercomp_dir').split('{pathsep}')
        l_element_dir = config.get('shot_structure', 'element_dir').split('{pathsep}')
        l_renderelem_dir = config.get('shot_structure', 'renderelem_dir').split('{pathsep}')
        l_mograph_dir = config.get('shot_structure', 'mograph_dir').split('{pathsep}')
        l_ref_dir = config.get('shot_structure', 'ref_dir').split('{pathsep}')
        l_nukescript_dir.insert(0, r'[getenv SHOT_PATH]')
        l_plate_dir.insert(0, r'[getenv SHOT_PATH]')
        l_precomp_dir.insert(0, r'[getenv SHOT_PATH]')
        l_rendercomp_dir.insert(0, r'[getenv SHOT_PATH]')
        l_element_dir.insert(0, r'[getenv SHOT_PATH]')
        l_renderelem_dir.insert(0, r'[getenv SHOT_PATH]')
        l_mograph_dir.insert(0, r'[getenv SHOT_PATH]')
        l_ref_dir.insert(0, r'[getenv SHOT_PATH]')
        log.info('Successfully retrieved Shot directory structure from config file.')
        log.info(l_nukescript_dir)
        log.info(os.path.sep.join(l_nukescript_dir))
        nuke.addFavoriteDir("SHOT/nuke", os.path.sep.join(l_nukescript_dir))
        nuke.addFavoriteDir("SHOT/plates", os.path.sep.join(l_plate_dir))
        nuke.addFavoriteDir("SHOT/precomp", os.path.sep.join(l_precomp_dir))
        nuke.addFavoriteDir("SHOT/comp", os.path.sep.join(l_rendercomp_dir))
        nuke.addFavoriteDir("SHOT/elements", os.path.sep.join(l_element_dir))
        nuke.addFavoriteDir("SHOT/renders", os.path.sep.join(l_renderelem_dir))
        nuke.addFavoriteDir("SHOT/mograph", os.path.sep.join(l_mograph_dir))
        nuke.addFavoriteDir("SHOT/ref", os.path.sep.join(l_ref_dir))
    except Exception as e:
        log.warning("Caught exception %s when attempting to extract shot structure from the config file. Reverting to hard-coded shortcut paths."%type(e).__name__)
        log.warning(traceback.format_exc())
        nuke.addFavoriteDir("SHOT/nuke", os.path.join('[getenv SHOT_PATH]', 'nuke'))
        nuke.addFavoriteDir("SHOT/plates", os.path.join('[getenv SHOT_PATH]', 'pix', 'plates'))
        nuke.addFavoriteDir("SHOT/precomp", os.path.join('[getenv SHOT_PATH]', 'pix', 'precomp'))
        nuke.addFavoriteDir("SHOT/comp", os.path.join('[getenv SHOT_PATH]', 'pix', 'comp'))
        nuke.addFavoriteDir("SHOT/elements", os.path.join('[getenv SHOT_PATH]', 'pix', 'elements'))
        nuke.addFavoriteDir("SHOT/renders", os.path.join('[getenv SHOT_PATH]', 'pix', 'renders'))
        nuke.addFavoriteDir("SHOT/mograph", os.path.join('[getenv SHOT_PATH]', 'pix', 'mograph'))
        nuke.addFavoriteDir("SHOT/ref", os.path.join('[getenv SHOT_PATH]', 'ref'))
    
	

# custom formats
# nuke.load("formats.tcl")

# attempt to populate environment variables

if nuke.env['gui']:
   init_shot_env()
   nuke.addOnScriptLoad(init_shot_env)
else:
    try:
        tmp = os.environ['TANK_CONTEXT']
        print "INFO: Nuke launched from Shotgun."
        nuke.addOnScriptLoad(init_shot_env)
    except KeyError:
        pass

   
# print the environment to STDOUT
# print "DEBUG: Inside init.py, printing current environment."
# for env_key in sorted(os.environ.keys()):
#    print "%s : %s"%(env_key, os.environ[env_key])

# add support for RV
if nuke.env['gui']:
    import rvflipbook
    
if nuke.NUKE_VERSION_MAJOR > 8:
    nuke.knobDefault("Read.mov.mov64_decode_video_levels", "Video Range")

# add callback to auto-create directory path for write nodes
nuke.addBeforeRender(make_dir_path, nodeClass = 'Write')
# nuke.addAfterFrameRender(print_render_frame, nodeClass = 'Write')
