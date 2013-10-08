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
from sub_collab.negotiator import irc


class Registry:

    logger = logging.getLogger('SubliminalCollaborator.registry')

    # map of protocol name to negotiator constructor
    negotiatorConstructorMap = {
        'irc': irc.IRCNegotiator
    }


    def __init__(self):
        # negotiator map, key is protocol:host:username, values are configured negotiator instances
        self.negotiators = {}
        # nested session map: negotiator key -> peer username -> set(session)
        self.sessionsByUserByNegotiator = {}
        # sessions by view id
        self.sessionsByViewId = {}
        self.sessionsLock = threading.Lock()


    def buildNegotiatorKey(self, protocol, config):
        return '%s|%s@%s:%d' % (protocol, config['username'], config['host'], config['port'])


    def addOrUpdateNegotiator(self, protocol, config):
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
        if not config.has_key('username'):
            errorMsgs.append('  A configuration for protocol %s is missing a username!' % protocol)
            self.logger.warning(errorMsgs[-1])
        elif not config.has_key('host'):
            errorMsgs.append('  A configuration for protocol %s is missing a host!' % protocol)
            self.logger.warning(errorMsgs[-1])
        elif not config.has_key('port'):
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
        self.negotiators[negotiatorKey] = self.negotiatorConstructorMap[protocol](negotiatorKey, config)

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


    def listNegoriatorEntries(self):
        return self.negotiators.items()


    def getNegotiator(self, protocol, config):
        negotiatorKey = self.buildNegotiatorKey(protocol, config)
        return self.getNegotiator(negotiatorKey)


    def getNegotiator(self, negotiatorKey):
        return self.negotiators[negotiatorKey]


    def registerSessionByNegotiatorAndPeer(self, negotiatorKey, peerUser, session):
        if self.sessionsByUserByNegotiator.has_key(negotiatorKey):
            if self.sessionsByUserByNegotiator[negotiatorKey].has_key[peerUser]:
                session = self.sessionsByUserByNegotiator[negotiatorKey][peerUser]
                if session.view:
                    logger.warn('already collaborating on %s with %s' % (session.view.file_name(), peerUser))
                else:
                    logger.debug('attempt to register already existing session with %s but without a set view' % peerUser)
            else:
                self.sessionsByUserByNegotiator[negotiatorKey][peerUser] = set([session])
        else:
            self.sessionsByUserByNegotiator[negotiatorKey][peerUser].add(session)


    def registerSessionByViewId(self, view, session):
        if self.sessionsByViewId.has_key(view.id()):
            logger.warn('already sharing view %s with %s' % (view.file_name(), session.str()))
        else:
            self.sessionsByViewId[view.id()] = session


    def hasSession(self, negotiatorKey, peerUser):
        return self.sessionsByUserByNegotiator.has_key(negotiatorKey) and self.sessionsByUserByNegotiator[negotiatorKey].has_key(peerUser)


##################################################


# borrowing sys.modules global access approach used by the twisted reactor implementation, albeit a different implementation
import sys
import sub_collab

if 'sub_collab.registry' not in sys.modules or isinstance(sys.modules['sub_collab.registry'], types.ModuleType):
    Registry.logger.debug('setting up negotiator and session registry')
    registry = Registry()
    sub_collab.registry = registry
    sys.modules['sub_collab.registry'] = registry
