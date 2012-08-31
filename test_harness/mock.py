# All of SubliminalCollaborator is licensed under the MIT license.

#   Copyright (c) 2012 Nick Lloyd

#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:

#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.

#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHE`R
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
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

logger = logging.getLogger(__name__)
logger.propagate = False

def configureLogging():
    log.startLogging(sys.stdout)

    global logger
    # purge previous handlers set... for plugin reloading
    del logger.handlers[:]
    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutHandler.setFormatter(logging.Formatter(fmt='[SubliminalCollaborator(%(levelname)s): %(message)s]'))
    logger.addHandler(stdoutHandler)
    logger.setLevel(logging.DEBUG)


def callback(obj):
    print type(obj)

def negotiateCallback(obj):
    print 'negotiateCallback'
    print type(obj)

def onNegotiateCallback(obj1, obj2):
    print 'onNegotiateCallback'
    print type(obj1)
    print type(obj2)

def rejectedCallback(obj1, obj2):
    print 'rejectedCallback'
    print type(obj1)
    print type(obj2)

def runMockSubliminalCollaborator(host, port, username, password, channel, isHost=False):
    if type(port) == str:
        port = int(port)
    negotiator = irc.IRCNegotiator(negotiateCallback, onNegotiateCallback, rejectedCallback)
    negotiator.connect(host, port, username, password, channel=channel)
    if bool(isHost):
        reactor.callLater(5.0, runHostBehavior, negotiator)

def runHostBehavior(negotiator):
        users = negotiator.listUsers()
        while len(users) == 0:
            return
        logger.info('Initiating collaboration session with %s' % users[0])
        negotiator.negotiateSession(users[0])


def main(argv):
    if len(argv) < 4:
        print 'python mock.py host port username password channel? isHost=False'
        return

    configureLogging()
    print argv

    reactor.callLater(2.0, runMockSubliminalCollaborator, *argv)
    reactor.run()

if __name__ == "__main__":
   main(sys.argv[1:])
   print 'Quitting Mock SubliminalCollaborator'
