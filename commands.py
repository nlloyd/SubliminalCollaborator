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
import sublime
platform = sublime.platform()
arch = sublime.arch()
sys.path.insert(0, os.path.join(libs_path, platform, arch))

# --- configure logging system --- #
import logging
import logging.config

logging.config.fileConfig(os.path.join(__path__, 'logging.cfg'), disable_existing_loggers=False)
# --- ------------------------ --- #

logger = logging.getLogger("SubliminalCollaborator")

# wrapper function to the entrypoint into the sublime main loop
def callInSublimeLoop(funcToCall):
    sublime.set_timeout(funcToCall, 0)

# dirty hack: in case zope is already imported by another plugin, clear the module cache reference
# otherwise zope.interface will not be imported in here
if 'zope' in sys.modules:
    del sys.modules['zope']

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
from sub_collab.peer import base as pi
from sub_collab import common, registry, status_bar
from sub_collab import event as collab_event
from sub_collab.peer import base
from twisted.internet import reactor
from zope.interface import implements
import threading, logging, time, shutil, fileinput, re, functools


# map of protocol name to negotiator constructor
NEGOTIATOR_CONSTRUCTOR_MAP = {
    'irc': irc.IRCNegotiator
}

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
sessionsLock = threading.Lock()
# global for the current active view... because sublime.active_window().active_view() ignores the console view
globalActiveView = None


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
            for session in registry.listSessions():
                if session.state == pi.STATE_DISCONNECTED:
                    logger.info('Cleaning up dead session: %s' % session.str())
                    registry.removeSession(session)
            sessionsLock.release()
            time.sleep(5.0)


if not 'SESSION_CLEANUP_THREAD' in globals():
    SESSION_CLEANUP_THREAD = SessionCleanupThread()
    SESSION_CLEANUP_THREAD.start()


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
    for protocol, acctDetails in list(accts.items()):
        if protocol == 'connect_all_on_startup':
            CONNECT_ALL_ON_STARTUP = acctDetails
            continue
        for acctDetail in acctDetails:
            negotiator = registry.addOrUpdateNegotiator(protocol, acctDetail, NEGOTIATOR_CONSTRUCTOR_MAP)
            loadedNegotiators[negotiator[0]] = negotiator[1]
    # search for any configurations in the registry NOT found in the latest config file data
    for existingNegotiator in registry.listNegotiatorKeys():
        if existingNegotiator not in loadedNegotiators:
            registry.removeNegotiator(existingNegotiator)


def connectAllChat():
    logger.info('Connecting to all configured chat servers')
    for key, negotiator in registry.iterNegotiatorEntries():
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
                % '|'.join(list(self.proxiedCommands.keys())))
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

    implements(common.Observer)

    def __init__(self):
        sublime_plugin.ApplicationCommand.__init__(self)
        sublime_plugin.EventListener.__init__(self)
        status_bar.status_message('ready')


    def run(self, task):
        method = getattr(self, task, None)
        try:
            if method is not None:
                # logger.debug('running collaborate task %s' % task)
                method()
            else:
                logger.error('unknown plugin task %s' % task)

        except:
            logger.error('Unexpected exception when trying to run CollaborateCommand.%s(..): %s' % (task, str(sys.exc_info()),))


    #***** plugin commands *****#

    def connectToChat(self, clientIdx=None):
        if clientIdx == None:
            self.chatClientKeys = []
            for negotiatorKey, negotiator in registry.iterNegotiatorEntries():
                if not negotiator.isConnected():
                    self.chatClientKeys.append(negotiatorKey)
            if len(self.chatClientKeys) > 0:
                self.chatClientKeys.append('*** ALL ***')
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.connectToChat)
        elif clientIdx > -1:
            targetNegotiatorKey = self.chatClientKeys[clientIdx]
            if targetNegotiatorKey == '*** ALL ***':
                connectAllChat()
                for negotiator in registry.iterNegotiators():
                    negotiator.addObserver(self)
            elif not registry.getNegotiator(targetNegotiatorKey).isConnected():
                logger.info('Connecting to chat %s' % targetNegotiatorKey)
                negotiator = registry.getNegotiator(targetNegotiatorKey)
                negotiator.addObserver(self)
                negotiator.connect()
            else:
                logger.info('Already connected to chat %s' % targetNegotiatorKey)


    def disconnectFromChat(self, clientIdx=None):
        if clientIdx == None:
            self.chatClientKeys = []
            for negotiatorKey, negotiator in registry.iterNegotiatorEntries():
                if negotiator.isConnected():
                    self.chatClientKeys.append(negotiatorKey)
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.disconnectFromChat)
        elif clientIdx > -1:
            registry.getNegotiator(self.chatClientKeys[clientIdx]).disconnect()


    def showConnectedChats(self, clientIdx=None):
        if clientIdx == None:
            self.chatClientKeys = []
            for negotiatorKey, negotiator in registry.iterNegotiatorEntries():
                if negotiator.isConnected():
                    self.chatClientKeys.append(negotiatorKey)
            if len(self.chatClientKeys) == 0:
                self.chatClientKeys = ['*** No Active Chat Connections ***']
            sublime.active_window().show_quick_panel(self.chatClientKeys, self.showConnectedChats)
        else:
            if hasattr(self, 'chatClientKeys'):
                del self.chatClientKeys

    #***************************#


    def update(self, event, producer, data=None):
        if event == collab_event.INCOMING_SESSION_REQUEST:
            logger.debug('incoming session request: ' + str(data))
            username = data[0]
            # someone wants to collaborate with you! do you want to accept?
            acceptRequest = sublime.ok_cancel_dialog(username + ' wants to collaborate with you!')
            if acceptRequest == True:
                producer.acceptSessionRequest(data[0], data[1], data[2])
            else:
                producer.rejectSessionRequest(data[0])
        elif event == collab_event.ESTABLISHED_SESSION:
            logger.debug('session established, opening view selector')
            self.chooseView(session=producer)
        elif event == collab_event.FAILED_SESSION:
            pass
            #todo error window popup


    def openSession(self):
        """
        Start the chain of events to open a new session with a peer.
        Stores the list of negotiator keys for selection reference in case the configuration
        changes mid-selection.
        """
        self.negotiatorKeys = registry.listNegotiatorKeys()
        sublime.active_window().show_quick_panel(self.negotiatorKeys, self.chooseNegotiator)


    def chooseNegotiator(self, negotiatorKeyIdx=None):
        """
        View callback to select a negotiator client in order to choose a user.
        Returns if negotiatorKeyIdx is not provided.
        Default value of None for negotiatorKeyIdx provided to avoid exceptions.
        """
        if negotiatorKeyIdx is None or (negotiatorKeyIdx < 0):
            # if negotiatorKeyIdx < 0 then someone changed their mind, cleanup
            if self.negotiatorKeys:
                del self.negotiatorKeys
            return
        chosenNegotiatorKey = self.negotiatorKeys[negotiatorKeyIdx]
        del self.negotiatorKeys
        if registry.hasNegotiator(chosenNegotiatorKey):
            logger.debug('selecting peer from ' + chosenNegotiatorKey)
            self.choosePeer(negotiator=registry.getNegotiator(chosenNegotiatorKey))
        else:
            err_msg = 'No negotiator found named ' + chosenNegotiatorKey
            logger.error(err_msg)
            sublime.error_message(err_msg)


    def choosePeer(self, peerIdx=None, negotiator=None):
        """
        View callback to select a peer connected through a given chat negotiator.
        """
        if negotiator:
            self.chosenNegotiator = negotiator
            self.chosenNegotiator.addObserver(self)
            self.peerList = self.chosenNegotiator.listUsers()
            sublime.active_window().show_quick_panel(self.peerList, self.choosePeer)
        elif peerIdx is None or (peerIdx < 0):
            # if peerIdx < 0 then someone changed their mind, cleanup
            if hasattr(self, 'chosenNegotiator'):
                del self.chosenNegotiator
            if hasattr(self, 'peerList'):
                del self.peerList
            return
        else:
            chosenPeer = self.peerList[peerIdx]
            chosenNegotiator = self.chosenNegotiator
            del self.peerList
            del self.chosenNegotiator
            logger.debug('request to open session with %s through %s' % (chosenPeer, chosenNegotiator.getId()))
            chosenNegotiator.negotiateSession(chosenPeer)


    def chooseView(self, viewIdx=None, session=None):
        if session:
            self.chosenSession = session
            self.chosenSession.addObserver(self)
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
            sublime.active_window().show_quick_panel(self.viewNames, self.chooseView)
        elif viewIdx is None or (viewIdx < 0):
            # TODO perhaps send a "decided not to share anything" message out?
            if self.chosenSession:
                self.chosenSession.disconnect()
                del self.chosenSession
            if hasattr(self, 'viewNames'):
                del self.viewNames
            if hasattr(self, 'viewsByName'):
                del self.viewsByName
            return
        else:
            chosenViewName = self.viewNames[viewIdx]
            chosenView = self.viewsByName[chosenViewName]
            chosenSession = self.chosenSession
            del self.viewNames
            del self.viewsByName
            del self.chosenSession
            logger.debug('sharing %s with %s' % (chosenViewName, chosenSession,))
            registry.registerSessionByView(chosenView, chosenSession)
            chosenSession.startCollab(chosenView)
            

    def showSessions(self, idx=None, sessionCallback=None):
        if idx == None:
            self.activeSessions = registry.listSessions()
            self.sessionList = []
            for session in self.activeSessions:
                sessionLabel = '%s -> %s' % (session.getParentNegotiatorKey(), session.str())
                if hasattr(session, 'view'):
                    if session.view.file_name():
                        sessionLabel += ' (%s)' % os.path.basename(session.view.file_name())
                    else:
                        sessionLabel += ' (%s)' % session.view.name()
                self.sessionList.append(sessionLabel)
            if len(self.sessionList) == 0:
                self.sessionList = ['*** No Active Sessions ***']
            sublime.active_window().show_quick_panel(self.sessionList, self.showSessions)
        elif (idx > -1) and (sessionCallback is not None):
           sessionCallback(self.sessionList[idx])
        if hasattr(self, 'activeSessions'):
            del self.activeSessions
        if hasattr(self, 'sessionList'):
            del self.sessionList


    def closeSession(self, idx=None):
        if idx == None:
            self.activeSessions = registry.listSessions()
            self.killList = []
            for session in self.activeSessions:
                sessionLabel = '%s -> %s' % (session.getParentNegotiatorKey(), session.str())
                if hasattr(session, 'view'):
                    if session.view.file_name():
                        sessionLabel += ' (%s)' % os.path.basename(session.view.file_name())
                    else:
                        sessionLabel += ' (%s)' % session.view.name()
                self.killList.append(sessionLabel)
            if len(self.killList) == 0:
                self.killList = ['*** No Active Sessions ***']
            logger.debug('Listing active sessions available to close')
            sublime.active_window().show_quick_panel(self.killList, self.closeSession)
        elif idx > -1:
            if (len(self.killList) == 1) and (self.killList[0] == '*** No Active Sessions ***'):
                return
            logger.info('Closing session: ' + self.killList[idx])
            sessionToKill = self.activeSessions[idx]
            # cleanup regardless in case something goes wrong
            del self.activeSessions
            del self.killList
            # now try and terminate the session
            sessionToKill.disconnect()


    def swapRole(self, session=None):
        # if we are called with a session passed... typically as a callback from user selection
        swapping_session = None
        if (session is not None) and (session.state == pi.STATE_CONNECTED):
            swapping_session = session
        else:
            # swap on the active view? otherwise ask for which shared view
            view = sublime.active_window().active_view()
            session = registry.getSessionByView(view)
            if view and session:
                if session.state == pi.STATE_CONNECTED:
                    swapping_session = session
            else:
                self.showSessions(sessionCallback=self.swapRole)
                return
        swapping_session.swapRole()


    def on_selection_modified(self, view):
        # if view.file_name():
        # print('new selection: %s' % view.sel())
        session = registry.getSessionByView(view)
        if session:
            if (session.state == pi.STATE_CONNECTED) and not session.isProxyEventPublishing:
                logger.debug('selection: %s' % view.sel())
                session.sendSelectionUpdate(view.sel())


    def on_modified(self, view):
        # print(view.command_history(0, False))
        # print(view.command_history(-1, False))
        session = registry.getSessionByView(view)
        if session:
            if (session.state == pi.STATE_CONNECTED) and (session.role == pi.HOST_ROLE):
                command = view.command_history(0, False)
                lastCommand = session.lastViewCommand
                session.lastViewCommand = command
                payload = ''
                # handle history-capturable edit commands on this view
                if command[0] == 'insert':
                    # because of the way the insert commands are captured in the command_history
                    # this seems to be the most sensible way to handle this... grab latest character
                    # inserted and send it... not most efficient but it is a start
                    if command[0] == lastCommand[0]:
                        chars = command[1]['characters']
                        lastChars = lastCommand[1]['characters']
                        if chars.startswith(lastChars):
                            payload = chars.replace(lastChars, '', 1)
                        else:
                            payload = chars
                    else:
                        payload = command[1]['characters']
                    session.sendEdit(pi.EDIT_TYPE_INSERT, payload)
                elif command[0] ==  'insert_snippet':
                    payload = command[1]['contents']
                    session.sendEdit(pi.EDIT_TYPE_INSERT_SNIPPET, payload)
                elif command[0] == 'left_delete':
                    session.sendEdit(pi.EDIT_TYPE_LEFT_DELETE, payload)
                elif command[0] == 'right_delete':
                    session.sendEdit(pi.EDIT_TYPE_RIGHT_DELETE, payload)
                elif command[0] == 'paste':
                    payload = sublime.get_clipboard()
                    session.sendEdit(pi.EDIT_TYPE_PASTE, payload)


# ===== EditCommandProxyCommand ===== #


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
#         session = registry.getSessionByView(globalActiveView)
#         if session:
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
