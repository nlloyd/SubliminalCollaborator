import sublime, sublime_plugin
import threading
import logging
import time
from oyoyo.client import IRCClient 
from oyoyo.cmdhandler import DefaultCommandHandler  

def connect_callback(cli):
    # Join the channel '#subliminalcollaborator'
    time.sleep(10)
    helpers.join(cli, "#subliminalcollaborator")

class MyHandler(DefaultCommandHandler):
    def privmsg(self, nick, chan, msg):
        print "%s in %s said: %s" % (nick, chan, msg)

cli = IRCClient(MyHandler, host="irc.pearsoncmg.com", port=6667, nick="subliminal_nick",
         passwd='my9pv',
         connect_cb=None,
         blocking=True)

loop = True

class IRCClientThread(threading.Thread): 
    def __init__(self, irc_client):
        self.client = irc_client
        threading.Thread.__init__(self)

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        conn = self.client.connect()
        while loop:
#         print "LOOP"   
         conn.next()

irc_thread = IRCClientThread(cli)

def launch():
    irc_thread.start()

def kill():
    loop = False
    irc_thread.join()

class IrcSandboxCommand(sublime_plugin.TextCommand):
    def run(self, view):
        launch()

class KillIrcCommand(sublime_plugin.TextCommand):
    def run(self, view):
        kill()