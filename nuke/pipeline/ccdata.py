#!/usr/bin/python

# ccdata.py
#
# Contains CCData class
# 
# Constructor takes one argument: the path to a cc/cdl/ccc file
#

import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import re

class CCData():

    def __init__(self, ccdatafile):
        # check to be sure the file provided in the constructor exists
        if not os.path.exists(ccdatafile):
            raise ValueError("No CC data file exists on the filesystem at %s."%ccdatafile)
        # open the provided file
        xml_fh = open(ccdatafile)
        xml_string = xml_fh.read()
        xml_fh.close()
        # remove all namespace references - these are unnecessary and cause parsing problems down the line
        xml_fixed = re.sub(' xmlns="[^"]+"', '', xml_string, count=1)
        # build the element tree
        root = ET.fromstring(xml_fixed)
        # set the relevant values to None/default
        self.ccid = None
        self.slope = None
        self.offset = None
        self.power = None
        self.saturation = 1.0
        # loop through each element in the xml document
        for element in root.iter():
            # ColorCorrection tag - extract the ID
            if element.tag == 'ColorCorrection':
                try:
                    self.ccid = element.attrib['id']
                except:
                    pass
            # Slope tag - extract the values
            elif element.tag == 'Slope':
                self.slope = [float(ccval) for ccval in element.text.split(" ")]
            # Offset tag - extract the values
            elif element.tag == 'Offset':
                self.offset = [float(ccval) for ccval in element.text.split(" ")]
            # Power tag - extract the values
            elif element.tag == 'Power':
                self.power = [float(ccval) for ccval in element.text.split(" ")]
            # Saturation tag - extract the value
            elif element.tag == 'Saturation':
                self.saturation = float(element.text)
        # rebuild a fresh element tree based on the extracted values
        self.ccelement = ET.Element('ColorCorrection')
        if self.ccid:
            self.ccelement.set('id', self.ccid)
        sopnodeelement = ET.SubElement(self.ccelement, 'SOPNode')
        slopeelement = ET.SubElement(sopnodeelement, 'Slope')
        slopeelement.text = ' '.join([str(fpelem) for fpelem in self.slope])
        offsetelement = ET.SubElement(sopnodeelement, 'Offset')
        offsetelement.text = ' '.join([str(fpelem) for fpelem in self.offset])
        powerelement = ET.SubElement(sopnodeelement, 'Power')
        powerelement.text = ' '.join([str(fpelem) for fpelem in self.power])
        satnodeelement = ET.SubElement(self.ccelement, 'SatNode')
        saturationelement = ET.SubElement(satnodeelement, 'Saturation')
        saturationelement.text = str(self.saturation)
        
        # build the CDL document format
        self.cdlelement = ET.Element('ColorDecisionList')
        cdelement = ET.SubElement(self.cdlelement, 'ColorDecision')
        cdelement.append(self.ccelement)
        
        # build the CCC document format
        self.cccelement = ET.Element('ColorCorrectionCollection')
        self.cccelement.append(self.ccelement)
        
        # assign "pretty" xml to all three document formats
        self.ccelement_text = minidom.parseString(ET.tostring(self.ccelement)).toprettyxml(indent="  ")
        self.cccelement_text = minidom.parseString(ET.tostring(self.cccelement)).toprettyxml(indent="  ")
        self.cdlelement_text = minidom.parseString(ET.tostring(self.cdlelement)).toprettyxml(indent="  ")
        
    # if someone calls print - just print out the xml representation of the CC data
    def __repr__(self):
        return self.ccelement_text
        
    # writes out a .cc file. single argument is a path to a .cc file that you would like to write.
    def write_cc_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.ccelement_text)
        xmldata_fh.close()

    # writes out a .ccc file. single argument is a path to a .cc file that you would like to write.
    def write_ccc_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.cccelement_text)
        xmldata_fh.close()

    # writes out a .cdl file. single argument is a path to a .cc file that you would like to write.
    def write_cdl_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.cdlelement_text)
        xmldata_fh.close()
        