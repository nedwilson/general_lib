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
        if not os.path.exists(ccdatafile):
            raise ValueError("No CC data file exists on the filesystem at %s."%ccdatafile)
        xml_fh = open(ccdatafile)
        xml_string = xml_fh.read()
        xml_fh.close()
        xml_fixed = re.sub(' xmlns="[^"]+"', '', xml_string, count=1)
        root = ET.fromstring(xml_fixed)
        self.ccid = None
        self.slope = None
        self.offset = None
        self.power = None
        self.saturation = 1.0
        for element in root.iter():
            if element.tag == 'ColorCorrection':
                try:
                    self.ccid = element.attrib['id']
                except:
                    pass
            elif element.tag == 'Slope':
                self.slope = [float(ccval) for ccval in element.text.split(" ")]
            elif element.tag == 'Offset':
                self.offset = [float(ccval) for ccval in element.text.split(" ")]
            elif element.tag == 'Power':
                self.power = [float(ccval) for ccval in element.text.split(" ")]
            elif element.tag == 'Saturation':
                self.saturation = float(element.text)
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
        
        self.cdlelement = ET.Element('ColorDecisionList')
        cdelement = ET.SubElement(self.cdlelement, 'ColorDecision')
        cdelement.append(self.ccelement)
        
        self.cccelement = ET.Element('ColorCorrectionCollection')
        self.cccelement.append(self.ccelement)
        
        self.ccelement_text = minidom.parseString(ET.tostring(self.ccelement)).toprettyxml(indent="  ")
        self.cccelement_text = minidom.parseString(ET.tostring(self.cccelement)).toprettyxml(indent="  ")
        self.cdlelement_text = minidom.parseString(ET.tostring(self.cdlelement)).toprettyxml(indent="  ")
        
    def __repr__(self):
        return self.ccelement_text
        
    def write_cc_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.ccelement_text)
        xmldata_fh.close()

    def write_ccc_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.cccelement_text)
        xmldata_fh.close()

    def write_cdl_file(self, filepath):
        xmldata_fh = open(filepath, 'w')
        xmldata_fh.write(self.cdlelement_text)
        xmldata_fh.close()
        
        
        
        