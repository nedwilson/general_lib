#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Background
#
#----------------------------------------------------------------------------------------------------------

for i in nuke.selectedNodes():
	
	i.knob('auto_descriptor').setValue(False)
	i.knob('optional_descriptor').setValue('preRenderBg')

	i.knob('file_type').setValue('exr')
