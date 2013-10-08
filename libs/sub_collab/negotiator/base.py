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

class Negotiator(Interface):
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
        Negotiate through the instant messaging layer a direct peer-to-peer connection
        with the user that has the given username.  Note the username in question must
        represent another SubliminalCollaborator Negotiator instance used by another
        user.

        If the user identified by the given username is not in the C{Array} returned
        by listUsers(), the expectation is that successful execution of this function
        will result in the given username being added to the list of known users.

        @return: C{peer.Peer} already connected to another C{peer.Peer}
        """

    def onNegotiateSession(username, host, port, accepted):
        """
        Callback method for incoming requests to start a peer-to-peer session.
        The username, host, and port of the requesting peer is provided as input.
        """


class Observer(Interface):
    """
    Basic listener interface.
    """

    def update(event, producer, data=None):
        """
        Single method stub to recieve named events from a producer with an 
        optional payload of data.
        """


class Observable(object):
    """
    Basic event producer sub-class.  Implementers publish events to registered C{Observer} instances.
    """

    def __init__(self):
        self.observers = set()


    def addObserver(self, observer):
        if Observer.providedBy(observer):
            self.observers.add(observer)

    def removeObserver(self, observer):
        self.observers.discard(observer)

    def notify(event, producer, data=None):
        for observer in self.observers:
            self.observer.update(event, producer, data)


INCOMING_REQUEST_EVENT      = 'incoming-request-event'
OUTGOING_REQUEST_EVENT      = 'outgoing-request-event'
SESSION_ACCEPTED_EVENT      = 'accept-session-event'
SESSION_REJECTED_EVENT      = 'reject-session-event'
SESSION_RETRY_EVENT         = 'retry-session-event'


class BaseNegotiator(object)
    """
    Base implementation of the Negotiator interface.

    Negotiators are both protocols and factories for themselves.
    Not sure if this is the best way to do things but for now it
    will do.

    This only provides a constructor to recieve an arbitrary id and a config C{dict}.
    """
    implements(Negotiator)


    def __ init__(self, id, config):
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

class PatchedServerSupportedFeatures(irc.ServerSupportedFeatures):

    def __init__(self):
        irc.ServerSupportedFeatures.__init__(self):
        self._features['PREFIX'] = self._parsePrefixParam('(qaovh)~&@+%')


class PatchedIRCClient(irc.IRCClient):

    # cache of nickname prefixes from ServerSupportedFeatures,
    # extracted by irc_RPL_NAMREPLY
    _nickprefixes = None

    def __init__(self):
        irc.IRCClient.__init__(self)

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

    ### Protocol methods

    def connectionMade(self):
        self.supported = PatchedServerSupportedFeatures()
        # container for NAMES replies
        self._namreply = {}
        self._queue = []
        if self.performLogin:
            self.register(self.nickname)
