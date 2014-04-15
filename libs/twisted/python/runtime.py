# -*- test-case-name: twisted.python.test.test_runtime -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import division, absolute_import

import os
import sys
import time
import imp
import warnings

from twisted.python import compat

if compat._PY3:
    _threadModule = "_thread"
else:
    _threadModule = "thread"



def shortPythonVersion():
    """
    Returns the Python version as a dot-separated string.
    """
    return "%s.%s.%s" % sys.version_info[:3]



knownPlatforms = {
    'nt': 'win32',
    'ce': 'win32',
    'posix': 'posix',
    'java': 'java',
    'org.python.modules.os': 'java',
    }



_timeFunctions = {
    #'win32': time.clock,
    'win32': time.time,
    }



class Platform:
    """
    Gives us information about the platform we're running on.
    """

    type = knownPlatforms.get(os.name)
    seconds = staticmethod(_timeFunctions.get(type, time.time))
    _platform = sys.platform

    def __init__(self, name=None, platform=None):
        if name is not None:
            self.type = knownPlatforms.get(name)
            self.seconds = _timeFunctions.get(self.type, time.time)
        if platform is not None:
            self._platform = platform


    def isKnown(self):
        """
        Do we know about this platform?

        @return: Boolean indicating whether this is a known platform or not.
        @rtype: C{bool}
        """
        return self.type != None


    def getType(self):
        """
        Get platform type.

        @return: Either 'posix', 'win32' or 'java'
        @rtype: C{str}
        """
        return self.type


    def isMacOSX(self):
        """
        Check if current platform is Mac OS X.

        @return: C{True} if the current platform has been detected as OS X.
        @rtype: C{bool}
        """
        return self._platform == "darwin"


    def isWinNT(self):
        """
        Are we running in Windows NT?

        This is deprecated and always returns C{True} on win32 because
        Twisted only supports Windows NT-derived platforms at this point.

        @return: C{True} if the current platform has been detected as
            Windows NT.
        @rtype: C{bool}
        """
        warnings.warn(
                "twisted.python.runtime.Platform.isWinNT was deprecated in "
                "Twisted 13.0. Use Platform.isWindows instead.",
                DeprecationWarning, stacklevel=2)
        return self.isWindows()


    def isWindows(self):
        """
        Are we running in Windows?

        @return: C{True} if the current platform has been detected as
            Windows.
        @rtype: C{bool}
        """
        return self.getType() == 'win32'


    def isVista(self):
        """
        Check if current platform is Windows Vista or Windows Server 2008.

        @return: C{True} if the current platform has been detected as Vista
        @rtype: C{bool}
        """
        if getattr(sys, "getwindowsversion", None) is not None:
            return sys.getwindowsversion()[0] == 6
        else:
            return False


    def isLinux(self):
        """
        Check if current platform is Linux.

        @return: C{True} if the current platform has been detected as Linux.
        @rtype: C{bool}
        """
        return self._platform.startswith("linux")


    def supportsThreads(self):
        """
        Can threads be created?

        @return: C{True} if the threads are supported on the current platform.
        @rtype: C{bool}
        """
        try:
            return imp.find_module(_threadModule)[0] is None
        except ImportError:
            return False


    def supportsINotify(self):
        """
        Return C{True} if we can use the inotify API on this platform.

        @since: 10.1
        """
        try:
            from twisted.python._inotify import INotifyError, init
        except ImportError:
            return False
        try:
            os.close(init())
        except INotifyError:
            return False
        return True


platform = Platform()
platformType = platform.getType()
seconds = platform.seconds
