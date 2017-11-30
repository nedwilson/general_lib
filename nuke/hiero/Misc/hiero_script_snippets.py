# print worker list

from hiero.ui.nuke_bridge.nukestudio import frameServer

l_formattedList = []

for worker in frameServer.getStatus(1).workerStatus:
    l_tmpWorker = worker.address.split(' - ')
    l_formattedList.append([l_tmpWorker[1], l_tmpWorker[2], l_tmpWorker[0]])

print ""
for l_fmtWorker in sorted(l_formattedList):
    print ' - '.join(l_fmtWorker)
    
# fix shot names on timeline

import hiero.ui

for o_timelineItem in hiero.ui.getTimelineEditor(hiero.ui.activeSequence()).selection():
    o_timelineItem.setName('_'.join(o_timelineItem.name().split('_')[0:2]).upper())
