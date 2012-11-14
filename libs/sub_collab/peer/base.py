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
from sub_collab.peer import interface
from twisted.internet import reactor, protocol, error, interfaces
from twisted.protocols import basic
from sub_collab import status_bar
import sublime
import logging, threading, sys, socket, struct, os, re, time

logger = logging.getLogger(__name__)
logger.propagate = False
# purge previous handlers set... for plugin reloading
del logger.handlers[:]
stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(logging.Formatter(fmt='[SubliminalCollaborator|Peer(%(levelname)s): %(message)s]'))
logger.addHandler(stdoutHandler)
logger.setLevel(logging.DEBUG)


# in bytes
MAX_CHUNK_SIZE = 1024

REGION_PATTERN = re.compile('(\d+), (\d+)')


class ViewPositionThread(threading.Thread):
    def __init__(self, peer):
        threading.Thread.__init__(self)
        self.peer = peer
        self.lastViewCenterLine = None

    def grabAndSendViewPosition(self):
        """
        Separate function to be called from the sublime main thread...
        because the view.visible_region() function demands that.
        """
        # calculate the center-most line in the view
        # this will match most closely with the true center of the view
        viewRegionLines = self.peer.view.split_by_newlines(self.peer.view.visible_region())
        lineIdx = len(viewRegionLines) / 2 - 1
        if lineIdx < 0:
            lineIdx = 0
        viewCenterRegion = viewRegionLines[lineIdx]
        if not viewCenterRegion == self.lastViewCenterLine:
            self.lastViewCenterLine = viewCenterRegion
            self.peer.sendViewPositionUpdate(viewCenterRegion)

    def run(self):
        logger.info('Monitoring view position')
        # we must be the host and connected
        while (self.peer.role == interface.HOST_ROLE) and (self.peer.state == interface.STATE_CONNECTED):
            if not self.peer.view == None:
                sublime.set_timeout(self.grabAndSendViewPosition, 0)
            time.sleep(0.5)
        logger.info('Stopped monitoring view position')

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

    # registered callback methods
    switchRole = None
    peerInitiatedDisconnect = None
    # callback for the server-peer
    peerConnectedCallback = None
    # callback for the client-peer
    peerRecvdViewCallback = None

    def __init__(self, username, failedToInitConnectCallback=None):
        self.sharingWithUser = username
        # connection can be an IListeningPort or IConnector
        self.connection = None
        self.host = None
        self.port = None
        # CLIENT or SERVER
        self.peerType = None
        # HOST_ROLE or PARTNER_ROLE
        self.role = None
        # STATE_CONNECTING, STATE_CONNECTED, STATE_DISCONNECTED
        self.state = None
        self.view = None
        self.failedToInitConnectCallback = failedToInitConnectCallback
        # queue of 2 or 3 part tuples
        self.toDoToViewQueue = []
        self.toDoToViewQueueLock = threading.Lock()
        # thread for polling host-side view
        self.viewPositionPollingThread = ViewPositionThread(self)
        # last collected command tuple (str, dict, int)
        self.lastViewCommand = ('', {}, 0)

    def hostConnect(self, port = 0, ipaddress=''):
        """
        Initiate a peer-to-peer session as the host by listening on the
        given port for a connection.

        @param port: C{int} port number to listen on, defaults to 0 (system will pick one)

        @return: the connected port number
        """
        self.peerType = interface.SERVER
        self.role = interface.HOST_ROLE
        self.state = interface.STATE_CONNECTING
        self.connection = reactor.listenTCP(port, self, backlog=1, interface=ipaddress)
        self.port = self.connection.getHost().port
        logger.info('Listening for peers at %s:%d' % (ipaddress, self.port))
        return self.port

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
        self.connection = reactor.connectTCP(self.host, self.port, self, timeout=1)

    def disconnect(self):
        """
        Disconnect from the peer-to-peer session.
        """
        self.stopCollab()
        if self.state == interface.STATE_DISCONNECTED:
            # already disconnected!
            return
        earlierState = self.state
        self.state = interface.STATE_DISCONNECTING
        if self.transport != None:
            self.sendMessage(interface.DISCONNECT)
        if self.peerType == interface.SERVER:
            logger.debug('Closing server-side connection')
            reactor.callFromThread(self.connection.stopListening)
        elif self.peerType == interface.CLIENT:
            logger.debug('Closing client-side connection')
            reactor.callFromThread(self.connection.disconnect)

    def startCollab(self, view):
        """
        Send the provided C{sublime.View} contents to the connected peer.
        """
        self.view = view
        self.view.set_read_only(True)
        viewName = self.view.file_name()
        if not viewName == None:
            viewName = os.path.basename(viewName)
        else:
            viewName = 'NONAME'
        totalToSend = self.view.size()
        begin = 0
        end = MAX_CHUNK_SIZE
        # now we make sure we are connected... better way to do this?
        while not self.state == interface.STATE_CONNECTED:
            time.sleep(1.0)
            if (self.state == interface.STATE_DISCONNECTING) or (self.state == interface.STATE_DISCONNECTED):
                logger.error('While waiting to share view over a connection the peer was disconnected!')
                self.disconnect()
                return
        logger.info('Sharing view %s with %s' % (self.view.file_name(), self.sharingWithUser))
        self.toAck = []
        self.sendMessage(interface.SHARE_VIEW, payload=('%s|%s' % (viewName, totalToSend)))
        while begin < totalToSend:
            chunkToSend = self.view.substr(sublime.Region(begin, end))
            self.toAck.append(len(chunkToSend))
            self.sendMessage(interface.VIEW_CHUNK, payload=chunkToSend)
            begin = begin + MAX_CHUNK_SIZE
            end = end + MAX_CHUNK_SIZE
            status_bar.progress_message("sending view to %s" % self.sharingWithUser, begin, totalToSend)
        self.sendMessage(interface.END_OF_VIEW, payload=view.settings().get('syntax'))
        self.view.set_read_only(False)
        # start the view position polling thread
        self.viewPositionPollingThread.start()

    def onStartCollab(self):
        """
        Callback method informing the peer that we have received the view.
        """
        logger.debug('collaboration session with view started!')
        if self.peerRecvdViewCallback:
            self.peerRecvdViewCallback(self)

    def stopCollab(self):
        """
        Notify the connected peer that we are terminating the collaborating session.
        """
        if (self.peerType == interface.CLIENT) and (self.view != None):
            self.view.set_read_only(False)
            self.view = None
        status_bar.status_message('stopped sharing with %s' % self.str())

    def onStopCollab(self):
        """
        Callback method informing the peer that we are terminating a collaborating session.
        """
        self.stopCollab()

    def sendViewPositionUpdate(self, centerOnRegion):
        """
        Send a window view position update to the peer so they know what
        we are looking at.

        @param centerOnRegion: C{sublime.Region} of the central-most line of the current visible portion of the view to send to the peer.
        """
        status_bar.heartbeat_message('sharing with %s' % self.str())
        self.sendMessage(interface.POSITION, payload=str(centerOnRegion))

    def recvViewPositionUpdate(self, centerOnRegion):
        """
        Callback method for handling view position updates from the peer.

        @param centerOnRegion: C{sublime.Region} to set as the current center of the view.
        """
        self.view.show_at_center(centerOnRegion)

    def sendSelectionUpdate(self, selectedRegions):
        """
        Send currently selected regions to the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions in the current view.
        """
        status_bar.heartbeat_message('sharing with %s' % self.str())
        self.sendMessage(interface.SELECTION, payload=str(selectedRegions))

    def recvSelectionUpdate(self, selectedRegions):
        """
        Callback method for handling selected regions updates from the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions to be set.
        """
        self.view.add_regions(self.sharingWithUser, selectedRegions, 'comment', sublime.DRAW_OUTLINED)

    def sendEdit(self, editType, content=None):
        """
        Send an edit event to the peer.

        @param editType: C{str} edit type (see above)
        @param content: C{Array} contents of the edit (None-able)
        """
        status_bar.heartbeat_message('sharing with %s' % self.str())
        logger.debug('sending edit: %s %s' %(interface.numeric_to_symbolic[editType], content))
        if (editType == interface.EDIT_TYPE_INSERT) \
            or (editType == interface.EDIT_TYPE_INSERT_SNIPPET) \
            or (editType == interface.EDIT_TYPE_PASTE):
            self.sendMessage(interface.EDIT, editType, payload=content)
        else:
            self.sendMessage(interface.EDIT, editType)

    def recvEdit(self, editType, content):
        """
        Callback method for handling edit events from the peer.

        @param editType: C{str} edit type (see above)
        @param content: C{Array} contents of the edit (None if delete editType)
        """
        self.view.set_read_only(False)
        if editType == interface.EDIT_TYPE_INSERT:
            self.view.run_command('insert', { 'characters': content })
        elif editType == interface.EDIT_TYPE_INSERT_SNIPPET:
            self.view.run_command('insert_snippet', { 'contents': content })
        elif editType == interface.EDIT_TYPE_LEFT_DELETE:
            self.view.run_command('left_delete')
        elif editType == interface.EDIT_TYPE_RIGHT_DELETE:
            self.view.run_command('right_delete')
        elif editType == interface.EDIT_TYPE_CUT:
            # faux cut since we are recieving the commands instead of invoking them directly
            self.view.run_command('left_delete')
        elif editType == interface.EDIT_TYPE_COPY:
            # we dont actually want to do anything here
            pass
        elif editType == interface.EDIT_TYPE_PASTE:
            # faux cut since we are recieving the commands instead of invoking them directly
            self.view.run_command('insert', { 'characters': content })
        elif editType == interface.EDIT_TYPE_UNDO:
            self.view.run_command('undo')
        elif editType == interface.EDIT_TYPE_REDO:
            self.view.run_command('redo')
        elif editType == interface.EDIT_TYPE_REDO_OR_REPEAT:
            self.view.run_command('redo_or_repeat')
        elif editType == interface.EDIT_TYPE_SOFT_UNDO:
            self.view.run_command('soft_undo')
        elif editType == interface.EDIT_TYPE_SOFT_REDO:
            self.view.run_command('soft_redo')
        self.view.set_read_only(True)

    def handleViewChanges(self):
        """
        Runs on the main UI event loop.
        Goes through the list of events queued up to modify the shared view
        and applies them to the associated view.
        """
        self.toDoToViewQueueLock.acquire()
        while len(self.toDoToViewQueue) > 0:
            toDo = self.toDoToViewQueue.pop(0)
            if len(toDo) == 2:
                logger.debug('Handling view change %s with size %d payload' % (interface.numeric_to_symbolic[toDo[0]], len(toDo[1])))
                if toDo[0] == interface.SHARE_VIEW:
                    self.view = sublime.active_window().new_file()
                    payloadBits = toDo[1].split('|')
                    if payloadBits[0] == 'NONAME':
                        self.view.set_name('SHARING-WITH-%s' % self.sharingWithUser)
                    else:
                        self.view.set_name(payloadBits[0])
                    self.view.set_read_only(True)
                    self.view.set_scratch(True)
                    self.viewPopulateEdit = self.view.begin_edit()
                    self.totalNewViewSize = int(payloadBits[1])
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                elif toDo[0] == interface.VIEW_CHUNK:
                    self.view.set_read_only(False)
                    self.view.insert(self.viewPopulateEdit, self.view.size(), toDo[1])
                    self.view.set_read_only(True)
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                elif toDo[0] == interface.END_OF_VIEW:
                    self.view.end_edit(self.viewPopulateEdit)
                    self.view.set_syntax_file(toDo[1])
                    self.viewPopulateEdit = None
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                    # view is populated and configured, lets share!
                    self.onStartCollab()
                elif toDo[0] == interface.SELECTION:
                    status_bar.heartbeat_message('sharing with %s' % self.str())
                    regions = []
                    for regionMatch in REGION_PATTERN.finditer(toDo[1]):
                        regions.append(sublime.Region(int(regionMatch.group(1)), int(regionMatch.group(2))))
                    self.recvSelectionUpdate(regions)
                elif toDo[0] == interface.POSITION:
                    status_bar.heartbeat_message('sharing with %s' % self.str())
                    regionMatch = REGION_PATTERN.search(toDo[1])
                    if regionMatch:
                        self.recvViewPositionUpdate(sublime.Region(int(regionMatch.group(1)), int(regionMatch.group(2))))
            elif len(toDo) == 3:
                status_bar.heartbeat_message('sharing with %s' % self.str())
                # edit event
                assert toDo[0] == interface.EDIT
                # make the shared selection the ACTUAL selection
                self.view.sel().clear()
                for region in self.view.get_regions(self.sharingWithUser):
                    self.view.sel().add(region)
                self.view.erase_regions(self.sharingWithUser)
                self.recvEdit(toDo[1], toDo[2])
        self.toDoToViewQueueLock.release()

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
            sublime.set_timeout(self.peerConnectedCallback, 0)

    def recvd_DISCONNECT(self, messageSubType=None, payload=''):
        """
        Callback method if we receive a DISCONNECT message.
        """
        if self.peerType == interface.CLIENT:
            logger.debug('Disconnecting from peer at %s:%d' % (self.host, self.port))
        else:
            logger.debug('Disconnecting from peer at %d' % self.port)
        self.disconnect()
        self.state = interface.STATE_DISCONNECTED
        logger.info('Disconnected from peer %s' % self.sharingWithUser)
        status_bar.status_message('Stopped sharing with %s' % self.sharingWithUser)

    def recvd_SHARE_VIEW(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.SHARE_VIEW, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(interface.SHARE_VIEW_ACK)
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvd_SHARE_VIEW_ACK(self, messageSubType, payload):
        self.ackdChunks = []

    def recvd_VIEW_CHUNK(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.VIEW_CHUNK, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(interface.VIEW_CHUNK_ACK, payload=str(len(payload)))
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvd_VIEW_CHUNK_ACK(self, messageSubType, payload):
        ackdChunkSize = int(payload)
        self.ackdChunks.append(ackdChunkSize)

    def recvd_END_OF_VIEW(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.END_OF_VIEW, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(interface.END_OF_VIEW_ACK)
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvd_END_OF_VIEW_ACK(self, messageSubType, payload):
        if self.toAck == self.ackdChunks:
            self.toAck = None
            self.ackdChunks = None
        else:
            logger.error('Sent %s chunks of data to peer but peer received %s chunks of data' % (self.toAck, self.ackdChunks))
            self.toAck = None
            self.ackdChunks = None
            self.sendMessage(interface.BAD_VIEW_SEND)
            self.disconnect()

    def recvd_SELECTION(self, messageSubType, payload):
        # logger.debug('selection change: %s' % payload)
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.SELECTION, payload))
        self.toDoToViewQueueLock.release()
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvd_POSITION(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.POSITION, payload))
        self.toDoToViewQueueLock.release()
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvd_EDIT(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((interface.EDIT, messageSubType, payload))
        self.toDoToViewQueueLock.release()
        sublime.set_timeout(self.handleViewChanges, 0)

    def recvdUnknown(self, messageType, messageSubType, payload):
        logger.warn('Received unknown message: %s, %s, %s' % (messageType, messageSubType, payload))

    def stringReceived(self, data):
        magicNumber, msgTypeNum, msgSubTypeNum = struct.unpack(self.messageHeaderFmt, data[:self.messageHeaderSize])
        assert magicNumber == interface.MAGIC_NUMBER
        msgType = interface.numeric_to_symbolic[msgTypeNum]
        msgSubType = interface.numeric_to_symbolic[msgSubTypeNum]
        payload = data[self.messageHeaderSize:]
        logger.debug('RECVD: %s-%s[%s]' % (msgType, msgSubType, payload))
        method = getattr(self, "recvd_%s" % msgType, None)
        if method is not None:
            method(msgSubTypeNum, payload)
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
            status_bar.heartbeat_message('lost share session with %s' % self.str())
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    #*** protocol.Factory method implementations ***#

    def buildProtocol(self, addr):
        logger.debug('building protocol for %s' % self.peerType)
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
            status_bar.heartbeat_message('lost share session with %s' % self.str())
            # may want to reconnect, but for now lets print why
            logger.error('Connection lost: %s - %s' % (reason.type, reason.value))

    def clientConnectionFailed(self, connector, reason):
        logger.error('Connection failed: %s - %s' % (reason.type, reason.value))
        self.state = interface.STATE_DISCONNECTED
        if (error.ConnectionRefusedError == reason.type) or (error.TCPTimedOutError == reason.type) or (error.TimeoutError == reason.type):
            if (self.peerType == interface.CLIENT) and (not self.failedToInitConnectCallback == None):
                self.failedToInitConnectCallback(self.sharingWithUser)
        self.disconnect()

    #*** helper functions ***#

    def sendMessage(self, messageType, messageSubType=interface.EDIT_TYPE_NA, payload=''):
        logger.debug('SEND: %s-%s[%s]' % (interface.numeric_to_symbolic[messageType], interface.numeric_to_symbolic[messageSubType], payload))
        reactor.callFromThread(self.sendString, struct.pack(self.messageHeaderFmt, interface.MAGIC_NUMBER, messageType, messageSubType) + payload.encode())

    def str(self):
        return self.sharingWithUser
