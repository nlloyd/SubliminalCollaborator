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
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#   THE SOFTWARE.
from zope.interface import implements
from sub_collab.peer import base
from twisted.internet import reactor, protocol, error, interfaces
from twisted.protocols import basic
from sub_collab import registry, status_bar
from sub_collab import event as collab_event
import sublime
import logging, threading, sys, socket, struct, os, re, time, functools


# in bytes
MAX_CHUNK_SIZE = 1024

REGION_PATTERN = re.compile('(\d+), (\d+)')


class ViewMonitorThread(threading.Thread):

    logger = logging.getLogger('SubliminalCollaborator.ViewMonitor')


    def __init__(self, peer):
        threading.Thread.__init__(self)
        self.peer = peer
        self.lastViewCenterLine = None
        self.shutdown = False


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


    def sendViewSize(self):
        self.peer.sendMessage(base.VIEW_SYNC, payload=str(self.peer.view.size()))


    def run(self):
        self.logger.info('Monitoring view')
        count = 0
        # we must be the host and connected
        while (self.peer.role == base.HOST_ROLE) \
                and (self.peer.state == base.STATE_CONNECTED) \
                and (not self.shutdown):
            if not self.peer.view == None:
                sublime.set_timeout(self.grabAndSendViewPosition, 0)
                if count == 10:
                    count = 0
                    sublime.set_timeout(self.sendViewSize, 0)
            time.sleep(0.5)
            count += 1
        self.logger.info('Stopped monitoring view')


    def destroy(self):
        self.shutdown = True


# build off of the Int32StringReceiver to leverage its unprocessed buffer handling
class BasicPeer(base.BasePeer, basic.Int32StringReceiver, protocol.ClientFactory, protocol.ServerFactory):
    """
    One side of a peer-to-peer collaboration connection.
    This is a direct connection with another peer endpoint for sending
    view data and events.
    """
    logger = logging.getLogger('SubliminalCollaborator.BasicPeer')

    # Message header structure in struct format:
    # '!HBB'

    # elements:
    # - magicNumber: 9, http://futurama.wikia.com/wiki/Number_9_man
    # - messageType: see constants below
    # - messageSubType: see constants below, 0 in all but edit-messages
    messageHeaderFmt = '!HBB'
    messageHeaderSize = struct.calcsize(messageHeaderFmt)


    def __init__(self, username, parentNegotiator):
        base.BasePeer.__init__(self, username, parentNegotiator)
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
        # queue of 2 or 3 part tuples
        self.toDoToViewQueue = []
        self.toDoToViewQueueLock = threading.Lock()
        # thread for polling host-side view and periodically checking view sync state
        self.viewMonitorThread = ViewMonitorThread(self)
        # last collected command tuple (str, dict, int)
        self.lastViewCommand = ('', {}, 0)
        # flag to inform EventListener if Proxy plugin is sending events
        # relates to a selection update issue around the cut command
        self.isProxyEventPublishing = False


    def hostConnect(self, port = 0, ipaddress=''):
        """
        Initiate a peer-to-peer session as the host by listening on the
        given port for a connection.

        @param port: C{int} port number to listen on, defaults to 0 (system will pick one)

        @return: the connected port number
        """
        self.peerType = base.SERVER
        self.role = base.HOST_ROLE
        self.state = base.STATE_CONNECTING
        self.connection = reactor.listenTCP(port, self, backlog=1, interface=ipaddress)
        self.port = self.connection.getHost().port
        self.logger.info('Listening for peers at %s:%d' % (ipaddress, self.port))
        return self.port


    def clientConnect(self, host, port):
        """
        Initiate a peer-to-peer session as the partner by connecting to the
        host peer with the given host and port.

        @param host: ip address of the host Peer
        @param port: C{int} port number of the host Peer
        """
        self.logger.info('Connecting to peer at %s:%d' % (host, port))
        self.host = host
        self.port = port
        self.peerType = base.CLIENT
        self.role = base.PARTNER_ROLE
        self.state = base.STATE_CONNECTING
        self.connection = reactor.connectTCP(self.host, self.port, self, timeout=5)


    def disconnect(self):
        """
        Disconnect from the peer-to-peer session.
        """
        self.stopCollab()
        if self.state == base.STATE_DISCONNECTED:
            # already disconnected!
            return
        earlierState = self.state
        self.state = base.STATE_DISCONNECTING
        if self.transport != None:
            self.sendMessage(base.DISCONNECT)
        if self.peerType == base.SERVER:
            self.logger.debug('Closing server-side connection')
            # self.connection.stopListening()
            reactor.callFromThread(self.connection.stopListening)
        elif self.peerType == base.CLIENT:
            self.logger.debug('Closing client-side connection')
            # self.connection.disconnect()
            reactor.callFromThread(self.connection.disconnect)


    def onDisconnect(self):
        """
        Callback method if we are disconnected.
        """
        if self.peerType == base.CLIENT:
            self.logger.debug('Disconnecting from peer at %s:%d' % (self.host, self.port))
        else:
            self.logger.debug('Disconnecting from peer at %d' % self.port)
        self.disconnect()
        self.state = base.STATE_DISCONNECTED
        self.logger.info('Disconnected from peer %s' % self.sharingWithUser)
        status_bar.status_message('Stopped sharing with %s' % self.sharingWithUser)


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
        while not self.state == base.STATE_CONNECTED:
            time.sleep(1.0)
            if (self.state == base.STATE_DISCONNECTING) or (self.state == base.STATE_DISCONNECTED):
                self.logger.error('While waiting to share view over a connection the peer was disconnected!')
                self.disconnect()
                return
        self.logger.info('Sharing view %s with %s' % (self.view.file_name(), self.sharingWithUser))
        self.toAck = []
        self.sendMessage(base.SHARE_VIEW, payload=('%s|%s' % (viewName, totalToSend)))
        while begin < totalToSend:
            chunkToSend = self.view.substr(sublime.Region(begin, end))
            self.toAck.append(len(chunkToSend))
            self.sendMessage(base.VIEW_CHUNK, payload=chunkToSend)
            begin = begin + MAX_CHUNK_SIZE
            end = end + MAX_CHUNK_SIZE
            status_bar.progress_message("sending view to %s" % self.sharingWithUser, begin, totalToSend)
        self.sendMessage(base.END_OF_VIEW, payload=view.settings().get('syntax'))
        self.view.set_read_only(False)
        # start the view monitoring thread
        self.viewMonitorThread.start()


    def resyncCollab(self):
        """
        Resync the shared editor contents between the host and the partner.
        """
        status_bar.status_message('RESYNCING VIEW CONTENT WITH PEER')
        self.view.set_read_only(True)
        totalToSend = self.view.size()
        begin = 0
        end = MAX_CHUNK_SIZE
        # now we make sure we are connected... better way to do this?
        while not self.state == base.STATE_CONNECTED:
            time.sleep(1.0)
            if (self.state == base.STATE_DISCONNECTING) or (self.state == base.STATE_DISCONNECTED):
                self.logger.error('While waiting to resync view over a connection the peer was disconnected!')
                self.disconnect()
                return
        view_name = self.view.file_name()
        if not view_name:
            view_name = self.view.name()
        self.logger.info('Resyncing view %s with %s' % (view_name, self.sharingWithUser))
        self.toAck = []
        self.sendMessage(base.RESHARE_VIEW, payload=str(totalToSend))
        while begin < totalToSend:
            chunkToSend = self.view.substr(sublime.Region(begin, end))
            self.toAck.append(len(chunkToSend))
            self.sendMessage(base.VIEW_CHUNK, payload=chunkToSend)
            begin = begin + MAX_CHUNK_SIZE
            end = end + MAX_CHUNK_SIZE
            status_bar.progress_message("sending view to %s" % self.sharingWithUser, begin, totalToSend)
        self.sendMessage(base.END_OF_VIEW, payload=self.view.settings().get('syntax'))
        self.view.set_read_only(False)
        # send view position as it stands now so the partner view is positioned appropriately post-resync
        viewRegionLines = self.view.split_by_newlines(self.view.visible_region())
        lineIdx = len(viewRegionLines) / 2 - 1
        if lineIdx < 0:
            lineIdx = 0
        viewCenterRegion = viewRegionLines[lineIdx]
        self.sendViewPositionUpdate(viewCenterRegion)
        # start the view monitoring thread if not already running
        if not self.viewMonitorThread.is_alive():
            self.viewMonitorThread.start()


    def onStartCollab(self):
        """
        Callback method informing the peer that we have received the view.
        """
        self.logger.debug('collaboration session with view started!')
        registry.registerSessionByView(self.view, self)
        # self.notify(collab_event.RECVD_VIEW, self)


    def stopCollab(self):
        """
        Notify the connected peer that we are terminating the collaborating session.
        """
        if (self.peerType == base.CLIENT) and (self.view != None):
            self.view.set_read_only(False)
            self.view = None
        status_bar.status_message('stopped sharing with %s' % self.str())


    def onStopCollab(self):
        """
        Callback method informing the peer that we are terminating a collaborating session.
        """
        self.stopCollab()


    def swapRole(self):
        """
        Request a role swap with the connected peer.
        """
        if self.view is None:
            self.logger.warn('Request to swap role when no view is being shared!')
            return
        if self.role == base.HOST_ROLE:
            self.logger.debug('Stopping ViewMonitorThread until role swap is decided')
            self.viewMonitorThread.destroy()
            self.viewMonitorThread.join()
        self.sendMessage(base.SWAP_ROLE)


    def onSwapRole(self):
        """
        Callback method to respond to role swap requests from the connected peer.
        """
        if self.view is None:
            self.logger.warn('Request from %s to swap role when no view is being shared!' % self.str())
            return
        if self.role == base.HOST_ROLE:
            self.logger.debug('Stopping ViewMonitorThread until role swap is decided')
            self.viewMonitorThread.destroy()
            self.viewMonitorThread.join()
        message = None
        view_name = self.view.file_name()
        if not view_name or (len(view_name) == 0):
            view_name = self.view.name()
            if not view_name or (len(view_name) == 0):
                view_name = 'untitled'
        if self.role == base.HOST_ROLE:
            message = '%s sharing %s with you wants to host...' % (self.str(), view_name)
        else:
            message = '%s sharing %s with you wants you to host...' % (self.str(), view_name)
        swapping_roles = sublime.ok_cancel_dialog(message)

        if swapping_roles:
            if self.role == base.HOST_ROLE:
                self.role = base.PARTNER_ROLE
                self.view.set_read_only(True)
            else:
                self.role = base.HOST_ROLE
                self.view.set_read_only(False)
                self.viewMonitorThread = ViewMonitorThread(self)
                self.viewMonitorThread.start()
            self.sendMessage(base.SWAP_ROLE_ACK)
        else:
            self.sendMessage(base.SWAP_ROLE_NACK)
        self.logger.info('session %s with %s role now changed to %s' % (view_name, self.str(), self.role))
        # wait for the swap to complete on the client side... 0.5 second because the message is tiny
        time.sleep(0.5)


    def onSwapRoleAck(self):
        """
        Callback method to respond to accepted role swap response from the connected peer.
        The caller of swapRole() waits for this method before actually swapping roles on its side.
        """
        if self.role == base.HOST_ROLE:
            self.role = base.PARTNER_ROLE
            self.view.set_read_only(True)
        else:
            self.role = base.HOST_ROLE
            self.view.set_read_only(False)
            self.viewMonitorThread = ViewMonitorThread(self)
            self.viewMonitorThread.start()
        view_name = self.view.file_name()
        if not view_name or (len(view_name) == 0):
            view_name = self.view.name()
            if not view_name or (len(view_name) == 0):
                view_name = 'untitled'
        self.logger.info('session %s with %s role now changed to %s' % (view_name, self.str(), self.role))


    def onSwapRoleNAck(self):
        """
        Callback method to respond to rejected role swap response from the connected peer.
        The caller of swapRole() may have this called if the connected peer rejects a swap role request.
        """
        if self.role == base.HOST_ROLE:
            self.viewMonitorThread = ViewMonitorThread()
            self.viewMonitorThread.start()
        sublime.message_dialog('%s sharing %s did not want to swap roles' % (self.str(), self.view.file_name()))


    def sendViewPositionUpdate(self, centerOnRegion):
        """
        Send a window view position update to the peer so they know what
        we are looking at.

        @param centerOnRegion: C{sublime.Region} of the central-most line of the current visible portion of the view to send to the peer.
        """
        status_bar.heartbeat_message('sharing with %s' % self.str())
        self.sendMessage(base.POSITION, payload=str(centerOnRegion))


    def recvViewPositionUpdate(self, centerOnRegion):
        """
        Callback method for handling view position updates from the peer.

        @param centerOnRegion: C{sublime.Region} to set as the current center of the view.
        """
        self.view.show_at_center(centerOnRegion.begin())


    def sendSelectionUpdate(self, selectedRegions):
        """
        Send currently selected regions to the peer.

        @param selectedRegions: C{sublime.RegionSet} of all selected regions in the current view.
        """
        status_bar.heartbeat_message('sharing with %s' % self.str())
        self.sendMessage(base.SELECTION, payload=str(selectedRegions))


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
        self.logger.debug('sending edit: %s %s' %(base.numeric_to_symbolic[editType], content))
        if (editType == base.EDIT_TYPE_INSERT) \
            or (editType == base.EDIT_TYPE_INSERT_SNIPPET) \
            or (editType == base.EDIT_TYPE_PASTE):
            self.sendMessage(base.EDIT, editType, payload=content)
        else:
            self.sendMessage(base.EDIT, editType)


    def recvEdit(self, editType, content):
        """
        Callback method for handling edit events from the peer.

        @param editType: C{str} edit type (see above)
        @param content: C{Array} contents of the edit (None if delete editType)
        """
        self.view.set_read_only(False)
        if editType == base.EDIT_TYPE_INSERT:
            self.view.run_command('insert', { 'characters': content })
        elif editType == base.EDIT_TYPE_INSERT_SNIPPET:
            self.view.run_command('insert_snippet', { 'contents': content })
        elif editType == base.EDIT_TYPE_LEFT_DELETE:
            self.view.run_command('left_delete')
        elif editType == base.EDIT_TYPE_RIGHT_DELETE:
            self.view.run_command('right_delete')
        elif editType == base.EDIT_TYPE_CUT:
            # faux cut since we are recieving the commands instead of invoking them directly
            self.view.run_command('left_delete')
        elif editType == base.EDIT_TYPE_COPY:
            # we dont actually want to do anything here
            pass
        elif editType == base.EDIT_TYPE_PASTE:
            # faux cut since we are recieving the commands instead of invoking them directly
            # we actually have to handle this as a direct view.replace() call to avoid
            # autoindent which occurs if we use the view.run_command('insert', ...) call
            paste_edit = self.view.begin_edit()
            for region in self.view.sel():
                self.view.replace(paste_edit, region, content)
            self.view.end_edit(paste_edit)
        elif editType == base.EDIT_TYPE_UNDO:
            self.view.run_command('undo')
        elif editType == base.EDIT_TYPE_REDO:
            self.view.run_command('redo')
        elif editType == base.EDIT_TYPE_REDO_OR_REPEAT:
            self.view.run_command('redo_or_repeat')
        elif editType == base.EDIT_TYPE_SOFT_UNDO:
            self.view.run_command('soft_undo')
        elif editType == base.EDIT_TYPE_SOFT_REDO:
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
                self.logger.debug('Handling view change %s with size %d payload' % (base.numeric_to_symbolic[toDo[0]], len(toDo[1])))
                if (toDo[0] == base.SHARE_VIEW) or (toDo[0] == base.RESHARE_VIEW):
                    self.totalNewViewSize = 0
                    if toDo[0] == base.SHARE_VIEW:
                        self.view = sublime.active_window().new_file()
                        payloadBits = toDo[1].split('|')
                        if payloadBits[0] == 'NONAME':
                            self.view.set_name('SHARING-WITH-%s' % self.sharingWithUser)
                        else:
                            self.view.set_name(payloadBits[0])
                        self.totalNewViewSize = int(payloadBits[1])
                    else:
                        # resync event, purge the old view in preparation for the fresh content
                        self.logger.debug('resyncing view')
                        self.lastResyncdPosition = 0
                        self.totalNewViewSize = int(toDo[1])
                    self.view.set_read_only(True)
                    self.view.set_scratch(True)
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                elif toDo[0] == base.VIEW_CHUNK:
                    self.view.set_read_only(False)
                    self.viewPopulateEdit = self.view.begin_edit()
                    # if we are a resync chunk...
                    if hasattr(self, 'lastResyncdPosition'):
                        self.view.replace(self.viewPopulateEdit,  \
                            sublime.Region(self.lastResyncdPosition, self.lastResyncdPosition + len(toDo[1])), \
                            toDo[1])
                        self.lastResyncdPosition += len(toDo[1])
                    else:
                        self.view.insert(self.viewPopulateEdit, self.view.size(), toDo[1])
                    self.view.end_edit(self.viewPopulateEdit)
                    self.viewPopulateEdit = None
                    self.view.set_read_only(True)
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                elif toDo[0] == base.END_OF_VIEW:
                    self.view.set_syntax_file(toDo[1])
                    if hasattr(self, 'lastResyncdPosition'):
                        del self.lastResyncdPosition
                    status_bar.progress_message("receiving view from %s" % self.sharingWithUser, self.view.size(), self.totalNewViewSize)
                    # view is populated and configured, lets share!
                    self.onStartCollab()
                elif toDo[0] == base.SELECTION:
                    status_bar.heartbeat_message('sharing with %s' % self.str())
                    regions = []
                    for regionMatch in REGION_PATTERN.finditer(toDo[1]):
                        regions.append(sublime.Region(int(regionMatch.group(1)), int(regionMatch.group(2))))
                    self.recvSelectionUpdate(regions)
                elif toDo[0] == base.POSITION:
                    status_bar.heartbeat_message('sharing with %s' % self.str())
                    regionMatch = REGION_PATTERN.search(toDo[1])
                    if regionMatch:
                        self.recvViewPositionUpdate(sublime.Region(int(regionMatch.group(1)), int(regionMatch.group(2))))
            elif len(toDo) == 3:
                status_bar.heartbeat_message('sharing with %s' % self.str())
                # edit event
                assert toDo[0] == base.EDIT
                # make the shared selection the ACTUAL selection
                self.view.sel().clear()
                for region in self.view.get_regions(self.sharingWithUser):
                    self.view.sel().add(region)
                self.view.erase_regions(self.sharingWithUser)
                self.recvEdit(toDo[1], toDo[2])
        self.toDoToViewQueueLock.release()


    def checkViewSyncState(self, peerViewSize):
        """
        Compares a received view size with this sides' view size.... if they don't match a resync event is
        triggered.
        """
        if self.view.size() != peerViewSize:
            self.logger.info('view out of sync!')
            self.sendMessage(base.VIEW_RESYNC)


    def recvd_CONNECTED(self, messageSubType, payload):
        """
        Callback method for the connection confirmation handshake between
        client and server.
        """
        if self.peerType == base.CLIENT:
            if self.state == base.STATE_CONNECTING:
                self.state = base.STATE_CONNECTED
                self.logger.info('Connected to peer: %s' % self.sharingWithUser)
            else:
                self.logger.error('Received CONNECTED message from server-peer when in state %s' % self.state)
        else:
            ## server/initiator side of the wire...
            # client is connected, send ACK and set our state to be connected
            self.sendMessage(base.CONNECTED)
            self.state = base.STATE_CONNECTED
            self.logger.info('Connected to peer: %s' % self.sharingWithUser)
            self.notify(collab_event.ESTABLISHED_SESSION, self)


    def recvd_DISCONNECT(self, messageSubType=None, payload=''):
        self.onDisconnect()


    def recvd_SHARE_VIEW(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.SHARE_VIEW, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(base.SHARE_VIEW_ACK)
        self.handleViewChanges()


    def recvd_RESHARE_VIEW(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.RESHARE_VIEW, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(base.SHARE_VIEW_ACK)
        self.handleViewChanges()


    def recvd_SHARE_VIEW_ACK(self, messageSubType, payload):
        self.ackdChunks = []


    def recvd_VIEW_CHUNK(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.VIEW_CHUNK, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(base.VIEW_CHUNK_ACK, payload=str(len(payload)))
        self.handleViewChanges()


    def recvd_VIEW_CHUNK_ACK(self, messageSubType, payload):
        ackdChunkSize = int(payload)
        self.ackdChunks.append(ackdChunkSize)


    def recvd_END_OF_VIEW(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.END_OF_VIEW, payload))
        self.toDoToViewQueueLock.release()
        self.sendMessage(base.END_OF_VIEW_ACK)
        self.handleViewChanges()


    def recvd_END_OF_VIEW_ACK(self, messageSubType, payload):
        if self.toAck == self.ackdChunks:
            self.toAck = None
            self.ackdChunks = None
        else:
            self.logger.error('Sent %s chunks of data to peer but peer received %s chunks of data' % (self.toAck, self.ackdChunks))
            self.toAck = None
            self.ackdChunks = None
            self.sendMessage(base.BAD_VIEW_SEND)
            self.disconnect()


    def recvd_SELECTION(self, messageSubType, payload):
        # self.logger.debug('selection change: %s' % payload)
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.SELECTION, payload))
        self.toDoToViewQueueLock.release()
        self.handleViewChanges()


    def recvd_POSITION(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.POSITION, payload))
        self.toDoToViewQueueLock.release()
        self.handleViewChanges()


    def recvd_EDIT(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        self.toDoToViewQueue.append((base.EDIT, messageSubType, payload))
        self.toDoToViewQueueLock.release()
        self.handleViewChanges()


    def recvd_SWAP_ROLE(self, messageSubType, payload):
        self.onSwapRole()


    def recvd_SWAP_ROLE_ACK(self, messageSubType, payload):
        self.onSwapRoleAck()


    def recvd_SWAP_ROLE_NACK(self, messageSubType, payload):
        self.onSwapRoleNAck()


    def recvd_VIEW_SYNC(self, messageSubType, payload):
        self.toDoToViewQueueLock.acquire()
        # no pending edits... safe to check
        if len(self.toDoToViewQueue) == 0:
            self.checkViewSyncState(int(payload))
        self.toDoToViewQueueLock.release()


    def recvd_VIEW_RESYNC(self, messageSubType, payload):
        self.resyncCollab()


    def recvdUnknown(self, messageType, messageSubType, payload):
        self.logger.warn('Received unknown message: %s, %s, %s' % (messageType, messageSubType, payload))


    def stringReceived(self, data):
        magicNumber, msgTypeNum, msgSubTypeNum = struct.unpack(self.messageHeaderFmt, data[:self.messageHeaderSize])
        assert magicNumber == base.MAGIC_NUMBER
        msgType = base.numeric_to_symbolic[msgTypeNum]
        msgSubType = base.numeric_to_symbolic[msgSubTypeNum]
        payload = data[self.messageHeaderSize:]
        self.logger.debug('RECVD: %s-%s[%s]' % (msgType, msgSubType, payload))
        method = getattr(self, "recvd_%s" % msgType, None)
        if method is not None:
            method(msgSubTypeNum, payload)
        else:
            self.recvdUnknown(msgType, msgSubType, payload)


    def connectionLost(self, reason):
        registry.removeSession(self)
        if self.peerType == base.CLIENT:
            # ignore this, clientConnectionLost() below will also be called
            return
        self.state = base.STATE_DISCONNECTED
        if error.ConnectionDone == reason.type:
            self.disconnect()
        else:
            status_bar.heartbeat_message('lost share session with %s' % self.str())
            # may want to reconnect, but for now lets print why
            self.logger.error('Connection lost: %s - %s' % (reason.type, reason.value))


    #*** internet.base.BaseProtocol (via basic.Int32StringReceiver) method implementations ***#

    def connectionMade(self):
        if self.peerType == base.CLIENT:
            pass
        else:
            pass

    #*** protocol.Factory method implementations ***#

    def buildProtocol(self, addr):
        self.logger.debug('building protocol for %s' % self.peerType)
        if self.peerType == base.CLIENT:
            self.logger.debug('Connected to peer at %s:%d' % (self.host, self.port))
            self.sendMessage(base.CONNECTED)
        return self


    #*** protocol.ClientFactory method implementations ***#

    def clientConnectionLost(self, connector, reason):
        registry.removeSession(self)
        self.state = base.STATE_DISCONNECTED
        if error.ConnectionDone == reason.type:
            self.disconnect()
        else:
            status_bar.status_message('lost share session with %s' % self.str())
            # may want to reconnect, but for now lets print why
            self.logger.error('Connection lost: %s - %s' % (reason.type, reason.value))


    def clientConnectionFailed(self, connector, reason):
        self.logger.error('Connection failed: %s - %s' % (reason.type, reason.value))
        registry.removeSession(self)
        self.state = base.STATE_DISCONNECTED
        if (error.ConnectionRefusedError == reason.type) or (error.TCPTimedOutError == reason.type) or (error.TimeoutError == reason.type):
            if self.peerType == base.CLIENT:
                self.notify(collab_event.FAILED_SESSION, self.sharingWithUser)
        self.disconnect()


    #*** helper functions ***#

    def sendMessage(self, messageType, messageSubType=base.EDIT_TYPE_NA, payload=''):
        self.logger.debug('SEND: %s-%s[bytes: %d]' % (base.numeric_to_symbolic[messageType], base.numeric_to_symbolic[messageSubType], len(payload)))
        reactor.callFromThread(self.sendString, struct.pack(self.messageHeaderFmt, base.MAGIC_NUMBER, messageType, messageSubType) + payload.encode())
