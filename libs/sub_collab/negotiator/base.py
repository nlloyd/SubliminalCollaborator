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
from zope.interface import Interface, implements

SESSION_RETRY       = 'TRY-NEXT-HOST-IP'
SESSION_REJECTED    = 'REJECTED'
SESSION_FAILED      = 'NO-GOOD-HOST-IP'

DCC_PROTOCOL_COLLABORATE    = 'collaborate'
DCC_PROTOCOL_RETRY          = 'retry-collaborate'


class INegotiator(Interface):
    """
    Representation of a peer-to-peer session negotiator.
    Provides methods to communicate through an instant messaging layer
    in order to establish a direct peer-to-peer session with another user.
    """

    def connect():
        """
        Initiate the connection process to an instant messaging server,
        if not already connected.

        The constructor is expected to recieve configuration data in the
        form of a dict.
        """

    def isConnected():
        """
        Check if the connection is established and ready.

        @return: True on success, None if in-process, False on failure
        """

    def disconnect():
        """
        Disconnect from the instant messaging server.
        """

    def listUsers():
        """
        List the users available for establishing a peer-to-peer session.
        Depending on the implementing class this could either be a "friends list",
        the users within a certain chat room or channel, or
        a previously stored local list of known users.

        @return: C{Array} of usernames
        """

    def getUserName():
        """
        Return your username on the IM server.
        Could be different from what you initially set on connection, depending
        on implementation.

        @return: C{str} actual username
        """

    def negotiateSession(username, view):
        """
        *Requester calling reciever*

        Negotiate through the instant messaging layer a direct peer-to-peer connection
        with the user that has the given username.  Note the username in question must
        represent another SubliminalCollaborator Negotiator instance used by another
        user.

        If the user identified by the given username is not in the C{Array} returned
        by listUsers(), the expectation is that successful execution of this function
        will result in the given username being added to the list of known users.

        @return: C{peer.Peer} with or without a connection to another C{peer.Peer}
        """

    def acceptSessionRequest(username, host, port):
        """
        *Reciever responding to requester*

        Accept a session request made by the given peer on the given host and port.
        """

    def rejectSessionRequest(username):
        """
        *Reciever responding to requester*

        Reject a session request made by the given peer.
        """

    def retrySessionRequest(username):
        """
        *Reciever responding to requester*

        A session failed to be established, inform the initial requester to try again.
        """


class BaseNegotiator(object):
    """
    Base implementation of the Negotiator interface.

    Negotiators are both protocols and factories for themselves.
    Not sure if this is the best way to do things but for now it
    will do.

    This only provides a constructor to recieve an arbitrary id and a config C{dict}.
    """
    implements(INegotiator)


    def __init__(self, id, config):
        self.id = id
        self.config = config


    def getId(self):
        return self.id


    def str(self):
        return self.id


    def getConfig(self):
        return self.config


# ******* patch twisted.words.protocols.irc.IRCClient adding names support until ticket 3275 is addressed ******* #

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, error, defer
from twisted.python import text

class PatchedServerSupportedFeatures(irc.ServerSupportedFeatures):

    def __init__(self):
        irc.ServerSupportedFeatures.__init__(self)
        self._features['PREFIX'] = self._parsePrefixParam('(qaovh)~&@+%')


class PatchedIRCClient(irc.IRCClient):

    # cache of nickname prefixes from ServerSupportedFeatures,
    # extracted by irc_RPL_NAMREPLY
    _nickprefixes = None

    def __init__(self):
        # container for NAMES replies
        self._namreply = {}
        

    def names(self, *channels):
        """
        Tells the server to give a list of users in the specified channels.

        Multiple channels can be specified at one time, `channelNames` will be
        called multiple times, once for each channel.

        @type channels: C{str}
        @param channels: The name of the channel or or channels to request
            the username lists for from the server.
        """
        # dump all names of all visible channels
        if not channels:
            self.sendLine("NAMES")
        else:
            # some servers do not support multiple channel names at once
            for channel in channels:
                self.sendLine("NAMES %s" % (channel,))


    def irc_RPL_NAMREPLY(self, prefix, params):
        """
        Handles the raw NAMREPLY that is returned as answer to
        the NAMES command. Accumulates users until ENDOFNAMES.

        @type prefix: C{str}
        @param prefix: irc command prefix, irrelevant to this method
        @type params: C{Array}
        @param params: parameters for the RPL_NAMREPLY message
            the third entry is the channel name and the fourth
            is a space-delimited list of member usernames.
        """
        # cache nickname prefixes if not already parsed from ServerSupportedFeatures instance
        if not self._nickprefixes:
            self._nickprefixes = ''
            prefixes = self.supported.getFeature('PREFIX', {})
            for prefixTuple in prefixes.itervalues():
                self._nickprefixes = self._nickprefixes + prefixTuple[0]
        channel = params[2]
        prefixedUsers = params[3].split()
        users = []
        for prefixedUser in prefixedUsers:
            users.append(prefixedUser.lstrip(self._nickprefixes))
        self._namreply.setdefault(channel, []).extend(users)


    def irc_RPL_ENDOFNAMES(self, prefix, params):
        """
        Handles the end of the NAMREPLY. This is called when all
        NAMREPLYs have finished. It gathers one, or all depending
        on the NAMES request, channel names lists gathered from
        RPL_NAMREPLY responses.

        @type prefix: C{str}
        @param prefix: irc command prefix, irrelevant to this method
        @type params: C{Array}
        @param params: parameters for the RPL_ENDOFNAMES message
            the second entry will be the channel for which all
            member usernames have already been sent to the client.
        """
        channel = params[1]
        if channel not in self._namreply:
            for channel, users in self._namreply.iteritems():
                self.channelNames(channel, users)
            self._namreply = {}
        else:
            users = self._namreply.pop(channel, [])
            self.channelNames(channel, users)


    def dcc_CHAT(self, user, channel, data):
        data = text.splitQuoted(data)
        if len(data) < 3:
            raise IRCBadMessage("malformed DCC CHAT request: %r" % (data,))

        (protocol, address, port) = data[:3]

        address = irc.dccParseAddress(address)
        try:
            port = int(port)
        except ValueError:
            raise irc.IRCBadMessage("Indecipherable port %r" % (port,))

        self.dccDoChat(user, channel, protocol, address, port, data)


    def dccDoChat(self, user, channel, protocol, address, port, data):
        pass

    ### Protocol methods

    def connectionMade(self):
        self.supported = PatchedServerSupportedFeatures()
        self._queue = []
        if self.performLogin:
            self.register(self.nickname)
