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
    
    nickname = "twistdbot"
    versionName = "subliminal_sandbox"
    versionNum = ''
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


    def channelNames(self, channel, names):
        print 'channel %s has the the following users: %s' % (channel, names)

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        # self.names('#' + self.factory.channel, '!' + self.factory.channel)

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
            if msg == 'show-names':
                print 'showing names'
                self.names(['#subliminalcollaboration'])
                return
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
        print prefix
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

    def userJoined(self, user, channel):
        """
        Called when I see another user joining a channel.
        """
        print 'user %s joined %s' % (user, channel)

    def userLeft(self, user, channel):
        print 'user %s left %s' % (user, channel)

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
        print addr
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
if not reactor_thread.is_alive():
    reactor_thread.start()

# view.run_command('collab_test')
class CollabTestCommand(sublime_plugin.TextCommand):
    irc_con = None

    def run(self, edit):    
        # if not reactor_thread.is_alive():
        #     reactor_thread.start()
        #     time.sleep(5.0)
        print 'running collab_test'
        print self.irc_con
        if not self.irc_con:
            print 'starting irc client'
            self.irc_con = reactor.connectTCP("localhost", 6667, f, 5)
            # if not reactor_thread.is_alive():
            #     reactor_thread.start()
        else:
            'stopping irc client'
            self.irc_con.disconnect()
            self.irc_con = None
        # for region in self.view.sel():
        #     print '%d - %d' % (region.begin(), region.end())

