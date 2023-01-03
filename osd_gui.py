from enum import Enum
import logging
import wx
from processor import OSDFile, OsdFont, OsdPreview, VideoFile
import wx.lib.agw.hyperlink as hl

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
        self.lbl_output_info.SetForegroundColour((255,0,0))

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
            self.lbl_output_info.SetLabel("Output directory already exists, remove it to regenerate PNG files") 
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
        self.cbo_upscale = wx.CheckBox(self, label="Upscale video to 1440p")
        vsizer.Add(self.cbo_upscale)
        hsizer.Add(vsizer)
        bsizer.Add(hsizer, 0, wx.LEFT)

        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        bsizer.AddSpacer(20)
        self.SetSizer(main_sizer)

        pub.subscribe(self.eventConfigUpdate, PubSubEvents.ConfigUpdate)

        self.btnStartPng.Bind(wx.EVT_BUTTON, self.btnStartPngClick)
        self.btnStartVideo.Bind(wx.EVT_BUTTON, self.btnStartVideoClick)
        self.cbo_upscale.Bind(wx.EVT_CHECKBOX, self.chekboxClick)

    def chekboxClick(self, event):
        appState.render_upscale = bool(self.cbo_upscale.Value)

    def eventConfigUpdate(self):
        configured = appState.is_configured()
        self.btnStartPng.Enable(configured)
        self.btnStartVideo.Enable(appState.is_output_exists()) 
    
    def btnStartVideoClick(self, event):
        status = appState.osd_init()
        pd = wx.ProgressDialog("Rendering video", "Check console log for status", 1, self, style=wx.PD_APP_MODAL)
        pd.Show()
        appState.osd_render_video()
        _osd_gen = appState._osd_gen
        while not _osd_gen.render_done:
            wx.MilliSleep(200)
            pd.Update(0)
        pd.Update(1)
        mes = wx.MessageBox("Render done.", "OK")
        pd.Destroy()
        pub.sendMessage(PubSubEvents.ConfigUpdate)
        

    def btnStartPngClick(self, event):
        status = appState.osd_init()
        pd = wx.ProgressDialog("Generating OSD", "Processing frames...", status.total_frames + 1, self, style=wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_REMAINING_TIME | wx.PD_ELAPSED_TIME | wx.PD_SMOOTH)
        pd.Show()
        appState.osd_start_process()
        keepGoing = True
        while keepGoing and not status.is_complete():
            wx.MilliSleep(200)
            keepGoing, skip = pd.Update(status.current_frame)
            if not keepGoing:
                appState.osd_cancel_process()
        
        if status.is_complete():
            mes = wx.MessageBox("OSD overlay files are in '%s' directory" % appState._output_path, "OK")
        else:
            mes = wx.MessageBox("Process canceled.", "CANCELED")
            
        pd.Destroy()
        pub.sendMessage(PubSubEvents.ConfigUpdate)


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

class BottomPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)

        box = wx.StaticBox(self, -1, "")
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        bsizer.AddSpacer(20)
        hsizer = wx.BoxSizer()
        hsizer.AddSpacer(20)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hyper2 = hl.HyperLinkCtrl(self, -1, "Latest version always here!",
                    URL="https://github.com/kirek007/ws-osd-pyk")
        vsizer.Add(hyper2)
        hsizer.Add(vsizer)
        hsizer.AddSpacer(20)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hyper2 = hl.HyperLinkCtrl(self, -1, "Psst, this is coffee driven application ;)",
                            URL="https://www.buymeacoffee.com/kirek")
        vsizer.Add(hyper2)
        hsizer.Add(vsizer)
        bsizer.Add(hsizer, 0, wx.LEFT)
        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        bsizer.AddSpacer(20)
        self.SetSizer(main_sizer)

class PrewievPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        
        box = wx.StaticBox(self, -1, "")
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        bsizer.AddSpacer(20)
        img = wx.EmptyImage(640, 360)
        self.imageCtrl = wx.StaticBitmap(self, wx.ID_ANY, 
                                         wx.BitmapFromImage(img))
        bsizer.Add(self.imageCtrl)                                 
        main_sizer = wx.BoxSizer()
        main_sizer.Add(bsizer, 1, wx.EXPAND | wx.ALL, 10)
        bsizer.AddSpacer(20)
        self.SetSizer(main_sizer)
        pub.subscribe(self.eventConfigUpdate, PubSubEvents.PreviewUpdate)
   
    def eventConfigUpdate(self):
        if not appState.is_configured():
            return
        logging.debug(f"Preview update requested.")
        self.onView()


    def onView(self):

        prev = OsdPreview(appState.get_osd_config())
        image = prev.generate_preview((appState.offsetLeft, appState.offsetTop ),appState.osdZoom)
        self.imageCtrl.SetBitmap(wx.Bitmap.FromBuffer(640, 360, image))
        self.imageCtrl.Refresh()
        self.Refresh()

class MainWindow(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, parent=None,
                          title="Walksnail OSD overlay tool")
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        fileInput = FileInputPanel(self)
        osdSettings = OsdSettingsPanel(self)
        buttonsPanel = ButtonsPanel(self)
        bottomPanel = BottomPanel(self)
        prewievPanel = PrewievPanel(self)
        vsizer.Add(fileInput, 0, wx.EXPAND | wx.ALL, 0)
        vsizer.Add(osdSettings, 0, wx.EXPAND | wx.ALL, 0)
        vsizer.Add(buttonsPanel, 0, wx.EXPAND | wx.ALL, 0)
        vsizer.Add(bottomPanel, 0, wx.EXPAND | wx.ALL, 0)
        main_sizer.Add(vsizer)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(prewievPanel, 0, wx.EXPAND, 0)
        main_sizer.Add(vsizer)
        self.SetSizer(main_sizer)
        self.Show()

        pub.subscribe(self.eventConfigUpdate, PubSubEvents.ConfigUpdate)
        pub.subscribe(self.eventConfigUpdate, PubSubEvents.PreviewUpdate)

    def eventConfigUpdate(self):
        if not appState.is_configured():
            return
        logging.debug(f"Preview update requested.")
        prev = OsdPreview(appState.get_osd_config())
        prev.generate_preview((appState.offsetLeft, appState.offsetTop ),appState.osdZoom)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = wx.App(False)

    frame = MainWindow()
    frame.Size = (1200, 785)
    frame.MinSize = wx.Size(1200, 785) 
    app.MainLoop()
