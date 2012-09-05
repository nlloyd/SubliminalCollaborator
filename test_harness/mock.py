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
if __file__ not in sys.path:
    sys.path.append(__path__) 

# need the windows select.pyd binary
from twisted.python import runtime, log
if runtime.platform.isWindows():
    __file__ = os.path.normpath(os.path.abspath(__file__))
    __path__ = os.path.dirname(__file__)
    libs_path = os.path.join(os.path.split(__path__)[0], 'libs', platform.architecture()[0])
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from negotiator import irc
from peer import interface
from twisted.internet import reactor, error
import time, threading, logging, sys

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

class MockFailure(object):
    def __init__(self, type):
        self.type = type

def negotiateCallback_accept(caller, session):
    print 'negotiateCallback_accept'

def negotiateCallback_retry(caller, session):
    print 'negotiateCallback_retry'
    session.clientConnectionFailed(None, MockFailure(error.ConnectionRefusedError))
    session.state = interface.STATE_DISCONNECTING
    session.disconnect()

def onNegotiateCallback_accept(caller, deferredOnNegotiateCallback, username):
    print 'onNegotiateCallback_accept: %s, %s' % (deferredOnNegotiateCallback, username)
    deferredOnNegotiateCallback.callback(0)

def onNegotiateCallback_reject(deferredOnNegotiateCallback, username):
    print 'onNegotiateCallbackReject: %s, %s' % (deferredOnNegotiateCallback, username)
    deferredOnNegotiateCallback.callback(1)

def rejectedCallback(obj1, obj2):
    print 'rejectedCallback: %s ,%s' % (obj1, obj2)

def runMockSubliminalCollaborator(host, port, username, password, channel, isHost=False, sessionBehavior='accept'):
    if type(port) == str:
        port = int(port)
    negotiateCallback = negotiateCallback_accept
    onNegotiateCallback = None
    if sessionBehavior == 'accept':
        onNegotiateCallback = onNegotiateCallback_accept
    elif sessionBehavior == 'reject':
        onNegotiateCallback = onNegotiateCallback_reject
    elif sessionBehavior == 'retry':
        negotiateCallback = negotiateCallback_retry
    irc.IRCNegotiator.negotiateCallback = negotiateCallback
    irc.IRCNegotiator.onNegotiateCallback = onNegotiateCallback
    irc.IRCNegotiator.rejectedOrFailedCallback = rejectedCallback
    negotiator = irc.IRCNegotiator()
    negotiator.connect(host, port, username, password, channel=channel)
    if isHost in ['True','true']:
        print 'running as mock host'
        reactor.callLater(5.0, runHostBehavior, negotiator)
    else:
        print 'running as mock client with session behavior set to %s' % sessionBehavior

def runHostBehavior(negotiator):
        users = negotiator.listUsers()
        while len(users) == 0:
            return
        logger.info('Initiating collaboration session with %s' % users[0])
        negotiator.negotiateSession(users[0])


def main(argv):
    if len(argv) < 4:
        print 'python mock.py host port username password channel? isHost=False sessionBehavior=accept|reject|retry'
        return

    configureLogging()
    print argv

    reactor.callLater(2.0, runMockSubliminalCollaborator, *argv)
    reactor.run()

if __name__ == "__main__":
   main(sys.argv[1:])
   print 'Quitting Mock SubliminalCollaborator'
