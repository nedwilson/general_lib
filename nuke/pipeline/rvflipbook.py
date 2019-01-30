# Copyright (c) 2010 The Foundry Visionmongers Ltd.  All Rights Reserved.
import platform
import sys
import os
import re
import thread
import nuke
import subprocess
import nukescripts
import nukescripts.flipbooking as flipbooking
import ConfigParser
import traceback
import socket

gb_use_rvsdi = False

class RVFlipbook(flipbooking.FlipbookApplication):
    """This is an example implementation of how to deal with implementing a
     flipbook application other than FrameCycler for NUKE. This script needs
     to be modified in several places before it can work, so please read all
     of the notes marked with TODO and modify them where necessary."""

    def __init__(self):
        # initialize show config
        global gb_use_rvsdi
        self._hostname = socket.gethostname().split('.', 1)[0]
        self._config = None
        self._lin_to_log_lut_path = None
        self._use_lin_to_log_lut = False
        self._display_lut_path = None
        self._use_display_lut = False
        self._shot_lut_path = None
        self._shot_lut_file_ext = None
        self._lin_to_log_exts = []
        self._shot_lut_exts = []
        self._shot_regexp = None
        self._temp_regexp = None
        self._rvsdi_hosts = []
        self._use_shot_cc = False
        try:
            str_show_cfg_path = os.environ['IH_SHOW_CFG_PATH']
            str_show_code = os.environ['IH_SHOW_CODE']
            self._config = ConfigParser.ConfigParser()
            self._config.read(str_show_cfg_path)
            self._lin_to_log_lut_path = self._config.get('color', 'lin_to_log_lut_path_%s'%sys.platform)
            if self._config.get('color', 'use_lin_to_log_lut') in ['Yes', 'YES', 'yes', 'Y', 'y', 'True', 'TRUE', 'true']:
                self._use_lin_to_log_lut = True
            self._display_lut_path = self._config.get('color', 'display_lut_path_%s'%sys.platform)
            if self._config.get('color', 'use_display_lut') in ['Yes', 'YES', 'yes', 'Y', 'y', 'True', 'TRUE', 'true']:
                self._use_display_lut = True
            self._shot_lut_path = self._config.get('color', 'shot_lut_file_path_%s'%sys.platform)
            self._shot_lut_file_ext = self._config.get('color', 'shot_lut_file_ext')
            self._lin_to_log_exts = self._config.get('color', 'lin_to_log_lut_exts').split(',')
            self._shot_lut_exts = self._config.get('color', 'shot_lut_exts').split(',')
            self._shot_regexp = re.compile(self._config.get(str_show_code, 'shot_regexp'))
            self._temp_regexp = re.compile(self._config.get(str_show_code, 'temp_element_regexp'))
            self._rvsdi_hosts = self._config.get('color', 'rvsdi_hosts').split(',')
        except BaseException as be:
            print "ERROR: Exception caught while attempting to load RV Flipbook information from show config file."
            print traceback.format_exc()

        # RV Path Implementation
        if sys.platform == 'darwin':
            if os.path.exists("/Applications/RVSDI.app/Contents/MacOS/RVSDI"):
                self._rvPath = "/Applications/RVSDI.app/Contents/MacOS/RVSDI"
                self._rvName = "RVSDI"
                gb_use_rvsdi = True
            else:
                self._rvPath = "/Applications/RV64.app/Contents/MacOS/RV64"
                self._rvName = "RV64"
        elif sys.platform == 'win32':
            if os.path.exists("C:\\Program Files\\RVSDI\\RVSDI.exe"):
                self._rvPath = "C:\\Program Files\\RVSDI\\RVSDI.exe"
                self._rvName = "RVSDI"
                gb_use_rvsdi = True
            else:
                self._rvPath = "C:\\Program Files\\Shotgun\\RV-7.2.3\\bin\\rv.exe"
                self._rvName = "RV64"
        else:
            if os.path.exists("/usr/local/tweak/rvsdi"):
                self._rvPath = "/usr/local/tweak/rvsdi"
                self._rvName = "RVSDI"
                gb_use_rvsdi = True
            else:
                self._rvPath = "/usr/local/tweak/rv64"
                self._rvName = "RV64"

    def name(self):
        return self._rvName

    def path(self):
        return self._rvPath

    def cacheDir(self):
        return os.environ["NUKE_TEMP_DIR"]

    def run(self, filename, frameRanges, views, options):
        # replace '####' in frame range with '%04d'
        pound_frameno_re = re.compile(r'\.(#+)\.')
        pound_match = pound_frameno_re.search(filename)
        if pound_match:
            pound_str = pound_match.group(1)
            pound_str_len = len(pound_str)
            valid_format_str = '%d'
            if pound_str_len > 1:
                valid_format_str = '%%0%dd'%pound_str_len
            filename = filename.replace(pound_str, valid_format_str)

        # handle frame ranges
        sequence_interval = str(frameRanges.minFrame())+"-"+str(frameRanges.maxFrame())
        for frame in xrange(frameRanges.minFrame(), frameRanges.maxFrame()):
            if frame not in frameRanges.toFrameList():
                print "This example only supports complete frame ranges"
                return

        os.path.normpath(filename)

        args = []
        
        if nuke.env['WIN32']:
            args.append( "\"" + self.path() + "\"" )
            filename = filename.replace("/", "\\")
            filename = "\"" + filename + "\""
        else:
            args.append( self.path() )


        roi = options.get("roi", None)
        if roi != None and not (roi["x"] == 0.0 and roi["y"] == 0.0 and roi["w"] == 0.0 and roi["h"] == 0.0):
            args.append("-c "+str(int(roi["x"])))
            args.append(str(int(roi["y"])))
            args.append(str(int(roi["w"])))
            args.append(str(int(roi["h"])))

        lut = options.get("lut", "")
        print "DEBUG: LUT selected in the Flipbook Panel: %s"%lut
        if lut == "sRGB":
            args.append("-sRGB")
        elif lut == "rec709":
            args.append('-rec709')

        if self._use_shot_cc:
            print("DEBUG: shot_cc checked in the Flipbook Panel!")

        args.append('[')
        args.append(repr(filename))
        args.append(sequence_interval)

        shotmatch = self._shot_regexp.search(filename)
        lut_filename = None
        file_extension = os.path.splitext(filename)[1][1:]

        shot_re_dict = {}
        if shotmatch:
            try:
                shot_re_dict['shot'] = shotmatch.groupdict()['shot']
                shot_re_dict['sequence'] = shotmatch.groupdict()['sequence']
                shot_re_dict['ext'] = self._shot_lut_file_ext
                tmp_filename = self._shot_lut_path.format(**shot_re_dict)
                print "DEBUG: Looking for shot LUT at path %s"%tmp_filename
                if os.path.exists(tmp_filename):
                    lut_filename = tmp_filename
                    print('DEBUG: Found it!')
                else:
                    print('DEBUG: LUT does not exist on filesystem. Skipping.')
            except BaseException as be:
                print "ERROR: Unable to determine shot LUT path. Skipping."
                print traceback.format_exc()

        if self._use_lin_to_log_lut and file_extension in self._shot_lut_exts and self._use_shot_cc:
            args.append('-pclut')
            args.append(self._lin_to_log_lut_path)

        # append shot LUT to command line, if it exists and we are not looking at a Quicktime
        if lut_filename and file_extension in self._shot_lut_exts and self._use_shot_cc:
            if self._shot_lut_file_ext in ['cdl', 'cc', 'ccc']:
                args.append('-fcdl')
            else:
                args.append('-flut')
            args.append(lut_filename)
        
        # append look LUT to command line, if the file extension is correct and we are using it for this show
        if self._use_display_lut and file_extension in self._shot_lut_exts and self._use_shot_cc:
            args.append('-llut')
            args.append(self._display_lut_path)

        args.append(']')
        if self._rvName == 'RVSDI':
            args.append('-present')

        # look for show LUT
        # try:
        #     args.append('-dlut %s'%os.environ['IH_SHOW_CFG_LUT'])
        # except KeyError:
        #     pass

        # os.environ['RV_CUSTOM_FLUT_DIR'] = os.path.join(os.environ['SHOT_PATH'], 'data', 'cdl')
        # print "Set environment variable RV_CUSTOM_FLUT_DIR to %s"%os.path.join(os.environ['SHOT_PATH'], 'data', 'cdl')
        # print args
        # os.spawnv(os.P_NOWAITO, self.path(), args)
        print ' '.join(args)
        subprocess.Popen(' '.join(args), shell=True)

    def capabilities(self):
        return {
            'proxyScale': False,
            'crop': True,
            'canPreLaunch': False,
            'supportsArbitraryChannels': True,
            'maximumViews' : 2,
            # TODO: This list is compiled from running rv with the following:
            # RV64 -formats | grep 'format "' | awk '{print $2}' | tr '[:space:]' ','; echo
            # This may differ for your platform!
            'fileTypes' : ["j2k","jpt","jp2","dpx","cin","cineon","jpeg","jpg","rla","rpf","yuv","exr","openexr","sxr","tif","tiff","sm","tex","tx","tdl","shd","targa","tga","tpic","rgbe","hdr","iff","png","z","zfile","sgi","bw","rgb","rgba","*mraysubfile*","movieproc","stdinfb","aiff","aif","aifc","wav","snd","au","mov","avi","mp4","m4v","dv"]
        }

    def dialogKnobs(self, dialog):
        shot_cc_knob = nuke.Boolean_Knob('shot_cc', 'Add Shot Color Correction?')
        shot_cc_knob.setFlag(nuke.STARTLINE)
        dialog.addKnob(shot_cc_knob)

    def dialogKnobChanged(self, dialog, knob):
        # if the user has changed the shot_cc knob, adjust the self._use_shot_cc variable
        if knob.name() == 'shot_cc':
            kval = knob.getValue()
            if kval == 1.0:
                self._use_shot_cc = True
            else:
                self._use_shot_cc = False

flipbooking.register( RVFlipbook() )
if gb_use_rvsdi:
    nukescripts.setFlipbookDefaultOption("flipbook", "RVSDI")
else:
    nukescripts.setFlipbookDefaultOption("flipbook", "RV64")
