import sublime, sublime_plugin
import threading
import time
import logging
from oyoyo import helpers
from oyoyo.client import IRCClient 
from oyoyo.cmdhandler import DefaultCommandHandler

logging.basicConfig(level=logging.ERROR)

# def connect_callback(cli):
#     # Join the channel '#subliminalcollaborator'
#     helpers.join(cli, "#subliminalcollaborator")

# tgt_nick = 'nick'

class MyHandler(DefaultCommandHandler):
    tgt_nick = 'nick'

    def privmsg(self, nick, chan, msg):
        # print 'msg from: %s' % nick
        # print 'only listening to: %s' % tgt_nick
        # if nick == tgt_nick:
        print "%s in %s, %d said: %s" % (nick, chan, len(msg), msg)

    def welcome(self, *args):
        print 'we have been welcomed!'
        helpers.join(self.client, "#subliminalcollaborator")

cli = IRCClient(MyHandler, host="irc.pearsoncmg.com", port=6667, nick="asdf",
         passwd='my9pv',
         blocking=True)

really_big_msg = 'abcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcdeabcde'


class IRCClientThread(threading.Thread): 
    def __init__(self, irc_client):
        self.client = irc_client
        self.live = True
        threading.Thread.__init__(self)

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        conn = self.client.connect()
        while self.live:
            conn.next()

irc_thread = IRCClientThread(cli)

def launch():
    irc_thread.start()
    time.sleep(5)
    helpers.msg(cli, 'subliminal_nick', really_big_msg)

def kill():
    irc_thread.loop = False
    helpers.quit(cli)

class IrcSandboxCommand(sublime_plugin.TextCommand):
    def run(self, view):
        launch()

class KillIrcCommand(sublime_plugin.TextCommand):
    def run(self, view):
        kill()

class UpdateNickCommand(sublime_plugin.TextCommand):
    def run(self, view):
        if tgt_nick == 'nick':
            tgt_nick = 'Rippa'
        elif tgt_nick == 'Rippa':
            tgt_nick = 'nick'
