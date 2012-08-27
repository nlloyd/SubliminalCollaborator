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
import threading

class ReactorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        if not reactor.running:
            print "[SubliminalCollaborator: starting the event reactor on a thread]"
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
        acctConfig = acctConfigAlt
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


# COMMANDS:
# - start session
# - show active sessions
# - close session
# - disconnect from chat

class SubCollaborateCommand(sublime_plugin.ApplicationCommand):

    def run(self, command):
        # command is one of: start-session, show-sessions, close-session, disconnect-chat
        pass
