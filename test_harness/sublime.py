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

# this is a collection of mock sublime api functions and classes
from StringIO import StringIO

class Region(object):

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def begin(self):
        return self.a

    def end(self):
        return self.b

    def size(self):
        return abs(self.b - self.a)

    def empty(self):
        return self.a == self.b

class View(object):

    def __init__(self):
        self.name = 'NONAME'
        self.readOnly = False
        self.scratch = False
        self.size = 0
        self.viewContents = StringIO()

    def load_faux_view(self, filepath):
        f = open(filepath, 'r')
        if len(self.viewContents.getvalue()) > 0:
            self.viewContents.close()
            self.viewContents = StringIO()
        self.viewContents.write(f.read())
        f.close()

    def set_name(self, name):
        self.name = name

    def set_read_only(self, readOnly):
        self.readOnly = readOnly

    def set_scratch(self, scratch):
        self.scratch = scratch

    def substr(self, region):
        return self.viewContents.getvalue()[region.begin():region.end()]

    def size(self):
        return self.size

    def begin_edit(self):
        mockEdit = open('/tmp/%s' % self.name, 'w+')
        return mockEdit

    def insert(self, edit, point, string):
        mockEdit.seek(point, 0)
        mockEdit.write(string)
        self.viewContents.write(string)
        self.size = self.size + len(string)

    def end_edit(self, edit):
        edit.flush()
        edit.close()

class Window(object):

    def new_file():
        return View()

def active_window():
    return Window()

