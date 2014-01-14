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
from zope.interface import implements
from sub_collab.negotiator import base
from sub_collab.peer import basic
from sub_collab import common, event, registry, status_bar
from twisted.words.protocols import irc
from twisted.internet import reactor, ssl, protocol, error, defer
import logging, sys, socket, functools
import sublime


class IRCNegotiator(base.BaseNegotiator, common.Observable, protocol.ClientFactory, base.PatchedIRCClient):
    """
    IRC client implementation of the Negotiator interface.
    Extends C{sub_collab.base.BaseNegotiator}

    Negotiators are both protocols and factories for themselves.
    Not sure if this is the best way to do things but for now it
    will do.
    """

    logger = logging.getLogger('SubliminalCollaborator.irc')

    #*** irc.IRCClient properties ***#
    versionName = 'SubliminalCollaborator'
    versionNum = '0.2.0'
    versionEnv = "Sublime Text 2"
    #******#

    negotiateCallback = None
    onNegotiateCallback = None
    rejectedOrFailedCallback = None

    def __init__(self, id, config):
        common.Observable.__init__(self)
        base.BaseNegotiator.__init__(self, id, config)
        base.PatchedIRCClient.__init__(self)
        assert config.has_key('host'), 'IRCNegotiator missing host'
        assert config.has_key('port'), 'IRCNegotiator missing port'
        assert config.has_key('username'), 'IRCNegotiator missing username'
        assert config.has_key('channel'), 'IRCNegotiator missing channel to connect to'
        self.clientConnection = None
        self.host = self.config['host'].encode()
        self.port = int(self.config['port'])
        self.nickname = self.config['username'].encode()
        if self.config.has_key('password'):
            self.password = self.config['password'].encode()
        if self.config.has_key('useSSL'):
            self.useSSL = self.config['useSSL']
        else:
            # default to false
            self.useSSL = False
        self.channel = self.config['channel'].encode()
        self.peerUsers = []
        self.unverifiedUsers = None
        self.connectionFailed = False
        # holder for the session currently being negotiated
        # this limits session handling to one at a time, which makes sense right now
        self.pendingSession = None
        self.hostAddressToTryQueue = None

    #*** Negotiator method implementations ***#

    def connect(self):
        """
        Connect to an instant messaging server.

        @return: True on success
        """
        if self.isConnected():
            return

        # start a fresh connection
        if self.clientConnection:
            self.clientConnection.disconnect()

        status_bar.status_message('connecting to %s' % self.str())
        if self.useSSL:
            self.logger.info('connecting to %s with ssl' % self.str())
            self.clientConnection = reactor.connectSSL(self.host, self.port, self, ssl.ClientContextFactory())
        else:
            self.logger.info('connecting to %s' % self.str())
            self.clientConnection = reactor.connectTCP(self.host, self.port, self)


    def isConnected(self):
        """
        Check if the connection is established and ready.

        @return: True on success, None if in-process, False on failure
        """
        # fully connected for us means we have registered and joined a channel
        # also that means we have a list of peer users (even if it is an empty list)
        connected = None
        if self.clientConnection:
            if self._registered:
                connected = True
        else:
            connected = False
        return connected
            

    def disconnect(self):
        """
        Disconnect from the instant messaging server.
        """
        if self.clientConnection:
            if self.clientConnection.state == 'disconnected':
                self.clientConnection = None
                self._registered = False
                self.peerUsers = None
            else:
                self.clientConnection.disconnect()
                # reactor.callFromThread(self.clientConnection.disconnect)
                self.logger.info('Disconnected from %s' % self.host)
                status_bar.status_message('disconnected from %s' % self.str())
            self.clientConnection = None
        self._registered = False
        self.peerUsers = None
        self.unverifiedUsers = None


    def listUsers(self):
        """
        List the users available for establishing a peer-to-peer session.
        Depending on the implementing class this could either be a "friends list",
        the users within a certain chat room or channel, or
        a previously stored local list of known users.

        @return: C{list} of usernames, or None if we are not connected yet
        """
        fullList = []
        if self.peerUsers:
            for peer in self.peerUsers:
                fullList.append(peer)
        if self.unverifiedUsers:
            for unverified in self.unverifiedUsers:
                fullList.append('*' + unverified)
        return fullList


    def getUserName(self):
        """
        Return the final user nickname after connection to 
        the IRC server.

        @return: C{str} actual username
        """
        return self.nickname


    def negotiateSession(self, username):
        """
        Negotiate through the instant messaging layer a direct peer-to-peer connection
        with the user that has the given username.  Note the username in question must
        represent another SubliminalCollaborator Negotiator instance used by another
        user.

        If the user identified by the given username is not in the C{Array} returned
        by listUsers(), the expectation is that successful execution of this function
        will result in the given username being added to the list of known users.
        """
        if (not username in self.peerUsers) and (not username in self.unverifiedUsers):
            self.addUserToLists(username)
        if self.hostAddressToTryQueue == None or len(self.hostAddressToTryQueue) == 0:
            self.hostAddressToTryQueue = socket.gethostbyname_ex(socket.gethostname())[2]
        ipaddress = self.hostAddressToTryQueue.pop()
        session = basic.BasicPeer(username, self)
        port = session.hostConnect()
        self.logger.debug('attempting to start session with %s at %s:%d' % (username, ipaddress, port))
        status_bar.status_message('trying to share with %s@%s' % (username, ipaddress))
        self.pendingSession = session
        registry.registerSession(session)
        self.ctcpMakeQuery(username, [('DCC CHAT', '%s %s %d' % (base.DCC_PROTOCOL_COLLABORATE, ipaddress, port))])


    def acceptSessionRequest(self, username, host, port):
        self.logger.debug('accepted session request from %s at %s:%d)' % (username, host, port))
        status_bar.status_message('accepted session request from %s, trying to connect to %s:%d' % (username, host, port))
        self.logger.info('Establishing session with %s at %s:%d' % (username, host, port))
        session = basic.BasicPeer(username, self)
        session.clientConnect(host, port)
        registry.registerSession(session)


    def rejectSessionRequest(self, username):
        self.logger.debug('rejected session request from %s' % username)
        self.msg(username, base.SESSION_REJECTED)


    def retrySessionRequest(self, username):
        self.logger.debug('request to retry from %s' % username)
        self.msg(username, base.SESSION_RETRY)


    #*** protocol.ClientFactory method implementations ***#

    def buildProtocol(self, addr):
        return self


    def clientConnectionLost(self, connector, reason):
        if error.ConnectionDone == reason.type:
            self.disconnect()
        else:
            # may want to reconnect, but for now lets print why
            self.logger.error('Connection lost: %s - %s' % (reason.type, reason.value))
            status_bar.status_message('connection lost to %s' % self.str())


    def clientConnectionFailed(self, connector, reason):
        self.logger.error('Connection failed: %s - %s' % (reason.type, reason.value))
        status_bar.status_message('connection failed to %s' % self.str())
        self.connectionFailed = True
        self.disconnect()


    #*** irc.IRCClient method implementations ***#

    def connectionMade(self):
        self.logger.debug('Connection made')
        base.PatchedIRCClient.connectionMade(self)
        # reactor.callFromThread(base.PatchedIRCClient.connectionMade, self)
        self.logger.info('Connected to ' + self.host)


    def signedOn(self):
        # join the channel after we have connected
        # part of the Negotiator connection process
        status_bar.status_message('connected to ' + self.str())
        self.logger.info('Joining channel ' + self.channel)
        self.join(self.channel)


    def joined(self, channel):
        self.logger.info('Joined channel ' + self.channel)
        self.names(self.channel)


    def channelNames(self, channel, names):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        names.remove(self.nickname)
        self.logger.debug('Received initial user list %s' % names)
        self.unverifiedUsers = []
        self.peerUsers = []
        for name in names:
            self.addUserToLists(name)


    def userJoined(self, user, channel):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        self.addUserToLists(user)


    def userLeft(self, user, channel):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        self.dropUserFromLists(user)


    def userQuit(self, user, quitMessage):
        self.dropUserFromLists(user)


    def userKicked(self, kickee, channel, kicker, message):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        self.dropUserFromLists(user)


    def userRenamed(self, oldname, newname):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        self.dropUserFromLists(oldname)
        self.addUserToLists(newname)


    def privmsg(self, user, channel, message):
        """
        Handles incoming private messages from a given user on a given channel.
        This is used by the peer attempting to establish a session to recieve
        information from the peer recieving the session request.
        """
        username = user.lstrip(self.getNickPrefixes())
        if '!' in username:
            username = username.split('!', 1)[0]
        self.logger.debug('Received %s from %s' % (message, username))
        if message == base.SESSION_RETRY:
            registry.removeSession(self.pendingSession)
            self.pendingSession.disconnect();
            self.pendingSession = None
            self.negotiateSession(username)
        elif message == base.SESSION_FAILED:
            # client recvd from server... report error and cleanup any half-made sessions
            self.logger.warn('All connections to all possible host ip addresses failed.')
            registry.removeSession(self.pendingSession)
            self.pendingSession.disconnect();
            self.pendingSession = None
        elif message == base.SESSION_REJECTED:
            # server recvd from client... report rejected and cleanup any half-made sessions
            self.logger.info('Request to share with user %s was rejected.' % username)
            registry.removeSession(self.pendingSession)
            self.pendingSession.disconnect();
            self.pendingSession = None


    def ctcpReply_VERSION(self, user, channel, data):
        username = user.lstrip(self.getNickPrefixes())
        if '!' in username:
            username = username.split('!', 1)[0]
        if (data == ('%s:%s:%s' % (self.versionName, self.versionNum, self.versionEnv))) or ((self.versionName in data) and (self.versionNum in data) and (self.versionEnv in data)):
            self.logger.debug('Verified peer %s' % username)
            self.peerUsers.append(username)
            self.unverifiedUsers.remove(username)
        else:
            # other client type, forget this user entirely
            self.unverifiedUsers.remove(username)


    def dccDoChat(self, user, channel, protocol, address, port, data):
        """
        Handler method for incoming DCC CHAT requests.
        If the specified protocol is 'collaborate' then the sending user
        is a peer wanting to establish a collaboration session at the given
        address and port.  This triggers a notification event to all observers, 
        basically requesting user input before proceeding to establish a session.
        """
        username = user.lstrip(self.getNickPrefixes())
        if '!' in username:
            username = username.split('!', 1)[0]
        self.logger.debug('Received dcc chat from %s, protocol %s, address %s, port %d' % (username, protocol, address, port))
        if protocol == base.DCC_PROTOCOL_COLLABORATE or protocol == base.DCC_PROTOCOL_RETRY:
            self.notify(event.INCOMING_SESSION_REQUEST, self, (username, address, port))

    #*** helper functions ***#

    def dropUserFromLists(self, user):
        username = user.lstrip(self.getNickPrefixes())
        if username in self.peerUsers:
            self.peerUsers.remove(username)
        if username in self.unverifiedUsers:
            self.unverifiedUsers.remove(username)


    def addUserToLists(self, user):
        username = user.lstrip(self.getNickPrefixes())
        self.unverifiedUsers.append(username)
        self.ctcpMakeQuery(user, [('VERSION', None)])
        # reactor.callFromThread(self.ctcpMakeQuery, user, [('VERSION', None)])


    def getNickPrefixes(self):
        if not self._nickprefixes:
            self._nickprefixes = ''
            prefixes = self.supported.getFeature('PREFIX', {})
            for prefixTuple in prefixes.itervalues():
                self._nickprefixes = self._nickprefixes + prefixTuple[0]
        return self._nickprefixes


    def str(self):
        return 'irc|%s@%s:%d' % (self.nickname, self.host, self.port)
