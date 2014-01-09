# All of SubliminalCollaborator is licensed under the MIT license.

#   Copyright (c) 2013 Nick Lloyd

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

import sublime
import threading
import logging
import types


class Registry(object):

    logger = logging.getLogger('SubliminalCollaborator.registry')

    def __init__(self):
        # negotiator map, key is protocol:host:username, values are configured negotiator instances
        self.negotiators = {}
        # nested session map: negotiator key -> peer username -> set(session)
        self.sessionsByUserByNegotiator = {}
        # sessions by view id
        self.sessionsByViewId = {}


    def buildNegotiatorKey(self, protocol, config):
        return '%s|%s@%s:%d' % (protocol, config['username'], config['host'], config['port'])


    def addOrUpdateNegotiator(self, protocol, config, constructorsByProtocol):
        """
        Adds or updates in the global registry the negotiator configuration
        identified by the protocol and contents of the negotiator configuration.

        Negotiator registry keys are a string of the format:
        protocol|username@host:port

        The username, host, and port values are expected in the config dict.

        This will also initialize fresh negotiator instances, if they are new/updated.

        @return: tuple with the negotiator key of the new or modified configuration
                 and a boolean which is True if the client was updated, False if was new, 
                 None if nothing happened (not new but no changes requiring update).
        """
        errorMsgs = ['The following configuration errors were found:\n']
        if not 'username' in config:
            errorMsgs.append('  A configuration for protocol %s is missing a username!' % protocol)
            self.logger.warning(errorMsgs[-1])
        elif not 'host' in config:
            errorMsgs.append('  A configuration for protocol %s is missing a host!' % protocol)
            self.logger.warning(errorMsgs[-1])
        elif not 'port' in config:
            errorMsgs.append('  A configuration for protocol %s is missing a port!' % protocol)
            self.logger.warning(errorMsgs[-1])
        
        negotiatorKey = self.buildNegotiatorKey(protocol, config)

        updated = self.hasNegotiator(negotiatorKey)
        added = not updated
        # make sure the updated config data is actually different
        if updated:
            updated = (self.getNegotiator(negotiatorKey).getConfig() != config)

        if updated:
            self.logger.debug('updating configuration for ' + negotiatorKey)
        elif added:
            self.logger.debug('adding configuration for ' + negotiatorKey)
        else:
            self.logger.debug('unchanged configuration for ' + negotiatorKey)

        # create negotiator instance
        # if updated config, disconnect old negotiator and create new
        if updated:
            self.removeNegotiator(negotiatorKey)
        self.negotiators[negotiatorKey] = constructorsByProtocol[protocol](negotiatorKey, config)

        # report errors, if any
        if len(errorMsgs) > 1:
            sublime.error_message(errorMsgs.join('\n'))
        return (negotiatorKey, updated)


    def hasNegotiator(self, protocol, config):
        negotiatorKey = self.buildNegotiatorKey(protocol, config)
        return self.hasNegotiator(negotiatorKey)


    def hasNegotiator(self, negotiatorKey):
        return self.negotiators.has_key(negotiatorKey)


    def removeNegotiator(self, protocol, config):
        negotiatorKey = self.buildNegotiatorKey(protocol, config)
        self.removeNegotiator(negotiatorKey)


    def removeNegotiator(self, negotiatorKey):
        oldNegotiator = self.negotiators.pop(negotiatorKey)
        if oldNegotiator.isConnected():
            oldNegotiator.disconnect()


    def listNegotiatorKeys(self):
        return self.negotiators.keys()


    def listNegotiators(self):
        return self.negotiators.values();


    def listNegotiatorEntries(self):
        return self.negotiators.items()


    def iterNegotiators(self):
        return self.negotiators.itervalues()


    def iterNegotiatorEntries(self):
        return self.negotiators.iteritems()


    def getNegotiator(self, protocol, config):
        negotiatorKey = self.buildNegotiatorKey(protocol, config)
        return self.getNegotiator(negotiatorKey)


    def getNegotiator(self, negotiatorKey):
        return self.negotiators[negotiatorKey]


    def registerSession(self, session):
        negotiatorKey = session.getParentNegotiatorKey()
        peerUser = session.sharingWithUser
        if negotiatorKey in self.sessionsByUserByNegotiator:
            if peerUser in self.sessionsByUserByNegotiator[negotiatorKey]:
                existingSessions = self.sessionsByUserByNegotiator[negotiatorKey][peerUser]
                if session in existingSessions:
                    if hasattr(session, 'view') and session.view:
                        self.logger.warn('already collaborating on %s with %s' % (session.view.file_name(), peerUser))
                    else:
                        self.logger.debug('attempt to register already existing session with %s but without a set view' % peerUser)
                else:
                    existingSessions.add(session)
            else:
                self.sessionsByUserByNegotiator[negotiatorKey] = {peerUser: set([session])}
        else:
            self.sessionsByUserByNegotiator[negotiatorKey] = {peerUser: set([session])}


    def registerSessionByView(self, view, session):
        if view.id() in self.sessionsByViewId:
            self.logger.warn('already sharing view %s with %s' % (view.file_name(), session.str()))
        else:
            self.sessionsByViewId[view.id()] = session


    def hasSession(self, negotiatorKey, peerUser):
        return negotiatorKey in self.sessionsByUserByNegotiator and peerUser in self.sessionsByUserByNegotiator[negotiatorKey]


    def getSessionsByNegotiatorAndPeer(self, negotiatorKey, peerUser):
        sessions = None
        if negotiatorKey in self.sessionsByUserByNegotiator:
            sessions = self.sessionsByUserByNegotiator[negotiatorKey].get(peerUser)
        return sessions


    def getSessionByView(self, view):
        return self.sessionsByViewId.get(view.id())


    def listSessions(self):
        sessions = []
        for sessionsByUser in self.sessionsByUserByNegotiator.itervalues():
            for userSessions in sessionsByUser.itervalues():
                sessions += userSessions
        return sessions


    def removeSession(self, session):
        """
        Remove a session from both session registries.
        """
        negotiatorKey = session.getParentNegotiatorKey()
        peerUser = session.sharingWithUser
        if negotiatorKey in self.sessionsByUserByNegotiator:
            sessionsByUser = self.sessionsByUserByNegotiator[negotiatorKey]
            if peerUser in sessionsByUser:
                sessionsByUser[peerUser].discard(session)
        if session in self.sessionsByViewId.values():
            for viewId, registeredSession in self.sessionsByViewId.items():
                if session == registeredSession:
                    self.sessionsByViewId.pop(viewId, None)


##################################################


# borrowing sys.modules global access approach used by the twisted reactor implementation, albeit a different implementation
import sys
import sub_collab

if 'sub_collab.registry' not in sys.modules or isinstance(sys.modules['sub_collab.registry'], types.ModuleType):
    Registry.logger.debug('setting up negotiator and session registry')
    registry = Registry()
    sub_collab.registry = registry
    sys.modules['sub_collab.registry'] = registry
