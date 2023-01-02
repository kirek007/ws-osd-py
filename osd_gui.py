from enum import Enum
import logging
import wx
from processor import OSDFile, OsdFont, OsdPreview, VideoFile

from settings import appState
from pubsub import pub

class PubSubEvents(str, Enum):
    FileSelected = "FileDrop"
    ConfigUpdate = "ConfigUpdate"
    ApplicationConfigured = "ApplicationConfigured"
    PreviewUpdate = "PreviewUpdate"
    


class FilesDropTarget(wx.FileDropTarget):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, window):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window

    #----------------------------------------------------------------------
    def OnDropFiles(self, x, y, filenames):
        filename = filenames[0]
        logging.debug("File drop: %s", filename)
        appState.getOptionsByPath(filename)
        pub.sendMessage(PubSubEvents.ConfigUpdate)


        return True

class FileInputPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)

        file_drop_target = FilesDropTarget(self)
        self.SetDropTarget(file_drop_target)

        lbl_info = wx.StaticText(
            self, label="Drag and drop all files here",  style=wx.ALIGN_CENTER)
        lbl_video = wx.StaticText(self, label="Selected video path:")
        self.lbl_video_sel = wx.StaticText(self, label="")
        self.lbl_video_info = wx.StaticText(self, label="")
        lbl_osd = wx.StaticText(self, label="Selected osd file path")
        self.lbl_osd_sel = wx.StaticText(self, label="")
        self.lbl_osd_info = wx.StaticText(self, label="")
        lbl_font = wx.StaticText(self, label="Selected font path")
        self.lbl_font_sel = wx.StaticText(self, label="")
        self.lbl_font_info = wx.StaticText(self, label="")
        lbl_output = wx.StaticText(self, label="Output directory")
        self.lbl_output_sel = wx.StaticText(self, label="")
        self.lbl_output_info = wx.StaticText(self, label="")

        self.font_default = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.font_bold = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.font_warning = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)

        lbl_info.SetFont(self.font_default)
        self.lbl_osd_sel.SetFont(self.font_bold)
        self.lbl_osd_info.SetFont(self.font_bold)
        self.lbl_video_sel.SetFont(self.font_bold)
        self.lbl_video_info.SetFont(self.font_bold)
        self.lbl_font_sel.SetFont(self.font_bold)
        self.lbl_font_info.SetFont(self.font_bold)
        self.lbl_output_sel.SetFont(self.font_bold)
        self.lbl_output_info.SetFont(self.font_bold)

        box = wx.StaticBox(self, -1, "Import files")
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        hsizer = wx.BoxSizer()

        bsizer.Add(lbl_info, 0, wx.ALL, 5)
        bsizer.Add(lbl_video, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_video_sel, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_video_info, 0, wx.ALL, 5)
        bsizer.Add(lbl_osd, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_osd_sel, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_osd_info, 0, wx.ALL, 5)
        bsizer.Add(lbl_font, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_font_sel, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_font_info, 0, wx.ALL, 5)
        bsizer.Add(lbl_output, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_output_sel, 0, wx.ALL, 5)
        bsizer.Add(self.lbl_output_info, 0, wx.ALL, 5)


        bsizer.Add(hsizer, 0, wx.LEFT)
        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        pub.subscribe(self.eventConfigUpdate, PubSubEvents.ConfigUpdate)

        pass
    def eventConfigUpdate(self):
        self.updateSettings()

    def updateSettings(self):
        """
        Write text to the text control
        """
        self.lbl_video_sel.SetLabel(appState._video_path) 
        self.lbl_osd_sel.SetLabel(appState._osd_path) 
        self.lbl_font_sel.SetLabel(appState._font_path) 
        self.lbl_output_sel.SetLabel(appState._output_path) 

        self.updateInfo()

    def updateInfo(self):
        if appState._osd_path:
            soft_name = OSDFile(appState._osd_path, None).get_software_name()
            self.lbl_osd_info.SetLabel("Recognized '%s' software." % soft_name) 

        if appState._font_path:
            font = OsdFont(appState._font_path)
            font_size_text = ("HD" if font.is_hd() else "SD")
            self.lbl_font_info.SetLabel("Recognized '%s' font." % font_size_text) 

        if appState._video_path:
            video = VideoFile(appState._video_path)
            video_size_text = ("HD" if video.is_hd() else "SD")
            self.lbl_video_info.SetLabel("Recognized '%s' video." % video_size_text) 

        if appState.is_output_exists():
            self.lbl_output_info.SetLabel("Output directory already exists, remove it to continue and drag files again") 
        else:
            self.lbl_output_info.SetLabel("") 

        if appState._font_path and appState._video_path:
            font = OsdFont(appState._font_path)
            video = VideoFile(appState._video_path)
            if video.is_hd() != font.is_hd():
                self.lbl_font_info.SetLabel("Font doesn't match video resolution, please select '%s' font " % video_size_text ) 
        

class ButtonsPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)

        box = wx.StaticBox(self, -1, "")
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        bsizer.AddSpacer(20)
        hsizer = wx.BoxSizer()
        hsizer.AddSpacer(20)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.btnStartPng = wx.Button(self, label="Generate PNG sequence only")
        self.btnStartPng.Disable()
        vsizer.Add(self.btnStartPng)
        hsizer.Add(vsizer)
        hsizer.AddSpacer(20)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.btnStartVideo = wx.Button(self, label="Render video with OSD")
        self.btnStartVideo.Disable()
        vsizer.Add(self.btnStartVideo)
        hsizer.Add(vsizer)
        hsizer.AddSpacer(20)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        # cbo = wx.Button(self, label="Fuck this shit")
        # vsizer.Add(cbo)
        hsizer.Add(vsizer)
        bsizer.Add(hsizer, 0, wx.LEFT)

        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        bsizer.AddSpacer(20)
        self.SetSizer(main_sizer)

        pub.subscribe(self.eventConfigUpdate, PubSubEvents.ConfigUpdate)

    def eventConfigUpdate(self):
        configured = appState.is_configured()
        self.btnStartPng.Enable(configured)
        self.btnStartVideo.Enable(configured) 


class OsdSettingsPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)

        box = wx.StaticBox(self, -1, "OSD position")
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        bsizer.AddSpacer(20)
        hsizer = wx.BoxSizer()
        hsizer.AddSpacer(20)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label='Offset left')
        vsizer.Add(lbl)
        self.osdOffsetLeft = wx.Slider(self,name="OSD offset X", minValue=-200, maxValue=600, value=0, style=wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL, size=wx.Size(150, -1))
        self.osdOffsetLeft.Bind(wx.EVT_SCROLL_CHANGED, self.eventSliderUpdated)
        vsizer.Add(self.osdOffsetLeft)
        hsizer.Add(vsizer)
        hsizer.AddSpacer(20)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label='Offset top')
        vsizer.Add(lbl)
        self.osdOffsetTop = wx.Slider(self,name="OSD offset Y", minValue=-200, maxValue=600, value=0, style=wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL, size=wx.Size(150, -1))
        self.osdOffsetTop.Bind(wx.EVT_SCROLL_CHANGED, self.eventSliderUpdated)
        vsizer.Add(self.osdOffsetTop)
        hsizer.Add(vsizer)
        hsizer.AddSpacer(20)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label='Zoom')
        vsizer.Add(lbl)
        self.osdZoom = wx.Slider(self,name="OSD zoom", minValue=80, maxValue=200, value=100, style=wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL, size=wx.Size(150, -1))
        self.osdZoom.Bind(wx.EVT_SCROLL_CHANGED, self.eventSliderUpdated)
        vsizer.Add(self.osdZoom)
        hsizer.Add(vsizer)
        bsizer.Add(hsizer, 0, wx.LEFT)
        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        bsizer.AddSpacer(10)
        self.SetSizer(main_sizer)

        pass
    
    def eventSliderUpdated(self, event):
        logging.debug(f"Slider updated.")
        appState.updateOsdPosition(self.osdOffsetLeft.Value, self.osdOffsetTop.Value, self.osdZoom.Value)

        pub.sendMessage(PubSubEvents.PreviewUpdate)


class OsdPreviewPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        sizer = wx.StaticBoxSizer(
            orient=wx.VERTICAL, parent=self, label="OSD Preview")
        self.SetSizer(sizer)

        self.dummy = wx.StaticText(self, label="")

        sizer.Add(self.dummy)
        pub.subscribe(self.eventConfigUpdate, PubSubEvents.ConfigUpdate)
        pub.subscribe(self.eventConfigUpdate, PubSubEvents.PreviewUpdate)

        pass

    def eventConfigUpdate(self):
        if not appState.is_configured():
            return
        logging.debug(f"Preview update requested.")
        prev = OsdPreview(appState.get_osd_config())
        # prev.generate_preview((self.osdOffsetX.GetValue(),self.osdOffsetY.GetValue()), self.osdZoom.GetValue())
        prev.generate_preview((appState.offsetLeft, appState.offsetTop ),appState.osdZoom)


class MainWindow(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, parent=None,
                          title="Walksnail OSD overlay generator by Kirek")
        sizer = wx.BoxSizer(wx.VERTICAL)
        fileInput = FileInputPanel(self)
        osdSettings = OsdSettingsPanel(self)
        osdPreview = OsdPreviewPanel(self)
        buttonsPanel = ButtonsPanel(self)
        sizer.Add(fileInput, 0, wx.EXPAND | wx.ALL, 0)
        sizer.Add(osdSettings, 0, wx.EXPAND | wx.ALL, 0)
        sizer.Add(buttonsPanel, 0, wx.EXPAND | wx.ALL, 0)
        sizer.Add(osdPreview, 0, wx.EXPAND | wx.ALL, 0)
        self.SetSizer(sizer)
        self.Show()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = wx.App(False)

    frame = MainWindow()
    frame.Size = (700, 900)
    app.MainLoop()
