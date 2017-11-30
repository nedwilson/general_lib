#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: alpha
#
#----------------------------------------------------------------------------------------------------------

import nuke

for i in nuke.selectedNodes():
	i.knob('output').setValue('alpha')