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
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
import sublime, sublime_plugin
import threading
import logging
# from oyoyo.client import IRCClient
# from oyoyo.cmdhandler import DefaultCommandHandler
# from oyoyo import helpers

# # def connect_callback(cli):
# #     # Identify to nickserv
# #     helpers.identify(cli, "my9pv")

# #     # Join the channel '#test'
# #     helpers.join(cli, "#subliminalcollaborator")

# class MyHandler(DefaultCommandHandler):
#     # Handle messages (the PRIVMSG command, note lower case)
#     def privmsg(self, nick, chan, msg):
#         print "%s in %s said: %s" % (nick, chan, msg)

# cli = IRCClient(MyHandler, host="irc.pearsoncmg.com", port=6667, nick="subliminal_nick",
#                 connect_cb=None)

# class IRCClientThread(threading.Thread):
#     def __init__(self, irc_client):
#         self.client = irc_client
#         threading.Thread.__init__(self)

#     def run(self):
#         logging.basicConfig(level=logging.DEBUG)
#         conn = self.client.connect()
#         while True:
#             conn.next()

# irc_thread = IRCClientThread(cli)
# irc_thread.start()

class CollabSessionCommand(sublime_plugin.WindowCommand):
    def run(self):
        print 'blah blah blah'
        # helpers.msg(cli, 'nick_hackathon', "ohai!")

