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
import sublime, sublime_plugin
import sys, os, platform

# this assures we use the included libs/twisted and libs/zope libraries
# this is of particular importance on Mac OS X since an older version of twisted
# is already installed in the OS
__file__ = os.path.normpath(os.path.abspath(__file__))
__path__ = os.path.dirname(__file__)
libs_path = os.path.join(__path__, 'libs')
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# need the windows select.pyd binary
from twisted.python import runtime
if runtime.platform.isWindows():
    __file__ = os.path.normpath(os.path.abspath(__file__))
    __path__ = os.path.dirname(__file__)
    libs_path = os.path.join(__path__, 'libs', platform.architecture()[0])
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from negotiator import irc
from twisted.internet import reactor
import threading, logging, sys

logger = logging.getLogger(__name__)
logger.propagate = False
# purge previous handlers set... for plugin reloading
del logger.handlers[:]
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(logging.Formatter(fmt='[SubliminalCollaborator(%(levelname)s): %(message)s]'))
logger.addHandler(stdoutHandler)
logger.setLevel(logging.DEBUG)

class ReactorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        if not reactor.running:
            logger.info('[SubliminalCollaborator: starting the event reactor on a thread]')
            reactor.run(installSignalHandlers=False)

ReactorThread().start()

negotiatorFactoryMap = {
    'irc': irc.IRCNegotiator
}

#*** globals for preferences and session variables ***#
# config dictionary, key is protocol:host:username, value is config dict
chatClientConfig = {}
# key is same as config dictionary with value equallying live negotiator instances
negotiatorInstances = {}
sessions = {}


def loadConfig():
    acctConfig = sublime.load_settings('Accounts.sublime-settings')
    acctConfigAlt = sublime.load_settings('Preferences.sublime-settings')
    if not acctConfig.has('subliminal_collaborator'):
        logger.info('loading configuration from Preferences.sublime-settings')
        acctConfig = acctConfigAlt
    else:
        logger.info('loading configuration from Accounts.sublime-settings')
    accts = acctConfig.get('subliminal_collaborator', {})
    configErrorList = []
    for protocol, acct_details in accts.items():
        for acct_detail in acct_details:
            if not acct_detail.has_key('host'):
                configErrorList.append('A %s protocol configuration is missing a host entry' % protocol)
            if not acct_detail.has_key('port'):
                configErrorList.append('A %s protocol configuration is missing a port entry' % protocol)
            if not acct_detail.has_key('username'):
                configErrorList.append('A %s protocol configuration is missing a username entry' % protocol)
            if not acct_detail.has_key('password'):
                configErrorList.append('A %s protocol configuration is missing a password entry' % protocol)
            clientKey = '%s:%s:%s' % (protocol, acct_detail['host'], acct_detail['username'])
            chatClientConfig[clientKey] = acct_detail
    acctConfig.clear_on_change('subliminal_collaborator')
    acctConfig.add_on_change('subliminal_collaborator', loadConfig)
    if acctConfig != acctConfigAlt:
        acctConfigAlt.clear_on_change('subliminal_collaborator')
        acctConfigAlt.add_on_change('subliminal_collaborator', loadConfig)
    # report errors, if any
    if len(configErrorList) > 0:
        errorMsg = 'The following configuration errors were found:\n'
        for error in configErrorList:
            errorMsg = '%s%s\n' % (errorMsg, error)
        sublime.error_message(errorMsg)
        
loadConfig()


class CollaborateCommand(sublime_plugin.ApplicationCommand):
    chatClientKeys = []
    sessionKeys = []
    userList = []
    selectedNegotiator = None
    currentView = None

    def run(self, task):
        method = getattr(self, task, None)
        try:
            if method is not None:
                logger.debug('running collaborate task %s' % task)
                method()
            else:
                logger.error('unknown plugin task %s' % task)
        except:
            logger.error('unknown plugin task %s' % task)

    def startSession(self):
        self.chatClientKeys = chatClientConfig.keys()
        sublime.active_window().show_quick_panel(self.chatClientKeys, self.selectUser)

    def selectUser(self, clientIdx):
        targetClient = self.chatClientKeys[clientIdx]
        logger.debug('select user from client %s' % targetClient)
        self.selectedNegotiator = None
        if negotiatorInstances.has_key(targetClient):
            logger.debug('Found negotiator for %s, using it' % targetClient)
            self.selectedNegotiator = negotiatorInstances[targetClient]
        else:
            logger.debug('No negotiator for %s, creating one' % targetClient)
            self.selectedNegotiator = negotiatorFactoryMap[targetClient.split(':', 1)[0]]()
            negotiatorInstances[targetClient] = self.selectedNegotiator
        # now lets make sure we are connected to get the user list... and if we are not connected yet
        # start that process
        if self.selectedNegotiator.isConnected():
            sublime.active_window().show_quick_panel(self.userList, self.openSession)
        else:
            self.selectedNegotiator.connect(**chatClientConfig[targetClient])
            self.retryCounter = 0

    def openSession(self, userIdx=None):
        if not userIdx:
            if not self.selectedNegotiator.isConnected():
                if self.retryCounter > 30:
                    logger.warn('Failed to connect client %s' % self.selectedNegotiator.str())
                else:
                    # increment retry count... 
                    self.retryCounter = self.retryCounter + 1
                    logger.debug('Not connected yet to client %s, retry %d to connect' % (self.selectedNegotiator.str(), self.retryCounter))
                    sublime.set_timeout(lambda: openSession, 1000)
            else:
                # we are connected, retrieve and show current user list from target chat client negotiator
                self.userList = self.selectedNegotiator.listUsers()
                sublime.active_window().show_quick_panel(self.userList, self.openSession)
        else:
            # have a specified user, lets open a collaboration session!
            logger.debug('Opening collaboration session with user %s on client %s' % (self.userList[userIdx], self.selectedNegotiator))

    def showSessions(self):
        pass

    def closeSession(self):
        pass

    def disconnectChat(self, clientIdx=None):
        if not clientIdx:
            self.chatClientKeys = negotiatorInstances.keys()
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.selectUser)
        else:
            negotiatorInstances[self.chatClientKeys[clientIdx]].disconnect()