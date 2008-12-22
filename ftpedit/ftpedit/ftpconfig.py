###############################################################################
# Name: ftpconfig.py                                                          #
# Purpose: Ftp Configuration Window.                                          #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""Ftp Configuration Window"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id$"
__revision__ = "$Revision$"

#-----------------------------------------------------------------------------#
# Imports
import wx

# Editra Libraries
import ed_glob

#-----------------------------------------------------------------------------#
# Globals

_ = wx.GetTranslation
#-----------------------------------------------------------------------------#

class FtpConfigDialog(wx.Dialog):
    def __init__(self, parent, title=u''):
        wx.Dialog.__init__(self, parent, title=title)

        # Attributes
        self._panel = FtpConfigPanel(self)

        # Layout
        self.__DoLayout()

        # Event Handlers
        

    def __DoLayout(self):
        """Layout the Dialog"""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

#-----------------------------------------------------------------------------#

class FtpConfigPanel(wx.Panel):
    """Main Configuration Panel"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # Attributes
        self._sites = FtpSitesPanel(self)

        # Layout
        self.__DoLayout()

        # Event Handlers
        

    def __DoLayout(self):
        """Layout the Dialog"""
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Sites
        sizer.Add(self._sites, 1, wx.EXPAND)

        # Final layout
        self.SetSizer(sizer)
        self.SetAutoLayout(True)

#-----------------------------------------------------------------------------#

class FtpSitesTree(wx.TreeCtrl):
    """Listing of saved sites"""
    def __init__(self, parent):
        """create the tree"""
        wx.TreeCtrl.__init__(self, parent,
                             style=wx.TR_FULL_ROW_HIGHLIGHT|\
                                   wx.TR_EDIT_LABELS|\
                                   wx.TR_SINGLE)

        # Attributes
        self._imglst = wx.ImageList(16, 16)
        self._imgidx = dict(folder=0, site=1)
        self._root = None # TreeItemId

        # Setup
        self.SetImageList(self._imglst)
        self.__SetupImageList()
        self._root = self.AddRoot(_("My Sites"), self._imgidx['folder'])

        # Event Handlers
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndLabelEdit)

    def __SetupImageList(self):
        """Setup the image list"""
        bmp = wx.ArtProvider.GetBitmap(str(ed_glob.ID_FOLDER), wx.ART_MENU)
        self._imgidx['folder'] = self._imglst.Add(bmp)

        bmp = wx.ArtProvider.GetBitmap(str(ed_glob.ID_WEB), wx.ART_MENU)
        self._imgidx['site'] = self._imglst.Add(bmp)

    def OnBeginLabelEdit(self, evt):
        """Handle updating after a tree label has been edited"""
        pass

    def OnEndLabelEdit(self, evt):
        """Handle updating after a tree label has been edited"""
        pass

#-----------------------------------------------------------------------------#

class FtpSitesPanel(wx.Panel):
    """Sites Panel"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        # Attributes
        self._tree = FtpSitesTree(self)

        # Layout
        self.__DoLayout()

        # Event Handlers
        

    def __DoLayout(self):
        """Layout the Dialog"""
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl = wx.StaticText(self, label=_("Sites:"))
        lsizer = wx.BoxSizer(wx.HORIZONTAL)
        lsizer.AddMany([((3, 3), 0), (lbl, 0)])
        sizer.AddMany([((5, 5), 0),
                       (lsizer, 0, wx.ALIGN_LEFT),
                       ((5, 5), 0),
                       (self._tree, 1, wx.EXPAND|wx.ALIGN_LEFT)])

        # Buttons
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        newbtn = wx.Button(self, wx.ID_NEW, _("New Site"))
        delbtn = wx.Button(self, wx.ID_DELETE, _("Delete"))
        hsizer.AddMany([(newbtn, 0, wx.ALIGN_CENTER_VERTICAL),
                        ((5, 5), 0),
                        (delbtn, 0, wx.ALIGN_CENTER_VERTICAL)])

        sizer.AddMany([((5, 5), 0), (hsizer, 0, wx.EXPAND), ((5, 5), 0)])

        msizer = wx.BoxSizer(wx.HORIZONTAL)
        msizer.AddMany([((5, 5), 0), (sizer, 1, wx.EXPAND), ((5, 5), 0)])
        self.SetSizer(msizer)
        self.SetAutoLayout(True)

#-----------------------------------------------------------------------------#
