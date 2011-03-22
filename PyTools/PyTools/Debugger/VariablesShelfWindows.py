# -*- coding: utf-8 -*-
# Name: VariablesShelfWindows.py
# Purpose: Debugger plugin
# Author: Mike Rans
# Copyright: (c) 2010 Mike Rans
# License: wxWindows License
###############################################################################

"""Editra Shelf display window"""

__author__ = "Mike Rans"
__svnid__ = "$Id $"
__revision__ = "$Revision $"

#-----------------------------------------------------------------------------#
# Imports
import threading
import wx

# Editra Libraries
import util
import eclib
import ed_msg

# Local imports
from PyTools.Common.PyToolsUtils import PyToolsUtils
from PyTools.Common.PyToolsUtils import RunProcInThread
from PyTools.Common.BaseShelfWindow import BaseShelfWindow
from PyTools.Debugger.VariablesLists import VariablesList
from PyTools.Debugger import RPDBDEBUGGER

# Globals
_ = wx.GetTranslation

#-----------------------------------------------------------------------------#

class BaseVariablesShelfWindow(BaseShelfWindow):
    def __init__(self, parent, listtype, filterlevel, buttontitle="Unused", taskfn=None):
        """Initialize the window"""
        super(BaseVariablesShelfWindow, self).__init__(parent)
        self.listtype = listtype
        ctrlbar = self.setup(VariablesList(self, listtype, filterlevel))
        ctrlbar.AddStretchSpacer()
        self.layout(buttontitle, taskfn)
        
        # attributes
        self.filterlevel = filterlevel
        self.key = None

    def UpdateVariablesList(self, variables):
        if not variables:
            return
        self._listCtrl.Clear()
        self._listCtrl.PopulateRows(variables)
        self._listCtrl.Refresh()

    def update_namespace(self, key, expressionlist):
        old_key = self.key
        old_expressionlist = self._listCtrl.get_expression_list()

        if key == old_key:
            expressionlist = old_expressionlist

        self.key = key

        if expressionlist is None:
            expressionlist = [(self.listtype, True)]

        worker = RunProcInThread(self.listtype, self.UpdateVariablesList, \
            RPDBDEBUGGER.get_namespace, expressionlist, self.filterlevel)
        worker.start()
        return (old_key, old_expressionlist)
        
class LocalVariablesShelfWindow(BaseVariablesShelfWindow):
    def __init__(self, parent):
        """Initialize the window"""
        super(LocalVariablesShelfWindow, self).__init__(parent, u"locals()", 0)

        # Attributes
        RPDBDEBUGGER.clearlocalvariables = self._listCtrl.Clear
        RPDBDEBUGGER.updatelocalvariables = self.update_namespace
        
        RPDBDEBUGGER.update_namespace()

    def Unsubscription(self):
        RPDBDEBUGGER.clearlocalvariables = lambda:None
        RPDBDEBUGGER.updatelocalvariables = lambda x,y:(None,None)
        
class GlobalVariablesShelfWindow(BaseVariablesShelfWindow):
    def __init__(self, parent):
        """Initialize the window"""
        super(GlobalVariablesShelfWindow, self).__init__(parent, u"globals()", 0)

        # Attributes
        RPDBDEBUGGER.clearglobalvariables = self._listCtrl.Clear
        RPDBDEBUGGER.updateglobalvariables = self.update_namespace
        
        RPDBDEBUGGER.update_namespace()
        
    def Unsubscription(self):
        RPDBDEBUGGER.clearglobalvariables = lambda:None
        RPDBDEBUGGER.updateglobalvariables = lambda x,y:(None,None)
        
class ExceptionsShelfWindow(BaseVariablesShelfWindow):
    ANALYZELBL = "Analyze Exception"
    STOPANALYZELBL = "Stop Analysis"

    def __init__(self, parent):
        """Initialize the window"""
        super(ExceptionsShelfWindow, self).__init__(parent, u"rpdb_exception_info", 0, self.ANALYZELBL, self.OnAnalyze)

        # Attributes
        RPDBDEBUGGER.clearexceptions = self._listCtrl.Clear
        RPDBDEBUGGER.updateexceptions = self.update_namespace
        RPDBDEBUGGER.catchunhandledexception = self.UnhandledException
        RPDBDEBUGGER.updateanalyze = self.UpdateAnalyze

        RPDBDEBUGGER.update_namespace()
        
    def Unsubscription(self):
        RPDBDEBUGGER.clearexceptions = lambda:None
        RPDBDEBUGGER.updateexceptions = lambda x,y:(None,None)
        RPDBDEBUGGER.unhandledexception = False
        RPDBDEBUGGER.catchunhandledexception = lambda:None
        RPDBDEBUGGER.updateanalyze = lambda:None
        
    def UnhandledException(self):
        RPDBDEBUGGER.unhandledexception = True
        wx.CallAfter(self._unhandledexception)
        
    def _unhandledexception(self):        
        dlg = wx.MessageDialog(self, "An unhandled exception was caught. Would you like to analyze it?",\
        "Warning", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        res = dlg.ShowModal()
        dlg.Destroy()

        if res != wx.ID_YES:
            RPDBDEBUGGER.unhandledexception = False
            RPDBDEBUGGER.do_go()
            return

        RPDBDEBUGGER.set_analyze(True)
        
    def OnAnalyze(self, event):
        if self.taskbtn.GetLabel() == self.ANALYZELBL:
            RPDBDEBUGGER.set_analyze(True)
        else:
            RPDBDEBUGGER.set_analyze(False)

    def UpdateAnalyze(self):
        if RPDBDEBUGGER.analyzing:
            self.taskbtn.SetLabel(self.STOPANALYZELBL)
        else:
            self.taskbtn.SetLabel(self.ANALYZELBL)
