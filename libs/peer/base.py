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
from twisted.internet import reactor, protocol, threads, interfaces
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


#################################################################################
MAGIC_NUMBER = 9

CLIENT = 'client'
SERVER = 'server'
PARTNER_ROLE = 'partner'
HOST_ROLE = 'host'

# states #
STATE_CONNECTING = 'connecting'
STATE_CONNECTED = 'connected'
STATE_DISCONNECTING = 'disconnecting'
STATE_DISCONNECTED = 'disconnected'

#*** constants representing message types and sub-types ***#

#--- message types ---#
# sent by client-peer on connection, sent back by server as ACK
CONNECTED = 0
# sent by client-peer prior to disconnect, sent back by server as ACK
DISCONNECT = 1
# sent to signal to the peer to prepare to receive a view, payloadSize == number of chunks to expect total
SHARE_VIEW = 2
# sent in reply to a SHARE_VIEW
SHARE_VIEW_ACK = 3
# chunk of view data
VIEW_CHUNK = 4
# sent in reply to a VIEW_CHUNK, with payloadSize indicating what was received
VIEW_CHUNK_ACK = 5
# sent instead of VIEW_CHUNK if sent != recvd payload sizes
VIEW_CHUNK_ERROR = 6
# sent to signal to the peer that the entire view has been sent
END_OF_VIEW = 7
END_OF_VIEW_ACK = 8
# view selection payload
SELECTION = 9
# edit event payload
EDIT = 10

#--- message sub-types ---#
EDIT_TYPE_NA = 11  # not applicable, sent by all but EDIT
# TODO figure out the rest

symbolic_to_numeric = {
    'CONNECTED': 0,
    'DISCONNECT': 1,
    'SHARE_VIEW': 2,
    'SHARE_VIEW_ACK': 3,
    'VIEW_CHUNK': 4,
    'VIEW_CHUNK_ACK': 5,
    'VIEW_CHUNK_ERROR': 6,
    'END_OF_VIEW': 7,
    'END_OF_VIEW_ACK': 8,
    'SELECTION': 9,
    'EDIT': 10,
    'EDIT_TYPE_NA': 11
}

# tyvm twisted/words/protocols/irc.py for this handy dandy trick!
numeric_to_symbolic = {}
for k, v in symbolic_to_numeric.items():
    numeric_to_symbolic[v] = k

#################################################################################


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

    def __init__(self, username):
        self.sharingWithUser = username

    def hostConnect(self, port = 0):
        """
        Initiate a peer-to-peer session as the host by listening on the
        given port for a connection.

        @param port: C{int} port number to listen on, defaults to 0 (system will pick one)

        @return: the connected port number
        """
        self.peerType = SERVER
        self.role = HOST_ROLE
        self.state = STATE_CONNECTING
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
        self.peerType = CLIENT
        self.role = PARTNER_ROLE
        self.state = STATE_CONNECTING
        self.connection = reactor.connectTCP(self.host, self.port, self)

    def disconnect(self):
        """
        Disconnect from the peer-to-peer session.
        """
        if self.state == STATE_DISCONNECTING:
            if self.peerType == SERVER:
                self.connection.stopListening()
            elif self.peerType == CLIENT:
                self.connection.disconnect()

    def onDisconnected(self):
        """
        Callback method if we are disconnected.
        """
        pass

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
        if self.peerType == CLIENT:
            if self.state == STATE_CONNECTING:
                self.state = STATE_CONNECTED
                logger.info('Connected to peer: %s' % self.sharingWithUser)
            else:
                logger.error('Received CONNECTED message from server-peer when in state %s' % self.state)
        else:
            # client is connected, send ACK and set our state to be connected
            self.sendMessage(CONNECTED)
            self.state = STATE_CONNECTED
            logger.info('Connected to peer: %s' % self.sharingWithUser)

    def recvdUnknown(self, messageType, messageSubType, payload):
        logger.warn('Received unknown message: %s, %s, %s' % (messageType, messageSubType, payload))

    #*** basic.Int32StringReceiver method implementations ***#

    def stringReceived(self, data):
        magicNumber, msgTypeNum, msgSubTypeNum = struct.unpack(self.messageHeaderFmt, data[:self.messageHeaderSize])
        assert magicNumber == MAGIC_NUMBER
        msgType = numeric_to_symbolic[msgTypeNum]
        msgSubType = numeric_to_symbolic[msgSubTypeNum]
        payload = data[self.messageHeaderSize:]
        logger.debug('RECVD: %s, %s, %d' % (msgType, msgSubType, len(payload)))
        method = getattr(self, "recvd_%s" % msgType, None)
        if method is not None:
            method(msgSubType, payload)
        else:
            self.recvdUnknown(msgType, msgSubType, payload)

    def connectionLost(self, reason):
        if type(protocol.connectionDone) == reason.type:
            self.disconnect()
        else:
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    #*** protocol.Factory method implementations ***#

    def buildProtocol(self, addr):
        if self.peerType == CLIENT:
            logger.info('Connected to peer at %s:%d' % (self.host, self.port))
            self.sendMessage(CONNECTED)
        return self

    #*** protocol.ClientFactory method implementations ***#

    def clientConnectionLost(self, connector, reason):
        print protocol.connectionDone
        if type(protocol.connectionDone) == reason.type:
            self.disconnect()
        else:
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    def clientConnectionFailed(self, connector, reason):
        logger.error('Connection failed: %s - %s' % (reason.type, reason.value))
        self.disconnect()

    #*** helper functions ***#

    def sendMessage(self, messageType, messageSubType=EDIT_TYPE_NA, payload=''):
        logger.debug('SEND: %s-%s[%s]' % (numeric_to_symbolic[messageType], numeric_to_symbolic[messageSubType], payload))
        reactor.callFromThread(self.sendString, struct.pack(self.messageHeaderFmt, MAGIC_NUMBER, messageType, messageSubType) + payload)

    def str(self):
        return self.sharingWithUser
