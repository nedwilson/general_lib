# Copyright (c) 2010 The Foundry Visionmongers Ltd.  All Rights Reserved.
import platform
import sys
import os.path
import re
import thread
import nuke
import subprocess
import nukescripts
import nukescripts.flipbooking as flipbooking

class RVFlipbook(flipbooking.FlipbookApplication):
    """This is an example implementation of how to deal with implementing a
     flipbook application other than FrameCycler for NUKE. This script needs
     to be modified in several places before it can work, so please read all
     of the notes marked with TODO and modify them where necessary."""
    
    def __init__(self):
        # TODO: Please put your own path in here or add RV path discovery.
        if sys.platform == 'darwin':
            if os.path.exists("/Applications/RVSDI.app/Contents/MacOS/RVSDI"):
                self._rvPath = "/Applications/RVSDI.app/Contents/MacOS/RVSDI"
                self._rvName = "RVSDI"
            else:
                self._rvPath = "/Applications/RV64.app/Contents/MacOS/RV64"
                self._rvName = "RV64"
        elif sys.platform == 'win32':
            if os.path.exists("C:\\Program Files\\RVSDI\\RVSDI.exe"):
                self._rvPath = "C:\\Program Files\\RVSDI\\RVSDI.exe"
                self._rvName = "RVSDI"
            else:
                self._rvPath = "C:\\Program Files\\Shotgun\\RV-7.2.3\\bin\\rv.exe"
                self._rvName = "RV64"
        else:
            if os.path.exists("/usr/local/tweak/rvsdi"):
                self._rvPath = "/usr/local/tweak/rvsdi"
                self._rvName = "RVSDI"
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
        # TODO: You probably want more involved handling of frame ranges!
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
        if lut == "linear-sRGB":
            args.append("-sRGB")
        elif lut == "linear-rec709":
            args.append('-rec709')

        args.append('[')
        args.append(filename)
        args.append(sequence_interval)

        # look for shot cdl
        try:
            args.append('-fcdl %s'%os.path.join(os.environ['SHOT_PATH'], 'data', 'cdl', '%s.cdl'%os.environ['SHOT']))
        except KeyError:
            pass

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

flipbooking.register( RVFlipbook() )
nukescripts.setFlipbookDefaultOption("flipbook", "RV")