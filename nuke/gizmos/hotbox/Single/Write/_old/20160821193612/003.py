#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Mocha
#
#----------------------------------------------------------------------------------------------------------

for i in nuke.selectedNodes():
	i.knob('auto_descriptor').setValue(False)
	i.knob('optional_descriptor').setValue('Mocha')

	i.knob('file_type').setValue('jpg')
	i.knob('_jpeg_quality').setValue(1)	
