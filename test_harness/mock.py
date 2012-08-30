
import sys, os, platform

# this assures we use the included libs/twisted and libs/zope libraries
# this is of particular importance on Mac OS X since an older version of twisted
# is already installed in the OS
__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)
libs_path = os.path.join(os.path.split(__path__)[0], 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# need the windows select.pyd binary
from twisted.python import runtime, log
if runtime.platform.isWindows():
    __file__ = os.path.normpath(os.path.abspath(__file__))
    __path__ = os.path.dirname(__file__)
    libs_path = os.path.join(os.path.split(__path__)[0], 'libs', platform.architecture()[0])
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from negotiator import irc
from twisted.internet import reactor
import time, threading, logging, sys, signal

def callback(obj):
    print type(obj)

def runMockSubliminalCollaborator(host, port, username, password, channel):
    if type(port) == str:
        port = int(port)
    negotiator = irc.IRCNegotiator(callback)
    negotiator.connect(host, port, username, password, channel=channel)

def main(argv):
    if len(argv) < 4:
        print 'Invalid argument count: at least 4 expected, got %d' % len(argv)
        return

    log.startLogging(sys.stdout)

    logger = logging.getLogger(__name__)
    logger.propagate = False
    # purge previous handlers set... for plugin reloading
    del logger.handlers[:]
    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutHandler.setFormatter(logging.Formatter(fmt='[SubliminalCollaborator(%(levelname)s): %(message)s]'))
    logger.addHandler(stdoutHandler)
    logger.setLevel(logging.DEBUG)
    reactor.callInThread(runMockSubliminalCollaborator, *argv)
    reactor.run()

if __name__ == "__main__":
   main(sys.argv[1:])
   print 'Quitting Mock SubliminalCollaborator'
