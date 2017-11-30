#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Depth
#
#----------------------------------------------------------------------------------------------------------

for i in nuke.selectedNodes():
	i.knob('auto_descriptor').setValue(False)
	i.knob('optional_descriptor').setValue('Depth')

	i.knob('file_type').setValue('exr')
	i.knob('datatype').setValue('32 bit float')	
