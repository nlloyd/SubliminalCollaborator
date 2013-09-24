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


class NegotiatorListener(Interface):
    """
    Interface for a listener to C{Negotiator} events.

    Meant to be implemented by UI handler in order to display to the user alerts or
    requests for input triggered by incoming or outgoing peer-to-peer session
    negotiations.
    """

    def acceptedSession(session):
        """
        """

    def retrySession():
        """
        """

    def rejectedSession(session):
        """
        """


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


    def getConfig(self):
        return self.config


    # def connect(self):
    #     pass


    # def isConnected(self):
    #     pass
