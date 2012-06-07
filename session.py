# All of SubliminalCollaborator is licensed under the MIT license.

#   Copyright (c) 2012 Nick Lloyd, Frank Papineau, Rippa Gasparyan

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
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
import sublime, sublime_plugin
import threading
import logging
from oyoyo import helpers
from oyoyo.client import IRCClient 
from oyoyo.cmdhandler import DefaultCommandHandler

class CollabMsgHandler(DefaultCommandHandler):
    tgt_nick = 'nick'

    def privmsg(self, nick, chan, msg):
        print 'msg from: %s' % nick
        print 'only listening to: %s' % tgt_nick
        if nick == tgt_nick:
            print "%s in %s said: %s" % (nick, chan, msg)

    def welcome(self, *args):
        print 'connected to irc!'
        helpers.join(self.client, "#subliminalcollaborator")

class IRCClientThread(threading.Thread): 
    def __init__(self, irc_client):
        self.client = irc_client
        threading.Thread.__init__(self)

    def run(self):
        logging.basicConfig(level=logging.DEBUG)
        conn = self.client.connect()
        while True:
            conn.next()

settings = sublime.load_settings('Preferences.sublime-settings')
# {
#     'sublinimal_collaborator_config': {
#         'irc': {
#             'host': "irc.pearsoncmg.com",
#             'port': 6667,
#             'pwd': "my9pv",
#             'nick': "subliminal_nick"
#         }
#     }
# }
collab_config = settings.get('subliminal_collaborator_config', None)

class CollabSessionCommand(sublime_plugin.WindowCommand):
    irc_client = None
    irc_thread = None
    session_view = None
    co_collab_nick = None

    def init(self):
        self.irc_client = IRCClient(CollabMsgHandler, host="irc.pearsoncmg.com", port=6667, nick="subliminal_nick",
                                passwd='my9pv', blocking=True)
        self.irc_thread = IRCClientThread(self.irc_client)
        self.irc_thread.start()

    def run(self):
        if not self.irc_client and not self.irc_thread:
            print 'oh nos! initing irc session'
            self.init()
        self.window.show_quick_panel(['Share active view (default)', 'Share other view...'], self.view_to_share)

    def view_to_share(self, choice_idx):
        if choice_idx < 1:
            self.session_view = self.window.active_view()
            self.window.show_input_panel('Share with (IRC nick):', 'sumdumguy', self.with_whom, None, None)
        else:
            self.current_views = []
            self.current_view_names = []
            for view in self.window.views():
                self.current_views.append(view)
                self.current_view_names.append(view.file_name())

            self.window.show_quick_panel(self.current_view_names, self.choose_this_view)

    def choose_this_view(self, view_idx):
        if view_idx >= 0:
            self.session_view = self.current_views[view_idx]
            self.window.show_input_panel('Share with (IRC nick):', 'sumdumguy', self.with_whom, None, None)

    def with_whom(self, irc_nick):
        self.co_collab_nick = irc_nick
        self.irc_client.command_handler.tgt_nick = irc_nick

    def start_session(self):
        print 'you chose to share %s, with %s' % (self.session_view.file_name(), self.irc_client.command_handler.tgt_nick)
        helpers.msg(self.irc_client, self.co_collab_nick, '!want.bacon?')



# class CollabSessionEventHandler(sublime_plugin.EventListener):

#     def on_modified(self, view):
#         # TODO: send change events to the partner
#         if view.file_name():
#             for region in view.sel():
#                 print region.begin()
#             print '!!! command %s modified: %s' % (view.command_history(0, True), view.file_name())

#     def on_selection_modified(self, view):
#         if view.file_name():
#             for region in view.sel():
#                 print 'sel_mod: %d' % region.begin()
