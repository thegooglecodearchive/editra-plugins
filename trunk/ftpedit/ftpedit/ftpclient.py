###############################################################################
# Name: ftpclient.py                                                          #
# Purpose: Ftp client for managing connections, downloads, uploads.           #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""Ftp Client

Ftp client class for managing connections, uploads, and downloads.

"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id$"
__revision__ = "$Revision$"

#-----------------------------------------------------------------------------#
# Imports
import threading
import re
import ftplib
import socket
import wx

# Editra Libraries
from eclib.infodlg import CalcSize
from util import Log

#-----------------------------------------------------------------------------#

# Event that ftp LIST command has completed value == dict of updates
edEVT_FTP_REFRESH = wx.NewEventType()
EVT_FTP_REFRESH = wx.PyEventBinder(edEVT_FTP_REFRESH, 1)

class FtpClientEvent(wx.PyCommandEvent):
    """Event for data transfer and signaling actions in the L{OutputBuffer}"""
    def __init__(self, etype, value=''):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype)
        self._value = value

    def GetValue(self):
        """Returns the value from the event.
        @return: the value of this event

        """
        return self._value

#-----------------------------------------------------------------------------#

class FtpClient(ftplib.FTP):
    """Ftp Client"""
    def __init__(self, parent, host=u'', port=21):
        """Create an ftp client object
        @param parent: owner window
        @keyword host: host name/ip
        @keyword port: port number

        """
        ftplib.FTP.__init__(self, host)

        # Attributes
        self._parent = parent   # Owner window
        self._default = u'.'    # Default path
        self._host = host       # Host name
        self._port = port       # Port number
        self._active = False    # Connected?
        self._data = list()     # recieved data
        self._lasterr = None    # Last error
        self._mutex = threading.Lock()
        self._busy = threading.Condition(self._mutex)

        # Setup
        self.set_pasv(True) # Use passive mode for now (configurable later)

    def ClearLastError(self):
        """Clear the last know error"""
        del self._lasterr
        self._lasterr = None

    def Connect(self, user, password):
        """Connect to the site
        @param user: username
        @param password: password

        """
        try:
            self.connect(self._host, self._port)
            self.login(user, password)
            self.cwd(self._default)
        except socket.error, msg:
            Log("[ftpedit][err] Connect: %s" % msg)
            self._lasterr = msg
            return False
        else:
            self._active = True

        return True

    def Disconnect(self):
        """Disconnect from the site"""
        try:
            if self._active:
                self.abort()
            self.quit()
            self._active = False
        except Exception, msg:
            self._lasterr = msg
            Log("[ftpedit][err] Disconnect: %s" % msg)

    def GetFileList(self, path):
        """Get list of files at the given path
        @return: list of dict(isdir, name, size, date)

        """
        try:
            code = self.retrlines('LIST', self.ProcessInput)
        except Exception, msg:
            Log("[ftpedit][err] GetFileList: %s" % msg)
            self._lasterr = msg

        # Critical section
        self._busy.acquire()
        rval = list(self._data)
        del self._data
        self._data = list()
        self._busy.release()
        return rval

    def GetLastError(self):
        """Get the last error that occured
        @return: Exception

        """
        return self._lasterr

    def IsActive(self):
        """Does the client have an active connection
        @return: bool

        """
        return self._active

    def MkDir(self, dname):
        """Make a new directory at the current path
        @param dname: string

        """
        raise NotImplementedError

    def ProcessInput(self, data):
        """Process incoming data
        @param data: string

        """
        processed = ParseFtpOutput(data)
        self._busy.acquire()
        self._data.append(processed)
        self._busy.release()

    def RefreshPath(self, path):
        """Refresh the path. Runs L{GetFileList} asyncronously and
        returns the results in a EVT_FTP_REFRESH event.

        """
        t = FtpThread(self._parent, self.GetFileList,
                      edEVT_FTP_REFRESH, args=[path,])
        t.start()

    def SetDefaultPath(self, dpath):
        """Set the default path
        @param dpath: string

        """
        self._default = dpath

    def SetHostname(self, hostname):
        """Set the host name
        @param hostname: string

        """
        self._host = hostname

    def SetPort(self, port):
        """Set the port to connect to
        @param port: port number (int)

        """
        self._port = port

#-----------------------------------------------------------------------------#

class FtpThread(threading.Thread):
    """Thread for running asyncronous ftp jobs"""
    def __init__(self, parent, funct, etype, args=list()):
        """Create the thread object
        @param parent: Parent window to recieve event(s)
        @param funct: method to run in the thread
        @param etype: event type
        @keyword args: list of args to pass to funct

        """
        threading.Thread.__init__(self)

        # Attributes
        self._parent = parent
        self._funct = funct
        self._etype = etype
        self._args = args

    def run(self):
        """Run the command"""
        result = self._funct(*self._args)
        evt = FtpClientEvent(self._etype, result)
        wx.PostEvent(self._parent, evt)

#-----------------------------------------------------------------------------#
# Utility
def ParseFtpOutput(line):
    """parse output from the ftp command
    @param line: line from ftp list.
    @return: dict(isdir, size, modified, fname)

    """
    rval = dict()
    parts = line.split(None, 9)
    state = 0
    dstring = u''
    for part in parts:
        # Permissions / type
        if state == 0:
            rval['isdir'] = part.startswith('d')
            state += 1
            continue

        # Size
        elif state == 4 and part.isdigit():
            val = int(part.strip())
            rval['size'] = CalcSize(val)
            state += 1

        # Last modified
        elif state >= 5 and state < 8:
            dstring = dstring + u" " + part
            if state == 7:
                rval['date'] = dstring.strip()
            state += 1

        # Filename
        elif state == 8:
            rval['name'] = part
            break

        else:
            state += 1

    return rval