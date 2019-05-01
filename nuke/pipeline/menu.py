#!/usr/local/bin/python

import sys
import os.path
import nuke
import nukescripts
import subprocess
import ConfigParser

import autoBackdrop
from SetEnabledByName import *
from utilities import *
from vclf_multi_autotrack import *
import scaleDagNodes

import autosave_backup

# add incremental autosave functionality
nuke.addOnScriptSave(autosave_backup.backup_autosave)

def display_delivery_window(cmd):
    print("INFO: Forking process %s."%cmd)
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        print(proc.stdout.read())
    except:
        print(sys.exc_info())


def build_delivery_args(output_opts='cc,avidqt,vfxqt,burnin,hires,export'):
    return_string='send_for_review(cc={cc}, b_method_avidqt={avidqt}, b_method_vfxqt={vfxqt}, b_method_burnin={burnin}, b_method_export={export}, b_method_hires={hires}, b_method_matte={matte})'
    dict_delivery_opts = { 'cc' : 'False', 'avidqt' : 'False', 'vfxqt' : 'False', 'burnin' : 'False', 'export' : 'False', 'hires' : 'False', 'matte' : 'False' }
    for output_opt in output_opts.split(','):
        dict_delivery_opts[output_opt] = 'True'
    return return_string.format(**dict_delivery_opts)

import trackLinker

import RotoShapes_to_trackers
import version_control

# Un-comment the following to add Deadline Support
# import DeadlineNukeClient
# tbmenu = m.addMenu("&Render")
# tbmenu.addCommand("Render with Deadline", DeadlineNukeClient.main, "")
# try:
#     if nuke.env[ 'studio' ]:
#         import DeadlineNukeFrameServerClient
#         tbmenu.addCommand("Reserve Frame Server Slaves", DeadlineNukeFrameServerClient.main, "")
# except:
#     pass

# read options from config file

config = ConfigParser.ConfigParser()
show_config_path = None
try:
    show_config_path = os.environ['IH_SHOW_CFG_PATH']
except KeyError:
    raise RuntimeError("This system does not have an IH_SHOW_CFG_PATH environment variable defined.")

if not os.path.exists(show_config_path):
    raise RuntimeError("The IH_SHOW_CFG_PATH environment variable is defined on this system with value %s, but no file exists at that location." % show_config_path)

config.read(show_config_path)

menubar = nuke.menu("Nuke")
m = menubar.addMenu("In-House")

n = m.addMenu("&Color")
n.addCommand("Lin2Log Wrapper", "nuke.createNode(\"LinLogWrapper.nk\")")

n = m.addMenu("Delivery")
o = n.addMenu("Render")

l_render_commands = config.get('delivery', 'render_delivery_options').split('|')
for render_command in l_render_commands:
    l_command = render_command.split(':')
    s_command = build_delivery_args(l_command[1])
    o.addCommand(l_command[0], s_command)

p = n.addMenu("Publish")
l_publish_commands = config.get('delivery', 'publish_delivery_menu_commands').split(',')
s_command_common = config.get('delivery', 'publish_delivery_cmd_%s'%sys.platform)
for publish_command in l_publish_commands:
    l_command = publish_command.split('|')
    s_command = 'display_delivery_window("%s %s")'%(s_command_common, l_command[1])
    p.addCommand(l_command[0], s_command)

n = m.addMenu("&File")
n.addCommand("Copy Read To Shot", "copyReadToShot()")
n.addCommand("Copy Render To Shot","copyRenderToShot()")
n.addCommand("Read from Write", "read_from_write()", "#r")
n.addCommand("Reveal in Finder", "reveal_in_finder()", "^f")

n = m.addMenu("&Filter")
n.addCommand("Arri Alexa Grain", "nuke.createNode(\'ScannedGrainIH\')")
n.addCommand("Edge Scatter", "nuke.createNode(\'EdgeScatter\')")
n.addCommand("Gradient Blur", "nuke.createNode(\"GradientBlur.nk\")")
n.addCommand("HiPass", "nuke.createNode(\'HIPASS\')")
n.addCommand("Weighted Blur", "nuke.createNode(\"WeightedBlur.nk\")")

n = m.addMenu("&Time")
n.addCommand( 'Hold at Current Frame', 'nuke.createNode("FrameHold")["first_frame"].setValue( nuke.frame() )', 'alt+h', icon="FrameHold.png")

n=m.addMenu("&Utility")
n.addCommand('Backdrop Color OCD', 'backdropColorOCD()')
n.addCommand("Build CC Nodes", "build_cc_nodes()", "alt+c")
n.addCommand("DAG/scale Nodes up", "scaleDagNodes.scaleNodes(1.1)","alt+=")
n.addCommand("DAG/scale Nodes down", "scaleDagNodes.scaleNodes(.9)","alt+-")
n.addCommand("Link Roto to Tracker","trackLinker.linkTrackToRoto()","alt+o")
n.addCommand("Make Write Directory", "make_dir_path()", "ctrl+F8")
n.addCommand('Named Auto Backdrop', lambda: autoBackdrop.autoBackdrop(), 'alt+b')
n.addCommand("Open Count Sheet", "open_count_sheet()")
n.addCommand("OpticalFlare Auto Multitrack", "vclf_multi_autotrack()")
n.addCommand("Precomp Write", "precomp_write()", "alt+p")
n.addCommand("Quick Label", "quickLabel()", "ctrl+alt+N")
n.addCommand("Roto/How is your paint going?","makeSad()")
n.addCommand("Roto/RotoShapes To Trackers", "RotoShapes_to_trackers.RotoShape_to_Trackers()")
n.addCommand("Roto/Set name to roto paint stroke range","setNameToStrokesRange()")
n.addCommand("Set Enabled Range from Name","setEnabledByName()")
n.addCommand("Slate/Slate and Burn-In", "nuke.createNode(\'ML_SlateBurnIn\')")
n.addCommand("Slate/Slate Only", "nuke.createNode(\'ML_SlateOnly\')")
n.addCommand("Viewer Input", "nuke.createNode(\'VIEWER_INPUT')")

# Swap out the default version up functionality with a method that makes the directory
# stored in the Write node.
nd_menu = menubar.findItem("Edit")
if not nd_menu == None:
    nd_menu.addCommand("&Node/&Filename/Version Up", "version_up_mkdir()", "#Up")
else:
    print "WARN: nd_menu object is None."
