#!/usr/bin/python

#python imports
import shutil
import os

#nuke import 
import nuke

#user defined global variable
max_autosave_files=5

#global variable to hold the next autosave number
next_autosave_version=0

def backup_autosave():
    global next_autosave_version
    #get autosave file
    autosave_file = nuke.toNode("preferences")["AutoSaveName"].evaluate()
    #compute next autosave file name
    file = autosave_file + str(next_autosave_version)
    #check if original autosave file exists 
    if os.path.exists(autosave_file):
        try:
            shutil.copy(autosave_file, file)
        except:
            pass
            # A message box every time it can't find an autosave file is irritating AF
            # nuke.message("Attention! Autosave file could not be copied!")
        nuke.tprint("Copied autosave file to: %s"%file)
        #start from the beginning if max files are reached
        if next_autosave_version==max_autosave_files:
            next_autosave_version=0
        else:
            next_autosave_version+=1
    elif nuke.Root()['name'].value():
        #warn if there is no autosave at all
        has_autosave=False
        for i in range(max_autosave_files):
            if os.path.exists(autosave_file + str(i)):
                has_autosave=True
                
        if not has_autosave and nuke.modified():
            pass
            # A message box every time it can't find an autosave file is irritating AF
            # nuke.message("Attention! You do not have an autosave file!")
