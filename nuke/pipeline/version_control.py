import os
import nuke



def check_script_version():
    twnode = None
    try:
        twnode = nuke.root()['timeline_write_node']
    except NameError:
        return
    # script is either untitled or was created outside of Nuke Studio
    if twnode is None:
        return
    script_write_nd_name= twnode.getValue()
    script_write_nd=nuke.toNode(script_write_nd_name)
    render_file=script_write_nd['file'].getValue()
    xml_file=render_file.split('.')[0]+".xml"
    if os.path.exists(xml_file):
        nuke.message("WARNING! It appears as if this script version has already been submitted for review. Please version up the script before you continue working.")



nuke.addOnScriptLoad(check_script_version)
