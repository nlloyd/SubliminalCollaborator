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
from peer import interface
from twisted.internet import reactor, protocol, error, interfaces
from twisted.protocols import basic
import logging, sys, socket, struct

logger = logging.getLogger(__name__)
logger.propagate = False
# purge previous handlers set... for plugin reloading
del logger.handlers[:]
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(logging.Formatter(fmt='[SubliminalCollaborator|Peer(%(levelname)s): %(message)s]'))
logger.addHandler(stdoutHandler)
logger.setLevel(logging.DEBUG)


# build off of the Int32StringReceiver to leverage its unprocessed buffer handling
class BasePeer(basic.Int32StringReceiver, protocol.ClientFactory, protocol.ServerFactory):
    """
    One side of a peer-to-peer collaboration connection.
    This is a direct connection with another peer endpoint for sending
    view data and events.
    """
    implements(interface.Peer)

    # Message header structure in struct format:
    # '!HBB'

    # elements:
    # - magicNumber: 9, http://futurama.wikia.com/wiki/Number_9_man
    # - messageType: see constants below
    # - messageSubType: see constants below, 0 in all but edit-messages
    messageHeaderFmt = '!HBB'
    messageHeaderSize = struct.calcsize(messageHeaderFmt)

    lastRecvdPayloadSize = 0
    lastSendPayloadSize = 0

    # connection can be an IListeningPort or IConnector
    connection = None
    host = None
    port = None

    # CLIENT or SERVER
    peerType = None
    # HOST_ROLE or PARTNER_ROLE
    role = None
    # STATE_CONNECTING, STATE_CONNECTED, STATE_DISCONNECTED
    state = None

    sharingWithUser = None
    view = None

    # callback method instances
    switchRole = None
    peerInitiatedDisconnect = None

    def __init__(self, username):
        self.sharingWithUser = username

    def hostConnect(self, port = 0):
        """
        Initiate a peer-to-peer session as the host by listening on the
        given port for a connection.

        @param port: C{int} port number to listen on, defaults to 0 (system will pick one)

        @return: the connected port number
        """
        self.peerType = interface.SERVER
        self.role = interface.HOST_ROLE
        self.state = interface.STATE_CONNECTING
        self.connection = reactor.listenTCP(port, self)
        logger.info('Listening for peers on port %d' % self.connection.getHost().port)
        return self.connection.getHost().port

    def clientConnect(self, host, port):
        """
        Initiate a peer-to-peer session as the partner by connecting to the
        host peer with the given host and port.

        @param host: ip address of the host Peer
        @param port: C{int} port number of the host Peer
        """
        logger.info('Connecting to peer at %s:%d' % (host, port))
        self.host = host
        self.port = port
        self.peerType = interface.CLIENT
        self.role = interface.PARTNER_ROLE
        self.state = interface.STATE_CONNECTING
        self.connection = reactor.connectTCP(self.host, self.port, self)

    def disconnect(self):
        """
        Disconnect from the peer-to-peer session.
        """
        if self.state == interface.STATE_DISCONNECTED:
            # already disconnected!
            return
        self.state = interface.STATE_DISCONNECTING
        if self.peerType == interface.SERVER:
            reactor.callFromThread(self.connection.stopListening)
            logger.debug('Telling peer to disconnect')
            self.sendMessage(interface.DISCONNECT)
        elif self.peerType == interface.CLIENT:
            reactor.callFromThread(self.connection.disconnect)

    def recvd_DISCONNECT(self, messsageSubType=None, payload=''):
        """
        Callback method if we receive a DISCONNECT message.
        """
        logger.debug('Disconnecting from peer at %s:%d' % (self.host, self.port))
        self.disconnect()
        self.state = interface.STATE_DISCONNECTED
        logger.info('Disconnected from peer %s' % self.sharingWithUser)

    def startCollab(self, view):
        """
        Send the provided C{sublime.View} contents to the connected peer.
        """
        pass

    def onStartCollab(self):
        """
        Callback method informing the peer to recieve the contents of a view.
        """
        pass

    def stopCollab(self):
        """
        Notify the connected peer that we are terminating the collaborating session.
        """
        pass

    def onStopCollab(self):
        """
        Callback method informing the peer that we are terminating a collaborating session.
        """
        pass

    def sendViewPositionUpdate(self, centerOnRegion):
        """
        Send a window view position update to the peer so they know what
        we are looking at.

        @param centerOnRegion: C{sublime.Region} of the current visible portion of the view to send to the peer.
        """
        pass

    def recvViewPositionUpdate(self, centerOnRegion):
        """
        Callback method for handling view position updates from the peer.

        @param centerOnRegion: C{sublime.Region} of the region to set as the current visible portion of the view.
        """
        pass

    def sendSelectionUpdate(self, selectedRegions):
        """
        Send currently selected regions to the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions in the current view.
        """
        pass

    def recvSelectionUpdate(self, selectedRegions):
        """
        Callback method for handling selected regions updates from the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions to be set.
        """
        pass

    def sendEdit(self, editType, content):
        """
        Send an edit event to the peer.

        @param editType: C{str} insert, edit, delete
        @param content: C{str} contents of the edit (None if delete editType)
        """
        pass

    def recvEdit(self, editType, content):
        """
        Callback method for handling edit events from the peer.

        @param editType: C{str} insert, edit, delete
        @param content: C{str} contents of the edit (None if delete editType)
        """
        pass

    def recvd_CONNECTED(self, messageSubType, payload):
        if self.peerType == interface.CLIENT:
            if self.state == interface.STATE_CONNECTING:
                self.state = interface.STATE_CONNECTED
                logger.info('Connected to peer: %s' % self.sharingWithUser)
            else:
                logger.error('Received CONNECTED message from server-peer when in state %s' % self.state)
        else:
            # client is connected, send ACK and set our state to be connected
            self.sendMessage(interface.CONNECTED)
            self.state = interface.STATE_CONNECTED
            logger.info('Connected to peer: %s' % self.sharingWithUser)

    def recvdUnknown(self, messageType, messageSubType, payload):
        logger.warn('Received unknown message: %s, %s, %s' % (messageType, messageSubType, payload))

    #*** basic.Int32StringReceiver method implementations ***#

    def stringReceived(self, data):
        magicNumber, msgTypeNum, msgSubTypeNum = struct.unpack(self.messageHeaderFmt, data[:self.messageHeaderSize])
        assert magicNumber == interface.MAGIC_NUMBER
        msgType = interface.numeric_to_symbolic[msgTypeNum]
        msgSubType = interface.numeric_to_symbolic[msgSubTypeNum]
        payload = data[self.messageHeaderSize:]
        logger.debug('RECVD: %s, %s, %d' % (msgType, msgSubType, len(payload)))
        method = getattr(self, "recvd_%s" % msgType, None)
        if method is not None:
            method(msgSubType, payload)
        else:
            self.recvdUnknown(msgType, msgSubType, payload)

    def connectionLost(self, reason):
        if self.peerType == interface.CLIENT:
            # ignore this, clientConnectionLost() below will also be called
            return
        self.state = interface.STATE_DISCONNECTED
        if error.ConnectionDone == reason.type:
            self.disconnect()
        else:
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    #*** protocol.Factory method implementations ***#

    def buildProtocol(self, addr):
        if self.peerType == interface.CLIENT:
            logger.debug('Connected to peer at %s:%d' % (self.host, self.port))
            self.sendMessage(interface.CONNECTED)
        return self

    #*** protocol.ClientFactory method implementations ***#

    def clientConnectionLost(self, connector, reason):
        self.state = interface.STATE_DISCONNECTED
        if error.ConnectionDone == reason.type:
            self.disconnect()
        else:
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    def clientConnectionFailed(self, connector, reason):
        logger.error('Connection failed: %s - %s' % (reason.type, reason.value))
        self.disconnect()

    #*** helper functions ***#

    def sendMessage(self, messageType, messageSubType=interface.EDIT_TYPE_NA, payload=''):
        logger.debug('SEND: %s-%s[%s]' % (interface.numeric_to_symbolic[messageType], interface.numeric_to_symbolic[messageSubType], payload))
        reactor.callFromThread(self.sendString, struct.pack(self.messageHeaderFmt, interface.MAGIC_NUMBER, messageType, messageSubType) + payload)

    def str(self):
        return self.sharingWithUser
