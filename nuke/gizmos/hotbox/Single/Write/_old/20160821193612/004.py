#----------------------------------------------------------------------------------------------------------
#
# AUTOMATICALLY GENERATED FILE TO BE USED BY W_HOTBOX
#
# NAME: Denoise
#
#----------------------------------------------------------------------------------------------------------

for i in nuke.selectedNodes():
    
        i.knob('auto_descriptor').setValue(False)
        i.knob('optional_descriptor').setValue('Denoise')


        i.knob('file_type').setValue('exr')
