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
import time, threading

host = 'localhost'
port = 6667
username = 'subpeer'
password = 'passwd'
channel = 'subliminalcollaboration'

test_negotiator = irc.IRCNegotiator()

class NegotiatorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        test_negotiator.connect(host, port, username, password, channel=channel)

        for tries in range(10):
            time.sleep(1.0)
            if test_negotiator.isConnected():
                break

        users = test_negotiator.listUsers()
        print users
        # for user in users:
        #     if username != user:
        #         test_negotiat
        # time.sleep(30.0)
        # test_negotiator.disconnect()


# view.run_command('negotiator_test')
class NegotiatorTestCommand(sublime_plugin.TextCommand):
    thread = None

    def run(self, edit):    
        # if not reactor_thread.is_alive():
        #     reactor_thread.start()
        #     time.sleep(5.0)
        print 'running collab_test'
        # if test_negotiator.isConnected():
        #     test_negotiator.disconnect()
        if test_negotiator.isConnected():
            test_negotiator.disconnect()
        else:
            # test_negotiator.connect(host, port, username, password, channel=channel)
            # print test_negotiator.listUsers()
            self.thread = NegotiatorThread()
            self.thread.start()

