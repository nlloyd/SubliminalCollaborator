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
from twisted.python import runtime, log
if runtime.platform.isWindows():
    __file__ = os.path.normpath(os.path.abspath(__file__))
    __path__ = os.path.dirname(__file__)
    libs_path = os.path.join(__path__, 'libs', platform.architecture()[0])
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

from twisted.internet import selectreactor
if not 'SELECTREACTORINSTALLED' in globals():
    selectreactor.install()
    SELECTREACTORINSTALLED = True
    
from negotiator import irc
from peer.interface import STATE_CONNECTED, STATE_DISCONNECTED, STATE_REJECT_TRIGGERED_DISCONNECTING, SERVER
from peer import base
from twisted.internet import reactor
import threading, logging, time, shutil

# log.startLogging(sys.stdout)

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
            logger.info('Starting the event reactor on a thread')
            reactor.run(installSignalHandlers=False)

if not 'REACTOR_THREAD' in globals():
    REACTOR_THREAD = ReactorThread()
    REACTOR_THREAD.start()

negotiatorFactoryMap = {
    'irc': irc.IRCNegotiator
}

#*** globals for preferences and session variables ***#
# config dictionary, key is protocol:host:username, value is config dict
chatClientConfig = {}
connectAllOnStartup = False
# key is same as config dictionary with value equallying live negotiator instances
negotiatorInstances = {}
# sessions by chatClient
sessions = {}
# sessions by view id
sessionsByViewId = {}
sessionsLock = threading.Lock()

class SessionCleanupThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global sessions
        global sessionsByViewId
        global sessionsLock
        time.sleep(5.0)
        # runs for as long as the reactor is running
        while reactor.running:
            sessionsLock.acquire()
            for sessionsKey, protocolSessions in sessions.items():
                for sessionKey, session in protocolSessions.items():
                    if session.state == STATE_DISCONNECTED:
                        deadSession = sessions[sessionsKey].pop(sessionKey)
                        logger.debug('Cleaning up dead session: %s' % deadSession.str())
            for viewId, session in sessionsByViewId.items():
                if session.state == STATE_DISCONNECTED:
                    sessionsByViewId.pop(viewId)
            sessionsLock.release()
            time.sleep(30.0)

if not 'SESSION_CLEANUP_THREAD' in globals():
    SESSION_CLEANUP_THREAD = SessionCleanupThread()
    SESSION_CLEANUP_THREAD.start()

def loadConfig():
    global connectAllOnStartup
    acctConfig = sublime.load_settings('Accounts.sublime-settings')
    accts = acctConfig.get('subliminal_collaborator')
    logger.info('loading configuration from Accounts.sublime-settings')
    configErrorList = []
    if not accts:
        logger.error('No configuration found!')
        return
    acctConfig.clear_on_change('subliminal_collaborator')
    acctConfig.add_on_change('subliminal_collaborator', loadConfig)
    for protocol, acct_details in accts.items():
        if protocol == 'connect_all_on_startup':
            connectAllOnStartup = acct_details
            continue
        for acct_detail in acct_details:
            if not acct_detail.has_key('host'):
                configErrorList.append('A %s protocol configuration is missing a host entry' % protocol)
            if not acct_detail.has_key('port'):
                configErrorList.append('A %s protocol configuration is missing a port entry' % protocol)
            if not acct_detail.has_key('username'):
                configErrorList.append('A %s protocol configuration is missing a username entry' % protocol)
            if not acct_detail.has_key('password'):
                configErrorList.append('A %s protocol configuration is missing a password entry' % protocol)
            clientKey = '%s|%s@%s:%d' % (protocol, acct_detail['username'], acct_detail['host'], acct_detail['port'])
            chatClientConfig[clientKey] = acct_detail
    # report errors, if any
    if len(configErrorList) > 0:
        errorMsg = 'The following configuration errors were found:\n'
        for error in configErrorList:
            errorMsg = '%s%s\n' % (errorMsg, error)
        sublime.error_message(errorMsg)


def connectAllChat():
    logger.info('Connecting to all configured chat servers')
    chatClientKeys = chatClientConfig.keys()
    for connectedClient in negotiatorInstances.keys():
        chatClientKeys.remove(connectedClient)
    for client in chatClientKeys:
        logger.info('Connecting to chat %s' % client)
        negotiatorInstances[client] = negotiatorFactoryMap[client.split(':', 1)[0]]()
        negotiatorInstances[client].connect(**chatClientConfig[client])

loadConfig()

if connectAllOnStartup:
    connectAllChat()


class OpenSublimeSettingsCommand(sublime_plugin.WindowCommand):

    def run(self):
        accts_file = os.path.join(os.path.join(sublime.packages_path(), 'User', 'Accounts.sublime-settings'))
        if os.path.exists(accts_file):
            if os.path.getsize(accts_file) == 0:
                os.remove(accts_file)
                shutil.copy(os.path.join(os.path.dirname(__file__), 'Accounts.sublime-settings'), os.path.join(sublime.packages_path(), 'User'))
        else:
            shutil.copy(os.path.join(os.path.dirname(__file__), 'Accounts.sublime-settings'), os.path.join(sublime.packages_path(), 'User'))
        view = self.window.open_file(os.path.join(sublime.packages_path(), 'User', 'Accounts.sublime-settings'))

    def is_enabled(self):
        return self.window.active_view() != None


class CollaborateCommand(sublime_plugin.ApplicationCommand, sublime_plugin.EventListener):
    chatClientKeys = []
    sessionKeys = []
    userList = []
    selectedNegotiator = None
    currentView = None

    def __init__(self):
        sublime_plugin.ApplicationCommand.__init__(self)
        irc.IRCNegotiator.negotiateCallback = self.openSession
        irc.IRCNegotiator.onNegotiateCallback = self.acceptSessionRequest
        irc.IRCNegotiator.rejectedOrFailedCallback = self.killHostedSession
        base.BasePeer.peerConnectedCallback = self.shareView
        base.BasePeer.peerRecvdViewCallback = self.addSharedView

    def run(self, task):
        method = getattr(self, task, None)
        try:
            if method is not None:
                logger.debug('running collaborate task %s' % task)
                method()
            else:
                logger.error('unknown plugin task %s' % task)

        except:
            logger.error(sys.exc_info())

    def startSession(self):
        self.chatClientKeys = chatClientConfig.keys()
        sublime.active_window().show_quick_panel(self.chatClientKeys, self.selectUser)

    def selectUser(self, clientIdx):
        if clientIdx < 0:
            return
        targetClient = self.chatClientKeys[clientIdx]
        logger.debug('select user from client %s' % targetClient)
        self.selectedNegotiator = None
        if negotiatorInstances.has_key(targetClient):
            logger.debug('Found negotiator for %s, using it' % targetClient)
            self.selectedNegotiator = negotiatorInstances[targetClient]
        else:
            logger.debug('No negotiator for %s, creating one' % targetClient)
            self.selectedNegotiator = negotiatorFactoryMap[targetClient.split('|', 1)[0]]()
            negotiatorInstances[targetClient] = self.selectedNegotiator
            self.selectedNegotiator.connect(**chatClientConfig[targetClient])
        # use our negotiator to connect to the chat server and wait to grab the userlist
        self.retryCounter = 0
        self.connectToUser()

    def connectToUser(self, userIdx=None):
        if userIdx == None:
            if not self.selectedNegotiator.isConnected():
                if self.retryCounter >= 30:
                    logger.warn('Failed to connect client %s' % self.selectedNegotiator.str())
                else:
                    # increment retry count... 
                    self.retryCounter = self.retryCounter + 1
                    logger.debug('Not connected yet to client %s, recheck counter: %d' % (self.selectedNegotiator.str(), self.retryCounter))
                    sublime.set_timeout(self.connectToUser, 1000)
            else:
                # we are connected, retrieve and show current user list from target chat client negotiator
                self.userList = self.selectedNegotiator.listUsers()
                sublime.active_window().show_quick_panel(self.userList, self.connectToUser)
        elif userIdx > -1:
            if sessions.has_key(self.selectedNegotiator.str()) and sessions[self.selectedNegotiator.str()].has_key(self.userList[userIdx]):
                # TODO status bar: already have a session for this user!
                return
            else:
                # have a specified user, lets open a collaboration session!
                logger.debug('Opening collaboration session with user %s on client %s' % (self.userList[userIdx], self.selectedNegotiator.str()))
                session = self.selectedNegotiator.negotiateSession(self.userList[userIdx])

    def openSession(self, session):
        protocolSessions = None
        # if we dont have a selected negotiator then the session was not initiated by us, so
        # search for the negotiator that knows about the initiating peer
        if self.selectedNegotiator == None:
            for negotiatorInstance in negotiatorInstances.values():
                if session.sharingWithUser in negotiatorInstance.listUsers():
                    self.selectedNegotiator = negotiatorInstance
                    break
        if sessions.has_key(self.selectedNegotiator.str()):
            protocolSessions = sessions[self.selectedNegotiator.str()]
        else:
            protocolSessions = {}
        protocolSessions[session.str()] = session
        sessions[self.selectedNegotiator.str()] = protocolSessions
        self.newSession = session

    def shareView(self, idx=None):
        if idx == None:
            views = sublime.active_window().views()
            self.viewsByName = {}
            self.viewNames = []
            for view in views:
                if view.file_name() == None:
                    name = 'no-file-name %d' % view.id()
                    self.viewsByName[name] = view
                    self.viewNames.append(name)
                else:
                    self.viewsByName[view.file_name()] = view
                    self.viewNames.append(view.file_name())
            sublime.active_window().show_quick_panel(self.viewNames, self.shareView)
        else:
            if idx >= -1:
                chosenViewName = self.viewNames[idx]
                chosenView = self.viewsByName[chosenViewName]
                self.newSession.startCollab(chosenView)
                sessionsByViewId[chosenView.id()] = self.newSession
            else:
                # TODO perhaps send a "decided not to share anything" message out?
                self.newSession.disconnect()
                self.newSession = None
            self.viewNames = None
            self.viewsByName = None

    def addSharedView(self, sessionWithView):
        sessionsByViewId[sessionWithView.view.id()] = sessionWithView

    def acceptSessionRequest(self, deferredOnNegotiateCallback, username):
        # self.deferredOnNegotiateCallback = deferredOnNegotiateCallback
        acceptSession = sublime.ok_cancel_dialog('%s wants to collaborate with you!' % username)
        deferredOnNegotiateCallback.callback(acceptSession)
        # self.acceptOrReject = ['%s wants to collaborate with you!' % username, 'No thanks!']
        # sublime.set_timeout(self.doAcceptOrRejectSession, 1000)

    # def doAcceptOrRejectSession(self):
    #     sublime.active_window().show_quick_panel(self.acceptOrReject, self.deferredOnNegotiateCallback.callback)

    def showSessions(self, idx=None):
        if idx == None:
            sessionList = []
            for client in sessions.keys():
                for user in sessions[client].keys():
                    if sessions[client][user].state == STATE_CONNECTED:
                        sessionList.append('%s -> %s' % (client, user))
            if len(sessionList) == 0:
                sessionList = ['*** No Active Sessions ***']
            sublime.active_window().show_quick_panel(sessionList, self.showSessions)

    def killHostedSession(self, protocol, username):
        sessionsLock.acquire()
        if sessions[protocol].has_key(username):
            toKill = sessions[protocol].pop(username)
            logger.debug('Cleaning up state hosted session with %s' % username)
            toKill.state = STATE_REJECT_TRIGGERED_DISCONNECTING
            toKill.disconnect()
        sessionsLock.release()

    def endSession(self, idx=None):
        if idx == None:
            self.killList = []
            for client in sessions.keys():
                for user in sessions[client].keys():
                    self.killList.append('%s -> %s' % (client, user))
            if len(self.killList) == 0:
                self.killList = ['*** No Active Sessions ***']
            sublime.active_window().show_quick_panel(self.killList, self.endSession)
        elif idx > -1:
            clientAndUser = self.killList[idx]
            if clientAndUser == '*** No Active Sessions ***':
                return
            client, user = clientAndUser.split(' -> ')
            logger.info('Closing session with user %s on chat %s' % (user, client))
            sessionToKill = sessions[client].pop(user)
            sessionToKill.disconnect()

    def connectChat(self, clientIdx=None):
        if clientIdx == None:
            self.chatClientKeys = chatClientConfig.keys()
            for connectedKey in negotiatorInstances.keys():
                if not negotiatorInstances[connectedKey].connectionFailed:
                    self.chatClientKeys.remove(connectedKey)
            if len(self.chatClientKeys) > 0:
                self.chatClientKeys.append('*** ALL ***')
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.connectChat)
        elif clientIdx > -1:
            targetClient = self.chatClientKeys[clientIdx]
            if targetClient == '*** ALL ***':
                connectAllChat()
            elif not negotiatorInstances.has_key(targetClient):
                logger.info('Connecting to chat %s' % targetClient)
                negotiatorInstances[targetClient] = negotiatorFactoryMap[targetClient.split('|', 1)[0]]()
                negotiatorInstances[targetClient].connect(**chatClientConfig[targetClient])
            else:
                logger.info('Already connected to chat %s' % targetClient)

    def disconnectChat(self, clientIdx=None):
        if clientIdx == None:
            self.chatClientKeys = negotiatorInstances.keys()
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.disconnectChat)
        elif clientIdx > -1:
            negotiatorInstances.pop(self.chatClientKeys[clientIdx]).disconnect()

    def on_selection_modified(self, view):
        if sessionsByViewId.has_key(view.id()):
            session = sessionsByViewId[view.id()]
            if session.state == STATE_CONNECTED:
                session.sendSelectionUpdate(view.sel())

    # def on_modified(self, view):
    #     print view.command_history(0)
