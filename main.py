import os
import pathlib
import wx
from processor import OSDFile, OsdFont, OsdPreview, VideoFile

from settings import appState
import cv2
########################################################################
class MyFileDropTarget(wx.FileDropTarget):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, window):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window

    #----------------------------------------------------------------------
    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        # self.window.SetInsertionPointEnd()
        # self.window.updateText("\n%d file(s) dropped at %d,%d:\n" %
        #                       (len(filenames), x, y))
        print(filenames)
        
        appState.getOptionsByPath(path=filenames[0])
        self.window.updateSettings()

        return True

########################################################################
class DnDPanel(wx.Panel):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, parent):
        """Constructor"""
        wx.Panel.__init__(self, parent=parent)

        self.font_default = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.font_bold = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        self.font_warning = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)

        lbl_info = wx.StaticText(self, label="Drag and drop all files here",  style=wx.ALIGN_CENTER)
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
        self.btnStart = wx.Button(self, label="Generate OSD")
        self.btnStart.Disable()

        p = wx.Panel(self)
        s = wx.BoxSizer(wx.VERTICAL)
        self.btnRender = wx.Button(p, label="Render video")
        self.osdOffsetX = wx.Slider(p,name="OSD offset X", minValue=-200, maxValue=600, value=0, size=wx.Size(200,20))
        self.osdOffsetY = wx.Slider(p,name="OSD offset Y", minValue=-200, maxValue=600, value=0, size=wx.Size(200,20))
        self.osdZoom = wx.Slider(p,name="OSD zoom", minValue=80, maxValue=200, value=100, size=wx.Size(200,20))
        s.Add(self.osdOffsetX, 0, wx.ALL, 5)
        s.Add(self.osdOffsetY, 0, wx.ALL, 5)
        s.Add(self.osdZoom, 0, wx.ALL, 5)
        s.Add(self.btnRender, 0, wx.ALL, 5)
        p.SetSizer(s)




        lbl_info.SetFont(self.font_default)

        self.lbl_osd_sel.SetFont(self.font_bold)
        self.lbl_osd_info.SetFont(self.font_bold)
        self.lbl_video_sel.SetFont(self.font_bold)
        self.lbl_video_info.SetFont(self.font_bold)
        self.lbl_font_sel.SetFont(self.font_bold)
        self.lbl_font_info.SetFont(self.font_bold)
        self.lbl_output_sel.SetFont(self.font_bold)
        self.lbl_output_info.SetFont(self.font_bold)

        self.lbl_output_info.SetForegroundColour((255,0,0))

        self.btnStart.Bind(wx.EVT_BUTTON,self.btnStartProcessOnClick) 
        self.btnRender.Bind(wx.EVT_BUTTON,self.btnRenderOnClick) 


        p2 = wx.Panel(self)
        s2 = wx.BoxSizer(wx.VERTICAL)
        p2.SetSizer(s2)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(p, 0, wx.ALL, 5)
        sizer.Add(p2, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        
        s2.Add(lbl_info, 0, wx.ALL, 5)
        s2.Add(lbl_video, 0, wx.ALL, 5)
        s2.Add(self.lbl_video_sel, 0, wx.ALL, 5)
        s2.Add(self.lbl_video_info, 0, wx.ALL, 5)
        s2.Add(lbl_osd, 0, wx.ALL, 5)
        s2.Add(self.lbl_osd_sel, 0, wx.ALL, 5)
        s2.Add(self.lbl_osd_info, 0, wx.ALL, 5)
        s2.Add(lbl_font, 0, wx.ALL, 5)
        s2.Add(self.lbl_font_sel, 0, wx.ALL, 5)
        s2.Add(self.lbl_font_info, 0, wx.ALL, 5)
        s2.Add(lbl_output, 0, wx.ALL, 5)
        s2.Add(self.lbl_output_sel, 0, wx.ALL, 5)
        s2.Add(self.lbl_output_info, 0, wx.ALL, 5)
        s2.Add(self.btnStart, 0, wx.ALL, 5)

        # sizer.Add(self.osdOffsetX, 0, wx.ALL, 5)
        # sizer.Add(self.osdOffsetY, 0, wx.ALL, 5)
        # sizer.Add(self.osdZoom, 0, wx.ALL, 5)
        # sizer.Add(self.btnRender, 0, wx.ALL, 5)
        
        


        file_drop_target = MyFileDropTarget(self)
        self.SetDropTarget(file_drop_target)

    def btnRenderOnClick(self, event):

        prev = OsdPreview(appState.get_osd_config())
        prev.generate_preview((self.osdOffsetX.GetValue(),self.osdOffsetY.GetValue()), self.osdZoom.GetValue())
        # appState.osd_render_video()
        # status = appState.osd_init()
        # pd = wx.ProgressDialog("Rendering Video", "Processing...", 1, self, style=wx.PD_CAN_ABORT | wx.PD_APP_MODAL | wx.PD_REMAINING_TIME | wx.PD_ELAPSED_TIME | wx.PD_SMOOTH)
        # pd.Show()
        # appState.osd_render_video()
        # keepGoing = True
        # while keepGoing and not appState.get_osd().render_done:
        #     wx.MilliSleep(200)
        #     keepGoing, skip = pd.Update(0)
        #     if appState.get_osd().render_done:
        #         pd.Update(1)
        #         keepGoing = False


        # if status.is_complete():
        #     mes = wx.MessageBox("OK")
        # else:
        #     mes = wx.MessageBox("Process canceled.", "CANCELED")
            
        # pd.Destroy()
        # self.updateSettings()


    def btnStartProcessOnClick(self, event): 
        print("pushed hard.")
        self.generateOsd()


    def generateOsd(self):
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
        self.updateSettings()
        

    #----------------------------------------------------------------------
    def updateSettings(self):
        """
        Write text to the text control
        """
        self.lbl_video_sel.SetLabel(appState._video_path) 
        self.lbl_osd_sel.SetLabel(appState._osd_path) 
        self.lbl_font_sel.SetLabel(appState._font_path) 
        self.lbl_output_sel.SetLabel(appState._output_path) 

        self.updateInfo()

        self.btnStart.Enable() if appState.is_configured() else self.btnStart.Disable()
            
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

########################################################################
class DnDFrame(wx.Frame):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        wx.Frame.__init__(self, parent=None, title="Walksnail OSD overlay generator by Kirek")
        panel = DnDPanel(self)
        self.Show()

#----------------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    

    frame = DnDFrame()
    frame.Size = (800, 900)
    app.MainLoop()