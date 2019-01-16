#!/usr/bin/python

import sys
import os.path
import nuke
import nukescripts
import subprocess

import autoBackdrop
from SetEnabledByName import *
from utilities import *
from vclf_multi_autotrack import *
import scaleDagNodes

import autosave_backup

# add incremental autosave functionality
nuke.addOnScriptSave(autosave_backup.backup_autosave)

def display_delivery_window(b_2k, b_matte=False, b_combined=False):
    cmd = "/Volumes/raid_vol01/shows/SHARED/bin/publish_delivery.py --gui"
    if b_2k:
        cmd = "/Volumes/raid_vol01/shows/SHARED/bin/publish_delivery.py --gui --hires"
    if b_matte:
        cmd = "/Volumes/raid_vol01/shows/SHARED/bin/publish_delivery.py --gui --matte"
    if b_combined:
        cmd = "/Volumes/raid_vol01/shows/SHARED/bin/publish_delivery.py --gui --combined"
    print "INFO: Forking process %s."%cmd
    subprocess.Popen(cmd, shell=True)

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

menubar = nuke.menu("Nuke")
m = menubar.addMenu("In-House")

n = m.addMenu("&Color")
n.addCommand("Lin2Log Wrapper", "nuke.createNode(\"LinLogWrapper.nk\")")

n = m.addMenu("Delivery")
o = n.addMenu("Render")
o.addCommand("Standard Delivery", "send_for_review()")
o.addCommand("Temp Delivery", "send_for_review(cc=False, b_method_hires=False)")
o.addCommand("DI Matte Delivery", "send_for_review(cc=False, b_method_avidqt=False, b_method_vfxqt=False, b_method_burnin=False, b_method_hires=False, b_method_matte=True)")

p = n.addMenu("Publish")
p.addCommand("Combined Package", "display_delivery_window(False, b_combined=True)")
p.addCommand("Quicktime Package", "display_delivery_window(False)")
p.addCommand("Hi-Res Package", "display_delivery_window(True)")
p.addCommand("Matte Package", "display_delivery_window(False, b_matte=True)")

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
