def cloneWithExpression(n):
    n.setSelected(False) 
    newNode = nuke.createNode(n.Class(), n.writeKnobs(nuke.WRITE_NON_DEFAULT_ONLY | nuke.TO_SCRIPT), inpanel=False)
    for k in newNode.allKnobs():
        if k.name() not in ["ypos","xpos","selected","dope_sheet"]:
            k.setExpression("%s.%s"%(n.name(),k.name()))

cloneWithExpression(nuke.selectedNodes()[0])