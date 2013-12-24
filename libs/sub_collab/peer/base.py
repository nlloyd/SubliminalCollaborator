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
from sub_collab import common


#################################################################################
# - magicNumber: 9, http://futurama.wikia.com/wiki/Number_9_man
MAGIC_NUMBER = 9

CLIENT = 'client'
SERVER = 'server'
PARTNER_ROLE = 'partner'
HOST_ROLE = 'host'

# states #
STATE_CONNECTING = 'connecting'
STATE_CONNECTED = 'connected'
STATE_REJECT_TRIGGERED_DISCONNECTING = 'disconnecting-on-rejected'
STATE_DISCONNECTING = 'disconnecting'
STATE_DISCONNECTED = 'disconnected'

#*** constants representing message types and sub-types ***#

#--- message types ---#
# sent by client-peer on connection, sent back by server as ACK
CONNECTED       = 0
# sent by client-peer prior to disconnect, sent back by server as ACK
DISCONNECT      = 1
# sent to signal to the peer to prepare to receive a view, payload is the base filename
SHARE_VIEW      = 2
# sent in reply to a SHARE_VIEW
SHARE_VIEW_ACK  = 3
# chunk of view data
VIEW_CHUNK      = 4
# sent in reply to a VIEW_CHUNK, with payloadSize indicating what was received
VIEW_CHUNK_ACK  = 5
# sent to signal to the peer that the entire view has been sent
END_OF_VIEW     = 6
END_OF_VIEW_ACK = 7
# sent in reply to an END_OF_VIEW_ACK to indicate that the bytes sent != bytes recvd
BAD_VIEW_SEND   = 8
# send the syntax config associated with the shared file
SYNTAX          = 9
# view selection payload
SELECTION       = 10
# view position payload
POSITION        = 11
# swap session roles
SWAP_ROLE       = 12
# sent if the peer accepts the swap role request
SWAP_ROLE_ACK   = 13
# sent if the peer denies the swap role request
SWAP_ROLE_NACK  = 14
# view sync message (payload is host view size)
VIEW_SYNC       = 15
# view resync request (client-to-host... need to resend the view as it is now)
VIEW_RESYNC     = 16
# view reshare request, like SHARE_VIEW but refreshes the buffer instead of creating a new buffer
RESHARE_VIEW    = 17
# edit event payload
EDIT            = 100

#--- message sub-types ---#
EDIT_TYPE_NA                = 120  # not applicable, sent by all but EDIT
EDIT_TYPE_INSERT            = 121
EDIT_TYPE_INSERT_SNIPPET    = 122
EDIT_TYPE_LEFT_DELETE       = 123
EDIT_TYPE_RIGHT_DELETE      = 124
EDIT_TYPE_CUT               = 125
EDIT_TYPE_COPY              = 126
EDIT_TYPE_PASTE             = 127
EDIT_TYPE_UNDO              = 128
EDIT_TYPE_REDO              = 129
EDIT_TYPE_REDO_OR_REPEAT    = 130
EDIT_TYPE_SOFT_UNDO         = 131
EDIT_TYPE_SOFT_REDO         = 132

symbolic_to_numeric = {
    'CONNECTED':                0,
    'DISCONNECT':               1,
    'SHARE_VIEW':               2,
    'SHARE_VIEW_ACK':           3,
    'VIEW_CHUNK':               4,
    'VIEW_CHUNK_ACK':           5,
    'END_OF_VIEW':              6,
    'END_OF_VIEW_ACK':          7,
    'BAD_VIEW_SEND':            8,
    'SYNTAX':                   9,
    'SELECTION':                10,
    'POSITION':                 11,
    'SWAP_ROLE':                12,
    'SWAP_ROLE_ACK':            13,
    'SWAP_ROLE_NACK':           14,
    'VIEW_SYNC':                15,
    'VIEW_RESYNC':              16,
    'RESHARE_VIEW':             17,
    'EDIT':                     100,
    'EDIT_TYPE_NA':             120,
    'EDIT_TYPE_INSERT':         121,
    'EDIT_TYPE_INSERT_SNIPPET': 122,
    'EDIT_TYPE_LEFT_DELETE':    123,
    'EDIT_TYPE_RIGHT_DELETE':   124,
    'EDIT_TYPE_CUT':            125,
    'EDIT_TYPE_COPY':           126,
    'EDIT_TYPE_PASTE':          127,
    'EDIT_TYPE_UNDO':           128,
    'EDIT_TYPE_REDO':           129,
    'EDIT_TYPE_REDO_OR_REPEAT': 130,
    'EDIT_TYPE_SOFT_UNDO':      131,
    'EDIT_TYPE_SOFT_REDO':      132
}

# tyvm twisted/words/protocols/irc.py for this handy dandy trick!
numeric_to_symbolic = {}
for k, v in symbolic_to_numeric.items():
    numeric_to_symbolic[v] = k

#################################################################################

class IPeer(Interface):
    """
    One side of a peer-to-peer collaboration connection.
    This is a direct connection with another peer endpoint for sending
    view data and events.
    """

    def hostConnect(port = None):
        """
        Initiate a peer-to-peer session as the host by listening on the
        given port for a connection.

        @param port: C{int} port number to listen on, or None for any available

        @return: the connected port number
        """

    def clientConnect(host, port):
        """
        Initiate a peer-to-peer session as the partner by connecting to the
        host peer with the given host and port.

        @param host: ip address of the host Peer
        @param port: C{int} port number of the host Peer

        @return: True on success
        """

    def disconnect():
        """
        Disconnect from the peer-to-peer session.
        """

    def onDisconnect():
        """
        Callback method if we are disconnected.
        """

    def startCollab(view):
        """
        Send the provided C{sublime.View} contents to the connected peer.
        """

    def resyncCollab():
        """
        Resync the shared editor contents between the host and the partner.
        """

    def onStartCollab():
        """
        Callback method informing the peer to recieve the contents of a view.
        """

    def stopCollab():
        """
        Notify the connected peer that we are terminating the collaborating session.
        """

    def onStopCollab():
        """
        Callback method informing the peer that we are terminating a collaborating session.
        """

    def swapRole():
        """
        Request a role swap with the connected peer.
        """

    def onSwapRole():
        """
        Callback method to respond to role swap requests from the connected peer.
        """

    def onSwapRoleAck():
        """
        Callback method to respond to accepted role swap response from the connected peer.
        The caller of swapRole() waits for this method before actually swapping roles on its side.
        """

    def onSwapRoleNAck():
        """
        Callback method to respond to rejected role swap response from the connected peer.
        The caller of swapRole() may have this called if the connected peer rejects a swap role request.
        """

    def sendViewPositionUpdate(centerOnRegion):
        """
        Send a window view position update to the peer so they know what
        we are looking at.

        @param centerOnRegion: C{sublime.Region} of the current visible portion of the view to send to the peer.
        """

    def recvViewPositionUpdate(centerOnRegion):
        """
        Callback method for handling view position updates from the peer.

        @param centerOnRegion: C{sublime.Region} of the region to set as the current visible portion of the view.
        """

    def sendSelectionUpdate(selectedRegions):
        """
        Send currently selected regions to the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions in the current view.
        """

    def recvSelectionUpdate(selectedRegions):
        """
        Callback method for handling selected regions updates from the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions to be set.
        """

    def sendEdit(editType, content):
        """
        Send an edit event to the peer.

        @param editType: C{str} edit type (see above)
        @param content: C{Array} contents of the edit (None if delete editType)
        """

    def recvEdit(editType, content):
        """
        Callback method for handling edit events from the peer.

        @param editType: C{str} edit type (see above)
        @param content: C{Array} contents of the edit (None if delete editType)
        """


class BasePeer(common.Observable):
    """
    Base implementation of IPeer interface that provides a constructor
    for all subclasses to use requiring a c{str} for the peer username and
    a reference to the C{INegotiator} implementation that created the session.
    """
    implements(IPeer)


    def __init__(self, username, parentNegotiator):
        common.Observable.__init__(self)
        self.sharingWithUser = username
        # just keep the id, otherwise reconfig with active sessions could result in memory leak
        self.parentNegotiatorKey = parentNegotiator.getId()
        # inherit all observers of the parent negotiator
        self.addAllObservers(parentNegotiator.observers)


    def getParentNegotiatorKey(self):
        return self.parentNegotiatorKey


    def str(self):
        return self.sharingWithUser
