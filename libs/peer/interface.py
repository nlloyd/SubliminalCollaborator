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
from zope.interface import Interface

class Peer(Interface):
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

        @return: the connected port number on success, -1 on failure
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

    def onDisconnected():
        """
        Callback method if we are disconnected.
        """

    def startCollab(view):
        """
        Send the provided C{sublime.View} contents to the connected peer.
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

        @param editType: C{str} insert, edit, delete
        @param content: C{str} contents of the edit (None if delete editType)
        """

    def recvEdit(editType, content\):
        """
        Callback method for handling edit events from the peer.

        @param editType: C{str} insert, edit, delete
        @param content: C{str} contents of the edit (None if delete editType)
        """
