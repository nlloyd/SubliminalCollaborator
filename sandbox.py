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

# twisted imports
from twisted.python import threadpool
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, threads
from twisted.python import log

# system imports
import time, threading

class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        # self.file.write('%s %s\n' % (timestamp, message))
        # self.file.flush()
        print '%s %s\n' % (timestamp, message)

    def close(self):
        pass
        # self.file.close()


class LogBot(irc.IRCClient):
    """A logging IRC bot."""
    
    nickname = "twistedbot"
    versionName = "subliminal_sandbox"
    versionEnv = "sublime text 2"
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        # self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger = MessageLogger(None)
        self.logger.log("[connected at %s]" % 
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.logger.close()


    # callbacks for events
    def created(self, when):
        """
        Called with creation date information about the server, usually at logon.

        @type when: C{str}
        @param when: A string describing when the server was created, probably.
        """
        print '[created]: %s' % when

    def yourHost(self, info):
        """
        Called with daemon information about the server, usually at logon.

        @type info: C{str}
        @param when: A string describing what software the server is running, probably.
        """
        print '[info]: %s' % info

    def myInfo(self, servername, version, umodes, cmodes):
        """
        Called with information about the server, usually at logon.

        @type servername: C{str}
        @param servername: The hostname of this server.

        @type version: C{str}
        @param version: A description of what software this server runs.

        @type umodes: C{str}
        @param umodes: All the available user modes.

        @type cmodes: C{str}
        @param cmodes: All the available channel modes.
        """
        print '[myInfo]: %s %s %s %s' % (servername, version, umodes, cmodes)

    def luserClient(self, info):
        """
        Called with information about the number of connections, usually at logon.

        @type info: C{str}
        @param info: A description of the number of clients and servers
        connected to the network, probably.
        """
        print '[luserClient]: %s' % info

    def bounce(self, info):
        """
        Called with information about where the client should reconnect.

        @type info: C{str}
        @param info: A plaintext description of the address that should be
        connected to.
        """
        print '[bounce]: %s' % info

    def isupport(self, options):
        """
        Called with various information about what the server supports.

        @type options: C{list} of C{str}
        @param options: Descriptions of features or limits of the server, possibly
        in the form "NAME=VALUE".
        """
        print '[isupport]:'
        print options  

    def luserChannels(self, channels):
        """
        Called with the number of channels existant on the server.

        @type channels: C{int}
        """
        print '[luserChannels]: %d' % channels

    def luserOp(self, ops):
        """
        Called with the number of ops logged on to the server.

        @type ops: C{int}
        """
        print '[luserOp]: %d' % ops

    def luserMe(self, info):
        """
        Called with information about the server connected to.

        @type info: C{str}
        @param info: A plaintext string describing the number of users and servers
        connected to this server.
        """
        print '[luserMe]: %s' % info

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        
        # Check to see if they're sending me a private message
        if channel == self.nickname:
            if msg == 'DIE':
                reactor.stop()
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a log bot" % user
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (self.nickname, msg))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'

    def dccDoSend(self, user, address, port, fileName, size, data):
        """Called when I receive a DCC SEND offer from a client.

        By default, I do nothing here."""
        ## filename = path.basename(arg)
        ## protocol = DccFileReceive(filename, size,
        ##                           (user,channel,data),self.dcc_destdir)
        ## reactor.clientTCP(address, port, protocol)
        ## self.dcc_sessions.append(protocol)
        print 'user: %s, addres: %s:%d, fileName: %s, data: %s' % (user, address, port, fileName, data)
        # print 'hostname: %s' % self.hostname



class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, password):
        self.channel = channel
        self.password = password

    def buildProtocol(self, addr):
        p = LogBot()
        p.factory = self
        p.password = self.password
        return p

    def clientConnectionLost(self, connector, reason):
        # """If we get disconnected, reconnect to server."""
        # connector.connect()
        print 'disconnecting'

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason

class ReactorThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        if not reactor.running:
            print "starting the reactor on a thread!"
            reactor.run(installSignalHandlers=False)

f = LogBotFactory("subliminalcollaboration", 'passwd')
reactor_thread = ReactorThread()
# reactor_thread.start()

# view.run_command('collab_test')
class CollabTestCommand(sublime_plugin.TextCommand):
    irc_con = None

    def run(self, edit):
        print 'running collab_test'
        print self.irc_con
        if not self.irc_con:
            print 'starting irc client'
            self.irc_con = reactor.connectTCP("localhost", 6667, f, 5)
            if not reactor_thread.is_alive():
                reactor_thread.start()
        else:
            'stopping irc client'
            self.irc_con.disconnect()
            self.irc_con = None
        # for region in self.view.sel():
        #     print '%d - %d' % (region.begin(), region.end())



#reactor.listenTCP(1234, EchoFactory())
#reactor.run()
# share_view_reply_pattern = re.compile('^!!OMGYES!!([0-9]+)!!$')
# view_sel_cmd_pattern = re.compile('^SELECTION\[([0-9]+),([0-9]+)\]$')
# view_set_syntax_pattern = re.compile('^SYNTAX (.*)$')

# class Role:
#     HOST = 1
#     PARTNER = 2

# class CollabMessages:
#     START_SHARE = '!want.bacon?'
#     START_SHARE_ACK_FMT = '!!OMGYES!!%d!!'
#     END_SHARE_PUBLISH = '!you.haz.teh.bacons!'

# class CollabMsgHandler(DefaultCommandHandler):
#     tgt_nick = None
#     session_view = None
#     session_role = None
#     session_selection = None
#     max_buf_size = 0
#     am_recving_buffer = False
#     in_queue = []
#     in_queue_lock = threading.Lock()
#     out_queue = []
#     out_queue_lock = threading.Lock()
#     chunk_lock = threading.Lock()

#     def privmsg(self, nick, chan, msg):
#         print 'msg from: %s' % nick
#         # print msg
#         # print len(nick)
#         # print len(chan)
#         # print len(msg)
#         # print 'only listening to: %s' % tgt_nick
        
#         nick_seg = None

#         if nick:
#             nick_segs = parse_nick(nick)
#             nick_seg = nick_segs[0]

#         if self.tgt_nick and nick_seg == self.tgt_nick:
#             if self.session_role == Role.HOST:
#                 ## HOST behavior
#                 # print 'imahost'
#                 buffer_match = share_view_reply_pattern.match(msg)
#                 cmd_match = view_sel_cmd_pattern.match(msg)
#                 if buffer_match:
#                     print 'sharing buffer'
#                     # bad hack for base64 encoding/decoding support
#                     self.max_buf_size = int(float(buffer_match.group(1))/2)
#                     self.share_entire_view()
#                 elif cmd_match:
#                     self.session_selection = None
#                     self.session_selection = sublime.Region(int(cmd_match.group(1)), int(cmd_match.group(2)))
#                     sublime.set_timeout(lambda: self.show_shared_selection(), 100)
#                 ## more msg handling here ##
#             else:
#                 cmd_match = view_sel_cmd_pattern.match(msg)
#                 syntax_match = view_set_syntax_pattern.match(msg)
#                 if msg == CollabMessages.END_SHARE_PUBLISH:
#                     self.am_recving_buffer = False
#                 elif cmd_match:
#                     self.session_selection = None
#                     self.session_selection = sublime.Region(int(cmd_match.group(1)), int(cmd_match.group(2)))
#                     sublime.set_timeout(lambda: self.show_shared_selection(), 100)
#                 elif syntax_match:
#                     self.session_syntax = syntax_match.group(1)
#                     sublime.set_timeout(lambda: self.set_syntax(), 100)
#                 elif self.am_recving_buffer:
#                     print 'recvd msg of len %d' % len(msg)
#                     self.in_queue_lock.acquire()
#                     self.in_queue.insert(0, msg)
#                     self.in_queue_lock.release()
#                     sublime.set_timeout(lambda: self.publish_partner_chunk(), 100)
#                 ## PARTNER behavior
#                 # print "%s said to %s: %s" % (nick_seg, chan, msg)
#         elif msg == CollabMessages.START_SHARE:
#             # request from a potential host to start a session
#             self.tgt_nick = nick_seg
#             print 'show start session dialog'
#             self.max_buf_size = 498 - (len(nick) + len(chan))
#             sublime.set_timeout(lambda: self.partner_accept_session_dialog(), 0)
#         else:
#             print "%s from %s IS NOT WELCOMEin " % (nick_seg, chan)

#     def welcome(self, *args):
#         print 'connected to irc as %s' % self.client.nick
#         helpers.join(self.client, "#subliminalcollaborator")

#     def set_syntax(self):
#         print self.session_syntax
#         self.session_view.settings().set('syntax', self.session_syntax)

#     def show_shared_selection(self):
#         print 'do i get here???'
#         # first clear previous shared selections
#         self.session_view.erase_regions('collab_shared_selection')
#         # now show the new one, scroll the view to it
#         self.session_view.add_regions('collab_shared_selection', [self.session_selection], 
#                                       'string', '')
#         self.session_view.show_at_center(self.session_selection)

#     def partner_accept_session_dialog(self):
#         sublime.active_window().show_quick_panel(['Collaborate with %s' % self.tgt_nick, 'No thanks!'], 
#                                                  self.partner_accept_session_ondone)

#     def partner_accept_session_ondone(self, response_idx):
#         if response_idx == 0:
#             self.session_role = Role.PARTNER
#             self.am_recving_buffer = True
#             helpers.msg(self.client, self.tgt_nick, CollabMessages.START_SHARE_ACK_FMT % self.max_buf_size)
#             print 'IWANTBACON'
#             self.session_view = sublime.active_window().new_file()
#             self.session_view.set_scratch(True)
#             # self.session_view.set_read_only(True) <-- may need a cleanup function if we do this
#         else:
#             self.session_role = None
#             self.tgt_nick = None

#     def share_next_chunk(self):
#         self.chunk_lock.acquire()
#         self.session_view.erase_regions('share_all_bacon')
#         self.session_view.show_at_center(self.chunk)
#         self.session_view.add_regions('share_all_bacon', [self.chunk], 'comment', '', sublime.DRAW_OUTLINED)
#         # self.session_view.add_regions('share_all_bacon', [self.chunk], 'string', '')
#         chunk_str = self.session_view.substr(self.chunk)
#         self.chunk_lock.release()
#         # print chunk_str
#         if len(chunk_str) > 0:
#             self.client.send("PRIVMSG", self.tgt_nick, ":%s" % b64encode(chunk_str))
#             # helpers.msg(self.client, self.tgt_nick, bytes(chunk_str, 'ascii'))

#     def post_share_cleanup(self):
#         # self.session_view.set_read_only(False)
#         self.session_view.erase_regions('share_all_bacon')
#         helpers.msg(self.client, self.tgt_nick, CollabMessages.END_SHARE_PUBLISH)
#         syntax = self.session_view.settings().get('syntax')
#         helpers.msg(self.client, self.tgt_nick, 'SYNTAX %s' % syntax)

#     def share_entire_view(self):
#         chunk_min_pt = 0
#         chunk_max_pt = self.max_buf_size
#         self.chunk_lock.acquire()
#         self.chunk = sublime.Region(chunk_min_pt, self.max_buf_size)
#         if self.max_buf_size > chunk_max_pt:
#             self.chunk = sublime.Region(self.chunk.begin(), chunk_max_pt)
#         self.chunk_lock.release()
#         while self.chunk.end() <= self.view_size:
#             print 'region: %d -> %d of buf size %d' % (self.chunk.begin(), self.chunk.end(), self.view_size)
#             sublime.set_timeout(lambda: self.share_next_chunk(), 200)
#             time.sleep(1)
#             self.chunk_lock.acquire()
#             self.chunk = sublime.Region(self.chunk.end(), self.chunk.end() + self.max_buf_size)
#             self.chunk_lock.release()
#         # one more chunk to send?
#         self.chunk_lock.acquire()
#         if self.chunk.end() > self.view_size and self.chunk.begin() < self.view_size:
#             self.chunk = sublime.Region(self.chunk.begin(), self.view_size)
#             sublime.set_timeout(lambda: self.share_next_chunk(), 200)
#         self.chunk_lock.release()
#         print 'done sharing, cleaning up'
#         sublime.set_timeout(lambda: self.post_share_cleanup(), 200)

#     def publish_partner_chunk(self):
#         self.in_queue_lock.acquire()
#         print 'chunks to publish: %d' % len(self.in_queue)
#         while len(self.in_queue) > 0:
#             chunk_str = self.in_queue.pop(-1)
#         self.in_queue_lock.release()
#         share_edit = self.session_view.begin_edit()
#         self.session_view.insert(share_edit, self.session_view.size(), b64decode(chunk_str))
#         self.session_view.end_edit(share_edit)
#         helpers.msg(self.client, self.tgt_nick, '!!MOAR.BACON.PLZ!!')


# class IRCClientThread(threading.Thread): 
#     def __init__(self, irc_client):
#         self.client = irc_client
#         self.live = True
#         threading.Thread.__init__(self)

#     def run(self):
#         conn = self.client.connect()
#         while self.live:
#             conn.next()
#         print 'disconnected from irc'

# # {
# #     "subliminal_collaborator_config": {
# #         "irc": {
# #             "host": "irc.something.com",
# #             "port": 6667,
# #             "pwd": "somepwd",
# #             "nick": "subliminal_nick"
# #         }
# #     }
# # }

# class CollabSessionCommand(sublime_plugin.WindowCommand):
#     irc_client = None
#     irc_thread = None
#     session_view = None
#     co_collab_nick = None

#     def init(self):
#         if self.irc_client and self.irc_thread:
#             print 'disconnecting'
#             self.irc_thread.live = False
#             helpers.quit(self.irc_client)
#             self.irc_thread.join(10)
#             self.irc_client = None
#             self.irc_thread = None

#         collab_config = self.window.active_view().settings().get("subliminal_collaborator_config", None)
#         irc_host = collab_config['irc']['host']
#         irc_port = collab_config['irc']['port']
#         irc_pwd = collab_config['irc']['pwd']
#         irc_nick = collab_config['irc']['nick']
#         self.irc_client = IRCClient(CollabMsgHandler, host=irc_host, port=irc_port, nick=irc_nick,
#                                 passwd=irc_pwd, blocking=True)
#         self.irc_thread = IRCClientThread(self.irc_client)
#         self.irc_thread.start()

#     def run(self, init_irc, send_select=False):
#         # print self.irc_client
#         # print self.irc_client.command_handler.session_view
#         if send_select:
#             if self.irc_client and self.irc_client.command_handler.session_view:
#                 if not self.session_view:
#                     self.session_view = self.irc_client.command_handler.session_view
#                 print 'session view'
#                 print self.session_view
#                 # print 'active view'
#                 # print self.window.active_view()
#                 if self.session_view:
#                     for region in self.session_view.sel():
#                         print '%d - %d' % (region.begin(), region.end())
#                         if self.irc_client.command_handler.tgt_nick:
#                             print "got to here"
#                             helpers.msg(self.irc_client, self.irc_client.command_handler.tgt_nick, 'SELECTION[%d,%d]' % (region.begin(), region.end()))
#                 # else:
#                 #     print 'not in active view!'
#         else:
#             if init_irc:
#                 self.init()
#             else:
#                 # if not self.irc_client and not self.irc_thread:
#                 #     print 'oh nos! initing irc session'
#                 #     self.init()
#                 self.window.show_quick_panel(['Share active view (default)', 'Share other view...'], self.view_to_share)

#     def view_to_share(self, choice_idx):
#         if choice_idx < 1:
#             self.session_view = self.window.active_view()
#             self.window.show_input_panel('Share with (IRC nick):', 'sub_frank', self.with_whom, None, None)
#         else:
#             self.current_views = []
#             self.current_view_names = []
#             for view in self.window.views():
#                 self.current_views.append(view)
#                 self.current_view_names.append(view.file_name())

#             self.window.show_quick_panel(self.current_view_names, self.choose_this_view)

#     def choose_this_view(self, view_idx):
#         if view_idx >= 0:
#             self.session_view = self.current_views[view_idx]
#             self.window.show_input_panel('Share with (IRC nick):', '', self.with_whom, None, None)

#     def with_whom(self, irc_nick):
#         self.co_collab_nick = irc_nick
#         self.irc_client.command_handler.tgt_nick = irc_nick
#         self.start_session()

#     def start_session(self):
#         print 'you chose to share %s, with %s' % (self.session_view.file_name(), self.irc_client.command_handler.tgt_nick)
#         self.irc_client.command_handler.session_view = self.session_view
#         self.irc_client.command_handler.view_size = self.session_view.size()
#         self.irc_client.command_handler.session_role = Role.HOST
#         helpers.msg(self.irc_client, self.co_collab_nick, CollabMessages.START_SHARE)


# class TestCommand(sublime_plugin.TextCommand):
#     def run(self, edit):
#         print 'WOAH'
#         for region in self.view.sel():
#             print '%d - %d' % (region.begin(), region.end())

# class CollabSessionEventHandler(sublime_plugin.EventListener):
#     last_region = None

#     def on_modified(self, view):
#         # TODO: send change events to the partner
#         if view.file_name():
#             for region in view.sel():
#                 print region.begin()
#             print '!!! command %s modified: %s' % (view.command_history(0, True), view.file_name())

#     def on_selection_modified(self, view):
#         if view.file_name():
#             for region in view.sel():
#                 if self.last_region and self.last_region == region:
#                     print 'done selecting!'
#                 self.last_region = region
#                 print 'sel_mod: %d' % region.begin()
