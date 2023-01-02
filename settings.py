import os
import pathlib

from processor import OsdGenStatus, OsdGenerator, OsdGenConfig


class AppState:

    def __init__(self) -> None:
        self._video_path = ""
        self._osd_path = ""
        self._font_path = ""
        self._output_path = ""
        self._osd_gen = None

        self.offsetLeft = 0
        self.offsetTop = 0
        self.osdZoom = 100

    def updateOsdPosition(self, left, top, zoom):
        self.offsetLeft = left
        self.offsetTop = top
        self.osdZoom = zoom

    def getOptionsByPath(self, path: str):
        file_ext = pathlib.Path(path).suffix

        match file_ext:
            case ".osd":
                self._osd_path = path
                video = os.fspath(pathlib.Path(path).with_suffix('.mp4'))
                if os.path.exists(video):
                    self._video_path = video
                self.update_output_path(path)
            case ".mp4":
                self._video_path = path
                osd = os.fspath(pathlib.Path(path).with_suffix('.osd'))
                if os.path.exists(osd):
                    self._osd_path = osd
                self.update_output_path(path)
            case ".png":
                self._font_path = path
            case _:
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
            self._output_path
        )

    def osd_init(self) -> OsdGenStatus:
        self._osd_gen = OsdGenerator(
            OsdGenConfig(
                self._video_path,
                self._osd_path,
                self._font_path,
                self._output_path
            ))
        return self.osd_gen_status()

    def osd_start_process(self):
        self._osd_gen.start()

    def osd_render_video(self):
        self._osd_gen.render()

    def get_osd(self):
        return self._osd_gen


appState = AppState()
