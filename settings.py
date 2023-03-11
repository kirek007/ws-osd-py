import os
import pathlib

from processor import OsdGenStatus, OsdGenerator, OsdGenConfig


class AppState:

    def __init__(self) -> None:
        self._video_path = ""
        self._osd_path = ""
        self._font_path = ""
        self._output_path = ""
        self._srt_path = ""
        self._osd_gen = None
        self._include_srt = False
        self._hide_sensitive_osd = False
        self._use_hw = False
        self._fast_srt = True

        self.offsetLeft = 0
        self.offsetTop = 0
        self.osdZoom = 100

        self.render_upscale = False

    def updateOsdPosition(self, left, top, zoom):
        self.offsetLeft = left
        self.offsetTop = top
        self.osdZoom = zoom

    def getOptionsByPath(self, path: str):
        file_ext = pathlib.Path(path).suffix

        if file_ext in {".osd", ".mp4", ".srt"}:
            video = os.fspath(pathlib.Path(path).with_suffix('.mp4'))
            srt = os.fspath(pathlib.Path(path).with_suffix('.srt'))
            osd = os.fspath(pathlib.Path(path).with_suffix('.osd'))
            if os.path.exists(video):
                self._video_path = video
            if os.path.exists(srt):
                self._srt_path = srt
            if os.path.exists(osd):
                self._osd_path = osd
            self.update_output_path(path)
        elif file_ext == ".png":
            self._font_path = path
        else:
            pass

    def update_output_path(self, path: str):
        self._output_path = os.path.join(
            path, "%s_generated" % os.path.splitext(path)[0])

    def is_output_exists(self):
        return os.path.exists(self._output_path)

    def is_configured(self) -> bool:
        if (self._font_path and self._osd_path and self._video_path and not self.is_output_exists()):
            return True
        else:
            return False 

    def osd_cancel_process(self):
        if self._osd_gen:
            self._osd_gen.stop()

    def osd_gen_status(self) -> OsdGenStatus:
        return self._osd_gen.osdGenStatus

    def get_osd_config(self) -> OsdGenConfig:
        return OsdGenConfig(
            self._video_path,
            self._osd_path,
            self._font_path,
            self._srt_path,
            self._output_path,
            self.offsetLeft,
            self.offsetTop,
            self.osdZoom,
            self.render_upscale,
            self._include_srt,
            self._hide_sensitive_osd,
            self._use_hw,
            self._fast_srt
        )

    def osd_init(self) -> OsdGenStatus:
        self._osd_gen = OsdGenerator(self.get_osd_config())
        return self.osd_gen_status()

    def osd_start_process(self):
        self._osd_gen.start()

    def osd_render_video(self):
        self._osd_gen.start_video(False)

    def osd_reset(self):
        self._osd_gen = None

    def get_osd(self):
        return self._osd_gen


appState = AppState()
