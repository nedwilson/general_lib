# setFrameRate - adds a Right-click menu to the Project Bin view, allowing multiple BinItems (Clips/Sequences) to have their frame rates set.
# Removes frame 1 from quicktimes
import hiero.core
import hiero.ui
from PySide2.QtWidgets import *
from PySide2.QtCore import *

class RemoveSlateFrame(QAction):
	def __init__(self):
		QAction.__init__(self, "Remove Slate Frame", None)
		self.triggered.connect(self.chopOffFrameOne)
		hiero.core.events.registerInterest("kShowContextMenu/kBin", self.eventHandler)

	def chopOffFrameOne(self):
		for item in hiero.ui.activeView().selection():
			item.activeItem().setInTime(item.activeItem().sourceIn()+1)

	# This handles events from the Project Bin View
	def eventHandler(self,event):
		enabled = True
		title = "Remove Slate Frame"
		self.setText(title)
		event.menu.addAction( self )

# Instantiate the Menu to get it to register itself.
RemoveSlateFrame = RemoveSlateFrame()