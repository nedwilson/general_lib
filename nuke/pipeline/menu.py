#!/usr/bin/python

import sys
import os.path
import nuke
import nukescripts

import autoBackdrop
from SetEnabledByName import *
from utilities import *
from vclf_multi_autotrack import *
import scaleDagNodes

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

n = m.addMenu("&File")
n.addCommand("Read from Write", "read_from_write()", "#r")
n.addCommand("Reveal in Finder", "reveal_in_finder()", "^f")
n.addCommand("Copy Read To Shot", "copyReadToShot()")
n.addCommand("Copy Render To Shot","copyRenderToShot()")

n = m.addMenu("&Time")
n.addCommand( 'Hold at Current Frame', 'nuke.createNode("FrameHold")["first_frame"].setValue( nuke.frame() )', 'alt+h', icon="FrameHold.png")

n = m.addMenu("&Color")
n.addCommand("Lin2Log Wrapper", "nuke.createNode(\"LinLogWrapper.nk\")")

n = m.addMenu("&Filter")
n.addCommand("Gradient Blur", "nuke.createNode(\"GradientBlur.nk\")")
n.addCommand("Weighted Blur", "nuke.createNode(\"WeightedBlur.nk\")")
n.addCommand("Edge Scatter", "nuke.createNode(\'EdgeScatter\')")
n.addCommand("Arri Alexa Grain", "nuke.createNode(\'ScannedGrainIH\')")

n=m.addMenu("&Utility")
n.addCommand('Named Auto Backdrop', lambda: autoBackdrop.autoBackdrop(), 'alt+b')
n.addCommand('Backdrop Color OCD', 'backdropColorOCD()')
n.addCommand("Make Write Directory", "make_dir_path()", "ctrl+F8")
n.addCommand("Slate/Slate and Burn-In", "nuke.createNode(\'ML_SlateBurnIn\')")
n.addCommand("Slate/Slate Only", "nuke.createNode(\'ML_SlateOnly\')")
n.addCommand("Viewer Input", "nuke.createNode(\'VIEWER_INPUT')")
n.addCommand("Roto/Set name to roto paint stroke range","setNameToStrokesRange()")
n.addCommand("Set Enabled Range from Name","setEnabledByName()")
n.addCommand("Roto/How is your paint going?","makeSad()")
n.addCommand("Link Roto to Tracker","trackLinker.linkTrackToRoto()","alt+o")
n.addCommand("DAG/scale Nodes up", "scaleDagNodes.scaleNodes(1.1)","alt+=")
n.addCommand("DAG/scale Nodes down", "scaleDagNodes.scaleNodes(.9)","alt+-")
n.addCommand("Roto/RotoShapes To Trackers", "RotoShapes_to_trackers.RotoShape_to_Trackers()")
n.addCommand("Quick Label", "quickLabel()", "ctrl+alt+N")
n.addCommand("OpticalFlare Auto Multitrack", "vclf_multi_autotrack()")
n.addCommand("Build CC Nodes", "build_cc_nodes()", "alt+c")
n.addCommand("Open Count Sheet", "open_count_sheet()")

# Swap out the default version up functionality with a method that makes the directory
# stored in the Write node.
nd_menu = menubar.findItem("Edit")
if not nd_menu == None:
    nd_menu.addCommand("&Node/&Filename/Version Up", "version_up_mkdir()", "#Up")
else:
    print "WARN: nd_menu object is None."
