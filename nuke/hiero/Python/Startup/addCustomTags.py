#!/usr/bin/python

import hiero
def addCustomTags(event):
	isCreated = False
	startupProject = hiero.core.projects()[-1]
	if startupProject.name() != "Tag Presets":
		tagBin = startupProject.tagsBin()
		for subBin in tagBin.bins():
			if subBin.name() == 'IH Tags':
				isCreated = True
		if not isCreated:
			mlBin = hiero.core.Bin('ML Tags')

			a65Tag = hiero.core.Tag('Arri 65')
			a65Tag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(a65Tag)

			aaxtaTag = hiero.core.Tag('Arri Alexa XT Anamorphic')
			aaxtaTag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(aaxtaTag)

			aaxtsTag = hiero.core.Tag('Arri Alexa XT Spherical')
			aaxtsTag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(aaxtsTag)

			aaxt169Tag = hiero.core.Tag('Arri Alexa XT 16:9')
			aaxt169Tag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(aaxt169Tag)

			aamTag = hiero.core.Tag('Arri Alexa Mini')
			aamTag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(aamTag)

			rd5kTag = hiero.core.Tag('Red Dragon 5K')
			rd5kTag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(rd5kTag)

			gp4kTag = hiero.core.Tag('GoPro 4K')
			gp4kTag.setIcon('icons:TagCameraTracker.png')
			mlBin.addItem(gp4kTag)

			mirrorTag = hiero.core.Tag('Mirror')
			mirrorTag.setIcon('icons:TagFullShot.png')
			mlBin.addItem(mirrorTag)

			tagBin.addItem(mlBin)

hiero.core.events.registerInterest('kAfterProjectLoad', addCustomTags)
