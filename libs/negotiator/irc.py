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
from negotiator import interface
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, threads


class IRCNegotiator(protocol.ClientFactory, irc.IRCClient):
    """
    IRC client implementation of the Negotiator interface.

    Negotiators are both protocols and factories for themselves.
    Not sure if this is the best way to do things but for now it
    will do.
    """
    implements(interface.Negotiator)

    #*** irc.IRCClient properties ***#
    versionName = 'SubliminalCollaborator'
    versionNum = 'pre-alpha'
    versionEnv = "Sublime Text 2"
    #******#

    clientConnection = None
    host = None
    port = None
    password = None

    peerUsers = None
    unverifiedUsers = None

    #*** Negotiator method implementations ***#

    def connect(self, host, port, username, password, **kwargs):
        """
        Connect to an instant messaging server.

        @param host: ip address or domain name of the host server
        @param port: C{int} port number of the host
        @param username: C{str} IM account username
        @param password: C{str} IM account password
        @param kwargs: {'channel': 'channelNameStringWoutPrefix'}

        @return: True on success
        """
        assert kwargs.has_key('channel')

        # start a fresh connection
        if self.clientConnection:
            self.clientConnection.disconnect()

        # irc.IRCClient member setting
        self.nickname = username

        self.host = host
        self.port = port
        self.password = password
        self.channel = kwargs['channel']

        self.clientConnection = threads.blockingCallFromThread(reactor, reactor.connectTCP,
            self.host, self.port, self)


    def isConnected(self):
        """
        Check if the connection is established and ready.

        @return: True on success, None if in-process, False on failure
        """
        # fully connected for us means we have registered and joined a channel
        # also that means we have a list of peer users (even if it is an empty list)
        if self.clientConnection and self._registered and self.peerUsers:
            return True
        elif self.clientConnection and (not self._registered or not self.peerUsers):
            return None
        else:
            return False
            

    def disconnect(self):
        """
        Disconnect from the instant messaging server.
        """
        if self.clientConnection:
            reactor.callFromThread(self.clientConnection.disconnect)
            print '[IRCNegotiator: disconnected from server %s]' % self.host
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
        for peer in self.peerUsers:
            fullList.append(peer)
        for unverified in self.unverifiedUsers:
            fullList.append('*' + unverified)
        return self.peerUsers


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
        pass


    def onNegotiateSession(self, username, host, port):
        """
        Callback method for incoming requests to start a peer-to-peer session.
        The username, host, and port of the requesting peer is provided as input.
        """
        pass

    #*** protocol.ClientFactory method implementations ***#

    def buildProtocol(self, addr):
        return self

    def clientConnectionLost(self, connector, reason):
        # may want to reconnect, but for now lets print why
        print '[IRCNegotiator: connection lost: %s]' % reason
        print type(reason)
        self.disconnect()

    def clientConnectionFailed(self, connector, reason):
        print '[IRCNegotiator: connection failed: %s]' % reason
        self.disconnect()

    #*** irc.IRCClient method implementations ***#

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        print '[IRCNegotiator: connected to server %s]' % self.host

    def signedOn(self):
        # join the channel after we have connected
        # part of the Negotiator connection process
        self.join(self.channel)

    def channelNames(self, channel, names):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        self.unverifiedUsers = []
        self.peerUsers = []
        for name in names:
            addUserToLists(name)

    def userJoined(self, user, channel):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        addUserToLists(user)

    def userLeft(self, user, channel):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        dropUserFromLists(user)

    def userQuit(self, user, quitMessage):
        dropUserFromLists(user)

    def userKicked(self, kickee, channel, kicker, message):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        dropUserFromLists(user)

    def userRenamed(self, oldname, newname):
        assert self.channel == channel.lstrip(irc.CHANNEL_PREFIXES)
        dropUserFromLists(oldname)
        addUserToLists(newname)

    def ctcpReply_VERSION(self, user, channel, data):
        print 'reply from user: %s' % user
        print data
        username = user.lstrip(irc.NICK_PREFIXES)
        if data == ('%s:%s:%s' % (self.versionName, self.versionNum, self.versionEnv)):
            self.peerUsers.append(username)
            self.unverifiedUsers.remove(username)
        elif (self.versionName in data) and (self.versionNum in data) and (self.versionEnv in data):
            self.peerUsers.append(username)
            self.unverifiedUsers.remove(username)
        else:
            # other client type, forget this user entirely
            self.unverifiedUsers.remove(username)

    #*** helper functions ***#

    def dropUserFromLists(self, user):
        username = user.lstrip(irc.NICK_PREFIXES)
        if username in self.peerUsers:
            self.peerUsers.remove(username)
        if username in self.unverifiedUsers:
            self.unverifiedUsers.remove(username)

    def addUserToLists(self, user):
        username = user.lstrip(irc.NICK_PREFIXES)
        self.unverifiedUsers.append(username)
        reactor.callFromThread(self.ctcpMakeQuery, user, [('VERSION', None)])
