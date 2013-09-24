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
import os
import platform
import sys

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

# --- configure logging system --- #
import logging
import logging.config

logging.config.fileConfig('logging.cfg', disable_existing_loggers=False)
# --- ------------------------ --- #

logger = logging.getLogger("SubliminalCollaborator")

import sublime

# wrapper function to the entrypoint into the sublime main loop
def callInSublimeLoop(funcToCall):
    sublime.set_timeout(funcToCall, 0)

# --- install and start the twisted reactor, if it hasn't already be started --- #
from twisted.internet.error import ReactorAlreadyInstalledError, ReactorAlreadyRunning, ReactorNotRestartable

reactorAlreadyInstalled = False
try:
    from twisted.internet import _threadedselect
    _threadedselect.install()
except ReactorAlreadyInstalledError:
    reactorAlreadyInstalled = True

from twisted.internet import reactor

try:
    reactor.interleave(callInSublimeLoop, installSignalHandlers=False)
except ReactorAlreadyRunning:
    reactorAlreadyInstalled = True
except ReactorNotRestartable:
    reactorAlreadyInstalled = True

if reactorAlreadyInstalled:
    logger.debug('twisted reactor already installed')
    if type(reactor) != _threadedselect.ThreadedSelectReactor:
        logger.warn('unexpected reactor type installed: %s, it is best to use twisted.internet._threadedselect!' % type(reactor))
else:
    logger.debug('twisted reactor installed and running')
# --- --------------------------------------------------------------------- --- #

import sublime_plugin
from sub_collab.negotiator import irc
from sub_collab.peer import interface as pi
from sub_collab import registry, status_bar
from sub_collab.peer import base
from twisted.internet import reactor
import threading, logging, time, shutil, fileinput, re, functools

#*** globals for preferences and session variables ***#
# config dictionary, key is protocol:host:username, value is config dict
# chatClientConfig = {}
CONNECT_ALL_ON_STARTUP = False
# # key is same as config dictionary, values are live negotiator instances
# negotiatorInstances = {}
# # sessions by chatClient
# sessions = {}
# # sessions by view id
# sessionsByViewId = {}
# sessionsLock = threading.Lock()
# global for the current active view... because sublime.active_window().active_view() ignores the console view
globalActiveView = None


# class SessionCleanupThread(threading.Thread):
#     def __init__(self):
#         threading.Thread.__init__(self)

#     def run(self):
#         global sessions
#         global sessionsByViewId
#         global sessionsLock
#         time.sleep(5.0)
#         # runs for as long as the reactor is running
#         while reactor.running:
#             sessionsLock.acquire()
#             for sessionsKey, protocolSessions in sessions.items():
#                 for sessionKey, session in protocolSessions.items():
#                     if session.state == pi.STATE_DISCONNECTED:
#                         deadSession = sessions[sessionsKey].pop(sessionKey)
#                         logger.info('Cleaning up dead session: %s' % deadSession.str())
#             for viewId, session in sessionsByViewId.items():
#                 if session.state == pi.STATE_DISCONNECTED:
#                     if session.view != None:
#                         sublime.set_timeout(functools.partial(session.view.set_read_only, False), 0)
#                     sessionsByViewId.pop(viewId)
#             sessionsLock.release()
#             for negotiatorKey, negotiator in negotiatorInstances.items():
#                 if negotiator.isConnected() == False:
#                     negotiatorInstances.pop(negotiatorKey)
#                     logger.info('Cleaning up disconnected negotiator %s' % negotiatorKey)
#             time.sleep(5.0)


# if not 'SESSION_CLEANUP_THREAD' in globals():
#     SESSION_CLEANUP_THREAD = SessionCleanupThread()
#     SESSION_CLEANUP_THREAD.start()


def loadConfig():
    global CONNECT_ALL_ON_STARTUP
    acctConfig = sublime.load_settings('Accounts.sublime-settings')
    accts = acctConfig.get('subliminal_collaborator')
    logger.info('loading configuration from Accounts.sublime-settings')
    if not accts:
        logger.error('No configuration found!')
        return
    acctConfig.clear_on_change('subliminal_collaborator')
    acctConfig.add_on_change('subliminal_collaborator', loadConfig)
    loadedNegotiators = {}
    for protocol, acctDetails in accts.items():
        if protocol == 'connect_all_on_startup':
            CONNECT_ALL_ON_STARTUP = acctDetails
            continue
        for acctDetail in acctDetails:
            negotiator = registry.addOrUpdateNegotiator(protocol, acctDetail)
            loadedNegotiators[negotiator[0]] = negotiator[1]
    # search for any configurations in the registry NOT found in the latest config file data
    for existingNegotiator in registry.listNegotiatorKeys():
        if not loadedNegotiators.has_key(existingNegotiator):
            registry.removeNegotiator(existingNegotiator)


def connectAllChat():
    logger.info('Connecting to all configured chat servers')
    for key, negotiator in registry.listNegotiatorEntries():
        logger.info('Connecting to chat %s' % key)
        if not negotiator.isConnected():
            negotiator.connect()


loadConfig()

if CONNECT_ALL_ON_STARTUP:
    connectAllChat()


# ===== OpenSublimeSettingsCommand ===== #


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


# ===== InstallMenuProxyCommand ===== #


class InstallMenuProxyCommand(sublime_plugin.WindowCommand):
    proxiedCommands = {
        'undo': 'Undo Insert Characters',
        'redo_or_repeat': 'Repeat Instert Characters',
        'soft_undo': 'Undo Insert Characters',
        'soft_redo': 'Soft Redo',
        'copy': 'Copy',
        'cut': 'Cut'
    }
    
    def run(self):
        logger.info('Installing menu command proxy configuration')
        logger.info('Backing up default Menu.sublime-menu to ~/.subliminal_collaborator')
        if not os.path.exists(os.path.expanduser(os.path.join('~', '.subliminal_collaborator'))):
            os.mkdir(os.path.expanduser(os.path.join('~','.subliminal_collaborator')))
        shutil.copy(os.path.join(sublime.packages_path(), 'Default', 'Main.sublime-menu'), \
            os.path.expanduser(os.path.join('~', '.subliminal_collaborator', 'Main.sublime-menu.backup')))
        self.installProxyEntries()


    def is_enabled(self):
        return not os.path.exists(os.path.join(os.getcwd(), 'menu_backup', 'Main.sublime-menu.backup'))

    def installProxyEntries(self):
        if not hasattr(self, 'command_pattern'):
            self.command_pattern = re.compile(r'^(\s*\{\s*"command":\s*")(%s)("\s*)(,\s*"mnemonic":\s*"[a-zA-Z]"\s*|)(\})(,|)(\s*)$' \
                % '|'.join(self.proxiedCommands.keys()))
        logger.info('Installing proxy commands to Main.sublime-menu')
        os.rename(os.path.join(sublime.packages_path(), 'Default','Main.sublime-menu'), os.path.join(sublime.packages_path(), 'Default','Main.sublime-menu.tmp'))
        for line in fileinput.FileInput(os.path.join(sublime.packages_path(), 'Default','Main.sublime-menu.tmp'), inplace=1):
            caption = ''
            matchBits = self.command_pattern.match(line)
            if matchBits:
                caption = self.proxiedCommands[matchBits.group(2)]
            line = self.command_pattern.sub(r'\1edit_command_proxy\3, "caption": "%s", "args": { "real_command": "\2" }\4\5\6\7' % caption, line)
            sys.stdout.write(line)
        os.rename(os.path.join(sublime.packages_path(), 'Default','Main.sublime-menu.tmp'), os.path.join(sublime.packages_path(), 'Default','Main.sublime-menu'))


# ===== UninstallMenuProxyCommand ===== #


class UninstallMenuProxyCommand(sublime_plugin.WindowCommand):

    def run(self):
        logger.info('Uninstalling menu command proxy configuration')
        logger.info('Restoring default Menu.sublime-menu')
        shutil.copy(os.path.expanduser(os.path.join('~', '.subliminal_collaborator', 'Main.sublime-menu.backup')), \
            os.path.join(sublime.packages_path(), 'Default', 'Main.sublime-menu'))
        shutil.rmtree(os.path.expanduser(os.path.join('~', '.subliminal_collaborator')))
        if not os.path.exists(os.path.expanduser(os.path.join('~', '.subliminal_collaborator', 'Main.sublime-menu.backup'))):
            logger.info('Successfully restored default Menu.sublime-menu')
        else:
            logger.error('Failed to restore default Menu.sublime-menu')

    def is_enabled(self):
        return os.path.exists(os.path.expanduser(os.path.join('~', '.subliminal_collaborator', 'Main.sublime-menu.backup')))


# ===== CollaborateCommand ===== #


class CollaborateCommand(sublime_plugin.ApplicationCommand, sublime_plugin.EventListener):

    def __init__(self):
        sublime_plugin.ApplicationCommand.__init__(self)
        sublime_plugin.EventListener.__init__(self)

# class CollaborateCommand(sublime_plugin.ApplicationCommand, sublime_plugin.EventListener):
#     chatClientKeys = []
#     sessionKeys = []
#     userList = []
#     selectedNegotiator = None

#     def __init__(self):
#         sublime_plugin.ApplicationCommand.__init__(self)
#         irc.IRCNegotiator.negotiateCallback = self.openSession
#         irc.IRCNegotiator.onNegotiateCallback = self.acceptSessionRequest
#         irc.IRCNegotiator.rejectedOrFailedCallback = self.killHostedSession
#         base.BasePeer.peerConnectedCallback = self.shareView
#         base.BasePeer.peerRecvdViewCallback = self.addSharedView
#         base.BasePeer.acceptSwapRole = self.acceptSwapRole
#         status_bar.status_message('ready')

#     def run(self, task):
#         method = getattr(self, task, None)
#         try:
#             if method is not None:
#                 # logger.debug('running collaborate task %s' % task)
#                 method()
#             else:
#                 logger.error('unknown plugin task %s' % task)

#         except:
#             logger.error(sys.exc_info())

#     def startSession(self):
#         self.chatClientKeys = chatClientConfig.keys()
#         sublime.active_window().show_quick_panel(self.chatClientKeys, self.selectUser)

#     def selectUser(self, clientIdx):
#         if clientIdx < 0:
#             return
#         targetClient = self.chatClientKeys[clientIdx]
#         logger.debug('select user from client %s' % targetClient)
#         self.selectedNegotiator = None
#         if negotiatorInstances.has_key(targetClient):
#             logger.debug('Found negotiator for %s, using it' % targetClient)
#             self.selectedNegotiator = negotiatorInstances[targetClient]
#         else:
#             logger.debug('No negotiator for %s, creating one' % targetClient)
#             self.selectedNegotiator = negotiatorFactoryMap[targetClient.split('|', 1)[0]]()
#             negotiatorInstances[targetClient] = self.selectedNegotiator
#             self.selectedNegotiator.connect(**chatClientConfig[targetClient])
#         # use our negotiator to connect to the chat server and wait to grab the userlist
#         self.retryCounter = 0
#         self.connectToUser()

#     def connectToUser(self, userIdx=None):
#         if userIdx == None:
#             if not self.selectedNegotiator.isConnected():
#                 if self.retryCounter >= 30:
#                     logger.warn('Failed to connect client %s' % self.selectedNegotiator.str())
#                 else:
#                     # increment retry count... 
#                     self.retryCounter = self.retryCounter + 1
#                     logger.debug('Not connected yet to client %s, recheck counter: %d' % (self.selectedNegotiator.str(), self.retryCounter))
#                     sublime.set_timeout(self.connectToUser, 1000)
#             else:
#                 # we are connected, retrieve and show current user list from target chat client negotiator
#                 self.userList = self.selectedNegotiator.listUsers()
#                 sublime.active_window().show_quick_panel(self.userList, self.connectToUser)
#         elif userIdx > -1:
#             if sessions.has_key(self.selectedNegotiator.str()) and sessions[self.selectedNegotiator.str()].has_key(self.userList[userIdx]):
#                 logger.debug('Already collaborating with this user!')
#                 # TODO status bar: already have a session for this user!
#                 return
#             else:
#                 # have a specified user, lets open a collaboration session!
#                 logger.debug('Opening collaboration session with user %s on client %s' % (self.userList[userIdx], self.selectedNegotiator.str()))
#                 session = self.selectedNegotiator.negotiateSession(self.userList[userIdx])

#     def openSession(self, session):
#         protocolSessions = None
#         # if we dont have a selected negotiator then the session was not initiated by us, so
#         # search for the negotiator that knows about the initiating peer
#         if self.selectedNegotiator == None:
#             for negotiatorInstance in negotiatorInstances.values():
#                 if session.sharingWithUser in negotiatorInstance.listUsers():
#                     self.selectedNegotiator = negotiatorInstance
#                     break
#         if sessions.has_key(self.selectedNegotiator.str()):
#             protocolSessions = sessions[self.selectedNegotiator.str()]
#         else:
#             protocolSessions = {}
#         protocolSessions[session.str()] = session
#         sessions[self.selectedNegotiator.str()] = protocolSessions
#         self.newSession = session

#     def shareView(self, idx=None):
#         if idx == None:
#             views = sublime.active_window().views()
#             self.viewsByName = {}
#             self.viewNames = []
#             for view in views:
#                 if view.file_name() == None:
#                     name = 'no-file-name %d' % view.id()
#                     self.viewsByName[name] = view
#                     self.viewNames.append(name)
#                 else:
#                     self.viewsByName[view.file_name()] = view
#                     self.viewNames.append(view.file_name())
#             sublime.active_window().show_quick_panel(self.viewNames, self.shareView)
#         else:
#             if idx > -1:
#                 chosenViewName = self.viewNames[idx]
#                 chosenView = self.viewsByName[chosenViewName]
#                 self.newSession.startCollab(chosenView)
#                 sessionsByViewId[chosenView.id()] = self.newSession
#             else:
#                 # TODO perhaps send a "decided not to share anything" message out?
#                 self.newSession.disconnect()
#                 self.newSession = None
#             self.viewNames = None
#             self.viewsByName = None

#     def addSharedView(self, sessionWithView):
#         sessionsByViewId[sessionWithView.view.id()] = sessionWithView

#     def acceptSessionRequest(self, deferredOnNegotiateCallback, username):
#         # self.deferredOnNegotiateCallback = deferredOnNegotiateCallback
#         acceptSession = sublime.ok_cancel_dialog('%s wants to collaborate with you!' % username)
#         deferredOnNegotiateCallback.callback(acceptSession)

#     def showSessions(self, idx=None, sessionCallback=None):
#         if idx == None:
#             sessionList = []
#             for client in sessions.keys():
#                 for user in sessions[client].keys():
#                     if sessions[client][user].state == pi.STATE_CONNECTED:
#                         sessionList.append('%s -> %s' % (client, user))
#             if len(sessionList) == 0:
#                 sessionList = ['*** No Active Sessions ***']
#             sublime.active_window().show_quick_panel(sessionList, self.showSessions)
#         elif (idx > -1) and sessionCallback is not None:
#             sessionList = []
#             for client in sessions.keys():
#                 for user in sessions[client].keys():
#                     if sessions[client][user].state == pi.STATE_CONNECTED:
#                         sessionList.append('%s -> %s' % (client, user))
#             if len(sessionList) > 0:
#                sessionCallback(sessionList[idx])

#     def swapRole(self, session=None):
#         # if we are called with a session passed... typically as a callback from user selection
#         swapping_session = None
#         if (session is not None) and (session.state == pi.STATE_CONNECTED):
#             swapping_session = session
#         else:
#             # swap on the active view? otherwise ask for which shared view
#             view = sublime.active_window().active_view()
#             if view and sessionsByViewId.has_key(view.id()):
#                 session = sessionsByViewId[view.id()]
#                 if session.state == pi.STATE_CONNECTED:
#                     swapping_session = session
#             else:
#                 self.showSessions(sessionCallback=self.swapRole)
#                 return
#         swapping_session.swapRole()

#     def acceptSwapRole(self, requestMessage):
#         return sublime.ok_cancel_dialog(requestMessage)

#     def killHostedSession(self, protocol, username):
#         sessionsLock.acquire()
#         if sessions[protocol].has_key(username):
#             toKill = sessions[protocol].pop(username)
#             logger.debug('Cleaning up hosted session with %s' % username)
#             if not toKill.state == pi.STATE_DISCONNECTED:
#                 toKill.state = pi.STATE_REJECT_TRIGGERED_DISCONNECTING
#             toKill.disconnect()
#         sessionsLock.release()

#     def endSession(self, idx=None):
#         if idx == None:
#             self.killList = []
#             for client in sessions.keys():
#                 for user in sessions[client].keys():
#                     self.killList.append('%s -> %s' % (client, user))
#             if len(self.killList) == 0:
#                 self.killList = ['*** No Active Sessions ***']
#             sublime.active_window().show_quick_panel(self.killList, self.endSession)
#         elif idx > -1:
#             clientAndUser = self.killList[idx]
#             if clientAndUser == '*** No Active Sessions ***':
#                 return
#             client, user = clientAndUser.split(' -> ')
#             logger.info('Closing session with user %s on chat %s' % (user, client))
#             sessionToKill = sessions[client].pop(user)
#             sessionToKill.disconnect()

#     def connectChat(self, clientIdx=None):
#         if clientIdx == None:
#             self.chatClientKeys = chatClientConfig.keys()
#             for connectedKey in negotiatorInstances.keys():
#                 if not negotiatorInstances[connectedKey].connectionFailed:
#                     self.chatClientKeys.remove(connectedKey)
#             if len(self.chatClientKeys) > 0:
#                 self.chatClientKeys.append('*** ALL ***')
#             sublime.active_window().show_quick_panel(self.chatClientKeys, self.connectChat)
#         elif clientIdx > -1:
#             targetClient = self.chatClientKeys[clientIdx]
#             if targetClient == '*** ALL ***':
#                 connectAllChat()
#             elif not negotiatorInstances.has_key(targetClient):
#                 logger.info('Connecting to chat %s' % targetClient)
#                 negotiatorInstances[targetClient] = negotiatorFactoryMap[targetClient.split('|', 1)[0]]()
#                 negotiatorInstances[targetClient].connect(**chatClientConfig[targetClient])
#             else:
#                 logger.info('Already connected to chat %s' % targetClient)

#     def disconnectChat(self, clientIdx=None):
#         if clientIdx == None:
#             self.chatClientKeys = negotiatorInstances.keys()
#             sublime.active_window().show_quick_panel(self.chatClientKeys, self.disconnectChat)
#         elif clientIdx > -1:
#             negotiatorInstances.pop(self.chatClientKeys[clientIdx]).disconnect()

#     def on_selection_modified(self, view):
#         # if view.file_name():
#         # print('new selection: %s' % view.sel())
#         if sessionsByViewId.has_key(view.id()):
#             session = sessionsByViewId[view.id()]
#             if (session.state == pi.STATE_CONNECTED) and not session.isProxyEventPublishing:
#                 logger.debug('selection: %s' % view.sel())
#                 session.sendSelectionUpdate(view.sel())

#     def on_modified(self, view):
#         # print(view.command_history(0, False))
#         # print(view.command_history(-1, False))
#         if sessionsByViewId.has_key(view.id()):
#             session = sessionsByViewId[view.id()]
#             if (session.state == pi.STATE_CONNECTED) and (session.role == pi.HOST_ROLE):
#                 command = view.command_history(0, False)
#                 lastCommand = session.lastViewCommand
#                 session.lastViewCommand = command
#                 payload = ''
#                 # handle history-capturable edit commands on this view
#                 if command[0] == 'insert':
#                     # because of the way the insert commands are captured in the command_history
#                     # this seems to be the most sensible way to handle this... grab latest character
#                     # inserted and send it... not most efficient but it is a start
#                     if command[0] == lastCommand[0]:
#                         chars = command[1]['characters']
#                         lastChars = lastCommand[1]['characters']
#                         if chars.startswith(lastChars):
#                             payload = chars.replace(lastChars, '', 1)
#                         else:
#                             payload = chars
#                     else:
#                         payload = command[1]['characters']
#                     session.sendEdit(pi.EDIT_TYPE_INSERT, payload)
#                 elif command[0] ==  'insert_snippet':
#                     payload = command[1]['contents']
#                     session.sendEdit(pi.EDIT_TYPE_INSERT_SNIPPET, payload)
#                 elif command[0] == 'left_delete':
#                     session.sendEdit(pi.EDIT_TYPE_LEFT_DELETE, payload)
#                 elif command[0] == 'right_delete':
#                     session.sendEdit(pi.EDIT_TYPE_RIGHT_DELETE, payload)
#                 elif command[0] == 'paste':
#                     payload = sublime.get_clipboard()
#                     session.sendEdit(pi.EDIT_TYPE_PASTE, payload)



# class EditCommandProxyCommand(sublime_plugin.ApplicationCommand, sublime_plugin.EventListener):

#     def on_load(self, view):
#         # handles initial sublime startup
#         global globalActiveView
#         globalActiveView = view

#     def on_activated(self, view):
#         global globalActiveView
#         globalActiveView = view

#     def run(self, real_command):
#         global globalActiveView
#         # print('proxying: %s' % real_command)
#         if globalActiveView == None:
#             logger.debug('no view to proxy commands to')
#             return
#         if sessionsByViewId.has_key(globalActiveView.id()):
#             session = sessionsByViewId[globalActiveView.id()]
#             session.isProxyEventPublishing = True
#             if (session.state == pi.STATE_CONNECTED) and (session.role == pi.HOST_ROLE):
#                 logger.debug('proxying: %s' % real_command)
#                 # make sure our selection is up-to-date
#                 if real_command != 'undo':
#                     session.sendSelectionUpdate(globalActiveView.sel())
#                 globalActiveView.run_command(real_command)
#                 if real_command ==  'cut':
#                     session.sendEdit(pi.EDIT_TYPE_CUT)
#                 elif real_command == 'copy':
#                     session.sendEdit(pi.EDIT_TYPE_COPY)
#                 # TODO: figure this out! for now we eat these commands
#                 # elif real_command == 'undo':
#                 #     session.sendEdit(pi.EDIT_TYPE_UNDO)
#                 # elif real_command == 'redo':
#                 #     session.sendEdit(pi.EDIT_TYPE_REDO)
#                 # elif real_command == 'redo_or_repeat':
#                 #     session.sendEdit(pi.EDIT_TYPE_REDO_OR_REPEAT)
#                 # elif real_command == 'soft_undo':
#                 #     session.sendEdit(pi.EDIT_TYPE_SOFT_UNDO)
#                 # elif real_command == 'soft_redo':
#                 #     session.sendEdit(pi.EDIT_TYPE_SOFT_REDO)
#             session.isProxyEventPublishing = False
#         else:
#             # run the command for real... not part of a session
#             globalActiveView.run_command(real_command)
