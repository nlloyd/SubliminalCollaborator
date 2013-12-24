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
from zope.interface import Interface


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


    def addAllObservers(self, observers):
        for observer in observers:
            if Observer.providedBy(observer):
                self.observers.add(observer)


    def removeObserver(self, observer):
        self.observers.discard(observer)


    def notify(self, event, producer, data=None):
        for observer in self.observers:
            observer.update(event, producer, data)
