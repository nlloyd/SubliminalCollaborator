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
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHE`R
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
import sublime, sublime_plugin
import threading
import logging
import time
import re
from oyoyo import helpers
from oyoyo.client import IRCClient 
from oyoyo.cmdhandler import DefaultCommandHandler

share_view_reply_pattern = re.compile('^!!OMGYES!!([0-9]+)!!$')

class Role:
    HOST = 1
    PARTNER = 2

class CollabMessages:
    START_SHARE = '!want.bacon?'
    START_SHARE_ACK_FMT = '!!OMGYES!!%d!!'
    END_SHARE_PUBLISH = '!you.haz.teh.bacons!'
        
class CollabMsgHandler(DefaultCommandHandler):
    tgt_nick = None
    session_view = None
    session_role = None
    max_buf_size = 0
    am_recving_buffer = False
    in_queue = []
    in_queue_lock = threading.Lock()
    out_queue = []
    out_queue_lock = threading.Lock()
    chunk_lock = threading.Lock()

    def privmsg(self, nick, chan, msg):
        print 'msg from: %s' % nick
        # print msg
        # print len(nick)
        # print len(chan)
        # print len(msg)
        # print 'only listening to: %s' % tgt_nick
        
        nick_seg = None

        if nick:
            nick_seg = nick.split('!',1)[0]

        if self.tgt_nick and nick_seg == self.tgt_nick:
            if self.session_role == Role.HOST:
                ## HOST behavior
                print 'imahost'
                buffer_match = share_view_reply_pattern.match(msg)
                if buffer_match:
                    print 'sharing buffer'
                    self.max_buf_size = int(buffer_match.group(1))
                    self.share_entire_view()
                ## more msg handling here ##
            else:
                if msg == CollabMessages.END_SHARE_PUBLISH:
                    self.am_recving_buffer = False
                if self.am_recving_buffer:
                    self.in_queue_lock.acquire()
                    self.in_queue.insert(0, msg)
                    self.in_queue_lock.release()
                    sublime.set_timeout(lambda: self.publish_partner_chunk(), 100)
                    print len(msg)
                ## PARTNER behavior
                print "%s said to %s: %s" % (nick_seg, chan, msg)
        elif msg == CollabMessages.START_SHARE:
            # request from a potential host to start a session
            self.tgt_nick = nick_seg
            print 'show start session dialog'
            self.max_buf_size = 498 - (len(nick) + len(chan))
            sublime.set_timeout(lambda: self.partner_accept_session_dialog(), 0)
        else:
            print "%s from %s IS NOT WELCOMEin " % (nick_seg, chan)

    def welcome(self, *args):
        print 'connected to irc as %s' % self.client.nick
        helpers.join(self.client, "#subliminalcollaborator")

    def partner_accept_session_dialog(self):
        sublime.active_window().show_quick_panel(['Collaborate with %s' % self.tgt_nick, 'No thanks!'], 
                                                 self.partner_accept_session_ondone)

    def partner_accept_session_ondone(self, response_idx):
        if response_idx == 0:
            self.session_role = Role.PARTNER
            self.am_recving_buffer = True
            helpers.msg(self.client, self.tgt_nick, CollabMessages.START_SHARE_ACK_FMT % self.max_buf_size)
            print 'IWANTBACON'
            self.session_view = sublime.active_window().new_file()
            self.session_view.set_scratch(True)
            # self.session_view.set_read_only(True) <-- may need a cleanup function if we do this
        else:
            self.session_role = None
            self.tgt_nick = None

    def share_next_chunk(self):
        self.chunk_lock.acquire()
        self.session_view.erase_regions('share_all_bacon')
        self.session_view.show_at_center(self.chunk)
        self.session_view.add_regions('share_all_bacon', [self.chunk], 'comment', '', sublime.DRAW_OUTLINED)
        chunk_str = self.session_view.substr(self.chunk)
        self.chunk_lock.release()
        # print chunk_str
        if len(chunk_str) > 0:
            self.client.send("PRIVMSG", self.tgt_nick, ":%s" % chunk_str)
            # helpers.msg(self.client, self.tgt_nick, bytes(chunk_str, 'ascii'))

    def post_share_cleanup(self):
        # self.session_view.set_read_only(False)
        self.session_view.erase_regions('share_all_bacon')
        helpers.msg(self.client, self.tgt_nick, CollabMessages.END_SHARE_PUBLISH)

    def share_entire_view(self):
        chunk_min_pt = 0
        chunk_max_pt = self.max_buf_size
        self.chunk_lock.acquire()
        self.chunk = sublime.Region(chunk_min_pt, self.max_buf_size)
        if self.max_buf_size > chunk_max_pt:
            self.chunk = sublime.Region(self.chunk.begin(), chunk_max_pt)
        self.chunk_lock.release()
        while self.chunk.end() <= self.view_size:
            print 'region: %d -> %d of buf size %d' % (self.chunk.begin(), self.chunk.end(), self.view_size)
            sublime.set_timeout(lambda: self.share_next_chunk(), 150)
            time.sleep(.2)
            self.chunk_lock.acquire()
            self.chunk = sublime.Region(self.chunk.end(), self.chunk.end() + self.max_buf_size)
            self.chunk_lock.release()
        # one more chunk to send?
        self.chunk_lock.acquire()
        if self.chunk.end() > self.view_size and self.chunk.begin() < self.view_size:
            self.chunk = sublime.Region(self.chunk.begin(), self.view_size)
            sublime.set_timeout(lambda: self.share_next_chunk(), 150)
        self.chunk_lock.release()
        print 'done sharing, cleaning up'
        sublime.set_timeout(lambda: self.post_share_cleanup(), 200)

    def publish_partner_chunk(self):
        self.in_queue_lock.acquire()
        chunk_str = self.in_queue.pop(-1)
        self.in_queue_lock.release()
        share_edit = self.session_view.begin_edit()
        self.session_view.insert(share_edit, self.session_view.size(), chunk_str)
        self.session_view.end_edit(share_edit)


class IRCClientThread(threading.Thread): 
    def __init__(self, irc_client):
        self.client = irc_client
        self.live = True
        threading.Thread.__init__(self)

    def run(self):
        conn = self.client.connect()
        while self.live:
            conn.next()
        print 'disconnected from irc'

# {
#     "subliminal_collaborator_config": {
#         "irc": {
#             "host": "irc.pearsoncmg.com",
#             "port": 6667,
#             "pwd": "my9pv",
#             "nick": "subliminal_nick"
#         }
#     }
# }

class CollabSessionCommand(sublime_plugin.WindowCommand):
    irc_client = None
    irc_thread = None
    session_view = None
    co_collab_nick = None

    def init(self):
        if self.irc_client and self.irc_thread:
            print 'disconnecting'
            self.irc_thread.live = False
            helpers.quit(self.irc_client)
            self.irc_thread.join(10)
            self.irc_client = None
            self.irc_thread = None

        collab_config = self.window.active_view().settings().get("subliminal_collaborator_config", {
                "irc": {
                    "host": "irc.pearsoncmg.com",
                    "port": 6667,
                    "pwd": "my9pv",
                    "nick": "sub_nick"
                }
            })
        irc_host = collab_config['irc']['host']
        irc_port = collab_config['irc']['port']
        irc_pwd = collab_config['irc']['pwd']
        irc_nick = collab_config['irc']['nick']
        self.irc_client = IRCClient(CollabMsgHandler, host=irc_host, port=irc_port, nick=irc_nick,
                                passwd=irc_pwd, blocking=True)
        self.irc_thread = IRCClientThread(self.irc_client)
        self.irc_thread.start()

    def run(self, init_irc):
        if init_irc:
            self.init()
        else:
            if not self.irc_client and not self.irc_thread:
                print 'oh nos! initing irc session'
                self.init()
            self.window.show_quick_panel(['Share active view (default)', 'Share other view...'], self.view_to_share)

    def view_to_share(self, choice_idx):
        if choice_idx < 1:
            self.session_view = self.window.active_view()
            self.window.show_input_panel('Share with (IRC nick):', 'sub_frank', self.with_whom, None, None)
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
            self.window.show_input_panel('Share with (IRC nick):', '', self.with_whom, None, None)

    def with_whom(self, irc_nick):
        self.co_collab_nick = irc_nick
        self.irc_client.command_handler.tgt_nick = irc_nick
        self.start_session()

    def start_session(self):
        print 'you chose to share %s, with %s' % (self.session_view.file_name(), self.irc_client.command_handler.tgt_nick)
        self.irc_client.command_handler.session_view = self.session_view
        self.irc_client.command_handler.view_size = self.session_view.size()
        self.irc_client.command_handler.session_role = Role.HOST
        helpers.msg(self.irc_client, self.co_collab_nick, CollabMessages.START_SHARE)


class TestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print self.view.size()

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
