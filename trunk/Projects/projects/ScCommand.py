###############################################################################
# Name: ScCommand.py                                                          #
# Purpose: Enumerate modified, added, deleted files in a list                 #
# Author: Kevin D. Smith <Kevin.Smith@sixquickrun.com>                        #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""
Source Control Commands

@author: Cody Precord <cprecord@editra.org>
@author: Kevin D. Smith <Kevin.Smith@sixquickrun.com>

"""

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__svnid__ = "$Id$"
__revision__ = "$Revision$"

#--------------------------------------------------------------------------#
# Imports
import wx
import os
import shutil
import threading
import subprocess
import tempfile

# Local Imports
from ConfigDialog import ConfigData
import diffwin

#--------------------------------------------------------------------------#
# Globals

# Error Codes
SC_ERROR_NONE = 0
SC_ERROR_RETRIEVAL_FAIL = 1

#--------------------------------------------------------------------------#
# Event Types

# Source Control Command has finished
ppEVT_CMD_COMPLETE = wx.NewEventType()
EVT_CMD_COMPLETE = wx.PyEventBinder(ppEVT_CMD_COMPLETE, 1)

# A diff job has completed
ppEVT_DIFF_COMPLETE = wx.NewEventType()
EVT_DIFF_COMPLETE = wx.PyEventBinder(ppEVT_DIFF_COMPLETE, 1)

# A status job event
ppEVT_STATUS = wx.NewEventType()
EVT_STATUS = wx.PyEventBinder(ppEVT_STATUS, 1)

class SourceControlEvent(wx.PyCommandEvent):
    """Base event to signal source controller events"""
    def __init__(self, etype, eid, value=None, err=SC_ERROR_NONE):
        wx.PyCommandEvent.__init__(self, etype, eid)

        # Attributes
        self._value = value
        self._err = err

    def GetError(self):
        """Get the error status code"""
        return self._err

    def GetValue(self):
        """Get the events value"""
        return self._value

    def SetError(self, err):
        """Set the error status"""
        self._err = err

    def SetValue(self, val):
        """Set the events value"""
        self._value = val

#--------------------------------------------------------------------------#

class ScCommandThread(threading.Thread):
    """Run a task in its own thread."""
    def __init__(self, parent, task, etype, args=(), kwargs=dict()):
        """Initialize the ScCommandThread. All *args and **kwargs are passed
        to the task.

        @param parent: Parent Window/EventHandler to recieve the events
                       generated by the process.
        @param task: callable to run. must return tuple (rval, errmsg)
        @param etype: callback event type to post

        """
        threading.Thread.__init__(self)

        # Attributes
        self.cancel = False         # Abort task
        self._parent = parent       # Parent Window/Event Handler
        self._pid = parent.GetId()  # Parent ID
        self.task = task            # Task method to run
        self.etype = etype
        self._args = args
        self._kwargs = kwargs

    def run(self):
        """Start running the task"""
        value, err = self.task(*self._args, **self._kwargs)

        # Post Results back to parent window
        evt = SourceControlEvent(self.etype, self._pid, value, err)
        wx.PostEvent(self._parent, evt)

#--------------------------------------------------------------------------#

class SourceController(object):
    """Source control command controller"""
    def __init__(self, owner):
        """Create the SourceController
        @param owner: Owner window

        """
        object.__init__(self)

        # Attributes
        self._parent = owner
        self._pid = self._parent.GetId()
        self.config = ConfigData() # Singleton config data instance
        self.tempdir = None
        self.scThreads = {}

        # Number of seconds to allow a source control command to run
        # before timing out
        self.scTimeout = 60

    def __del__(self):
        # Clean up tempdir
        if self.tempdir:
            shutil.rmtree(self.tempdir, ignore_errors=True)
        diffwin.CleanupTempFiles()

        # Stop any currently running source control threads
        for t in self.scThreads:
            t._Thread__stop()

    def _TimeoutCommand(self, callback, *args, **kwargs):
        """ Run command, but kill it if it takes longer than `timeout` secs
        @param callback: callable to call with results from command

        """
        result = []
        def resultWrapper(result, *args, **kwargs):
            """ Function to catch output of threaded method """
            args = list(args)
            method = args.pop(0)
            result.append(method(*args, **kwargs))

        # Insert result object to catch output
        args = list(args)
        args.insert(0, result)

        # Start thread
        t = threading.Thread(target=resultWrapper, args=args, kwargs=kwargs)
        t.start()
        self.scThreads[t] = True
        t.join(self.scTimeout)
        del self.scThreads[t]

        if t.isAlive():
            t._Thread__stop()
            return False

        if callback is not None:
            callback(result[0])

        return True

    def CompareRevisions(self, path, rev1=None, date1=None, rev2=None, date2=None):
        """
        Compare the playpen path to a specific revision, or compare two
        revisions

        Required Arguments:
        path -- absolute path of file to compare

        Keyword Arguments:
        rev1/date1 -- first file revision/date to compare against
        rev2/date2 -- second file revision/date to campare against

        """
        djob = ScCommandThread(self._parent, self.Diff, ppEVT_DIFF_COMPLETE,
                               args=(path, rev1, date1, rev2, date2))
        djob.setDaemon(True)
        djob.start()

    def Diff(self, path, rev1, date1, rev2, date2):
        """ Do the actual diff of two files by sending the files
        to be compared to the appropriate diff program.

        @return: tuple (None, err_code)

        """
        # Only do files
        if os.path.isdir(path):
            for fname in os.listdir(path):
                self.CompareRevisions(fname, rev1=rev1, date1=date1,
                                             rev2=rev2, date2=date2)
            return

        # Check if path is under source control
        sc = self.GetSCSystem(path)
        if sc is None:
            return None

        content1 = content2 = ext1 = ext2 = None

        # Grab the first specified revision
        if rev1 or date1:
            content1 = sc['instance'].fetch([path], rev=rev1, date=date1)
            if content1 and content1[0] is None:
                return None, SC_ERROR_RETRIEVAL_FAIL
            else:
                content1 = content1[0]
                if rev1:
                    ext1 = rev1
                elif date1:
                    ext1 = date1

        # Grab the second specified revision
        if rev2 or date2:
            content2 = sc['instance'].fetch([path], rev=rev2, date=date2)
            if content2 and content2[0] is None:
                return None, SC_ERROR_RETRIEVAL_FAIL
            else:
                content2 = content2[0]
                if rev2:
                    ext2 = rev2
                elif date2:
                    ext2 = date2

        if not (rev1 or date1 or rev2 or date2):
            content1 = sc['instance'].fetch([path])
            if content1 and content1[0] is None:
                return None, SC_ERROR_RETRIEVAL_FAIL
            else:
                content1 = content1[0]
                ext1 = 'previous'

        if not self.tempdir:
            self.tempdir = tempfile.mkdtemp()

        # Write temporary files
        path1 = path2 = None
        if content1 and content2:
            path = os.path.join(self.tempdir, os.path.basename(path))
            path1 = '%s.%s' % (path, ext1)
            path2 = '%s.%s' % (path, ext2)
            tfile = open(path1, 'w')
            tfile.write(content1)
            tfile.close()
            tfile2 = open(path2, 'w')
            tfile2.write(content2)
            tfile2.close()
        elif content1:
            path1 = path
            path = os.path.join(self.tempdir, os.path.basename(path))
            path2 = '%s.%s' % (path, ext1)
            tfile = open(path2, 'w')
            tfile.write(content1)
            tfile.close()
        elif content2:
            path1 = path
            path = os.path.join(self.tempdir, os.path.basename(path))
            path2 = '%s.%s' % (path, ext2)
            tfile2 = open(path2, 'w')
            tfile2.write(content2)
            tfile2.close()

        # Run comparison program
        if self.config.getBuiltinDiff() or not self.config.getDiffProgram():
            diffwin.GenerateDiff(path2, path1, html=True)
        elif isinstance(path2, basestring) and isinstance(path2, basestring):
            subprocess.call([self.config.getDiffProgram(), path2, path1])
        else:
            return (None, SC_ERROR_RETRIEVAL_FAIL)

        return (None, SC_ERROR_NONE)

    def GetSCSystem(self, path):
        """ Determine source control system being used on path if any
        @todo: possibly cache paths that are found to be under source control
               and the systems the belong to in order to improve performance

        """
        for key, value in self.config.getSCSystems().items():
            if value['instance'].isControlled(path):
                return value

    def IsSingleRepository(self, paths):
        """
        Are all paths from the same repository ?

        Required Arguments:
        nodes -- list of paths to test

        Returns: boolean indicating if all nodes are in the same repository
            (True), or if they are not (False).

        """
        previous = ''
        for path in paths:
            try:
                reppath = self.GetSCSystem(path)['instance'].getRepository(path)
            except:
                continue

            if not previous:
                previous = reppath
            elif previous != reppath:
                return False
        return True

    def ScCommand(self, nodes, command, callback=None, **options):
        """
        Run a source control command

        Required Arguments:
        nodes -- selected tree nodes [(treeitem, dict(path='', watcher=thread)]
        command -- name of command type to run

        """
        cjob = ScCommandThread(self._parent, self.RunScCommand,
                               ppEVT_CMD_COMPLETE,
                               args=(nodes, command, callback),
                               kwargs=options)
        cjob.setDaemon(True)
        cjob.start()

    def RunScCommand(self, nodes, command, callback, **options):
        """Does the running of the command
        @param nodes: list [(node, data), (node2, data2), ...]
        @param command: command string
        @return: (command, None)

        """
        concurrentcmds = ['status', 'history']
        NODE, DATA, SC = 0, 1, 2
        nodeinfo = []
        sc = None
        for node, data in nodes:
            # node, data, sc
            info = [node, data, None]

            # See if the node already has an operation running
            i = 0
            while data.get('sclock', None):
                time.sleep(1)
                i += 1
                if i > self.scTimeout:
                    return (None, None)

            # See if the node has a path associated
            # Technically, all nodes should (except the root node)
            if 'path' not in data:
                continue

            # Determine source control system
            sc = self.GetSCSystem(data['path'])
            if sc is None:
                if os.path.isdir(data['path']) or command == 'add':
                    sc = self.GetSCSystem(os.path.dirname(data['path']))
                    if sc is None:
                        continue
                else:
                    continue

            info[SC] = sc

            nodeinfo.append(info)

        # Check if the sc was found
        if sc is None:
            return (None, None)

        # Lock node while command is running
        if command not in concurrentcmds:
            for node, data, sc in nodeinfo:
                data['sclock'] = command

        rc = True
        try:
            # Find correct method
            method = getattr(sc['instance'], command, None)
            if method:
                # Run command (only if it isn't the status command)
                if command != 'status':
                    rc = self._TimeoutCommand(callback, method,
                                              [x[DATA]['path'] for x in nodeinfo],
                                              **options)
        finally:
            # Only update status if last command didn't time out
            if command not in ['history', 'revert', 'update'] and rc:
                for node, data, sc in nodeinfo:
                    self.StatusWithTimeout(sc, node, data)

            # Unlock
            if command not in concurrentcmds:
                for node, data, sc in nodeinfo:
                    del data['sclock']

        return (command, None)

    def StatusWithTimeout(self, sc, node, data, recursive=False):
        """Run a SourceControl status command with a timeout
        @param sc: SourceControll instance
        @param node: tree node, data
        @param data: data dict(path='')

        """
        status = {}
        try:
            rval = self._TimeoutCommand(None, sc['instance'].status,
                                        [data['path']],
                                        recursive=recursive,
                                        status=status)
        except Exception, msg:
            print "ERROR:", msg

        evt = SourceControlEvent(ppEVT_STATUS, self._pid,
                                 (node, data, status, sc))
        wx.PostEvent(self._parent, evt)
