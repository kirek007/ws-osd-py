import argparse
import cProfile
import io
import os
from datetime import datetime
from pathlib import Path
from pstats import SortKey
import pstats
from struct import unpack
from threading import Thread

import cv2
import numpy as np

class CountsPerSec:
    """
    Class that tracks the number of occurrences ("counts") of an
    arbitrary event and returns the frequency in occurrences
    (counts) per second. The caller must increment the count.
    """

    def __init__(self):
        self._start_time = None
        self._num_occurrences = 0

    def start(self):
        self._start_time = datetime.now()
        return self

    def increment(self):
        self._num_occurrences += 1

    def countsPerSec(self):
        elapsed_time = (datetime.now() - self._start_time).total_seconds()
        return self._num_occurrences / elapsed_time

class OsdFont:

    GLYPH_HD_H = 18 * 3
    GLYPH_HD_W = 12 * 3
    GLYPH_SD_H = 18 * 2
    GLYPH_SD_W = 12 * 2

    def __init__(self, path):
        self.font = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    def get_glyph(self, index):
        size_h = self.GLYPH_HD_H if self.is_hd() else self.GLYPH_SD_H
        size_w = self.GLYPH_HD_W if self.is_hd() else self.GLYPH_SD_W

        pos_y = size_h * (index)
        pos_y2 = pos_y + size_h
        glyph = self.font[pos_y:pos_y2, 0:size_w]

        return glyph

    def is_hd(self):
        font_w = self.font.shape[1]
        return font_w == self.GLYPH_HD_W



class OSDFile:
    def __init__(self, path, font: OsdFont):
        self.osdFile = open(path, "rb")
        self.fcType = self.osdFile.read(4).decode("utf-8")
        self.magic = self.osdFile.read(36)
        self.font = font

    def read_frame(self):
        READ_SIZE = 2124
        rawData = self.osdFile.read(READ_SIZE)
        if len(rawData) < READ_SIZE:
            return False

        return Frame(rawData, self.font)
    
    def get_software_name(self):
        match self.fcType:
            case "BTFL":
                return "Betaflight"
            case "ARDU":
                return "Ardupilot"
            case "INAV":
                return "INav"
            case _ :
                return "Unknown"



class Frame:
    frame_w = 53
    frame_h = 20

    def __init__(self, data, font: OsdFont):
        raw_time = data[0:4]
        self.startTime = unpack("<L", raw_time)[0]
        self.rawData = data[4:]
        self.font = font

    def __convert_to_glyphs(self):
        glyphs_arr = []
        for x in range(0, len(self.rawData), 2):
            gindex = int(self.rawData[x:x + 1].hex(), base=16)
            glyph = self.font.get_glyph(gindex)
            glyphs_arr.append(glyph)
        return glyphs_arr

    def get_osd_frame_glyphs(self):
        glyphs = self.__convert_to_glyphs()
        osd_frame = []

        gi = 0
        for y in range(self.frame_h):
            frame_line = []
            for x in range(self.frame_w):
                frame_line.append(glyphs[gi])
                gi += 1
            osd_frame.append(frame_line)
        return osd_frame


class VideoFrame:

    def __init__(self, data):
        self.data = data


class VideoFile:

    def __init__(self, path):
        self.videoFile = cv2.VideoCapture(path)

    def get_current_time(self):
        return self.videoFile.get(cv2.CAP_PROP_POS_MSEC)

    def is_hd(self):
        h, w = self.get_size()
        return h == 1080

    def get_size(self):
        width = self.videoFile.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
        height = self.videoFile.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
        return int(height), int(width)

    def get_total_frames(self):
        return int(self.videoFile.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_fps(self):
        fps = self.videoFile.get(cv2.CAP_PROP_FPS)
        return fps

    def read_frame(self):
        ret, frame = self.videoFile.read()
        if not ret:
            return None
        
        if len(frame) == 0:
            return None

        return VideoFrame(frame)


class OsdGenConfig:
    def __init__(self, video_path, osd_path, font_path, output_path) -> None: 
        self.video_path = video_path
        self.osd_path = osd_path
        self.font_path = font_path
        self.output_path = output_path

class OsdGenStatus:
    def __init__(self) -> None:
        self.current_frame = -1
        self.total_frames = -1
        self.fps = -1

    def update(self, current, total, fps) -> None:
        self.current_frame = current
        self.total_frames = total
        self.fps = fps

    def is_complete(self) -> bool:
        return self.current_frame >= self.total_frames

class OsdGenerator:

    def __init__(self, config: OsdGenConfig):
        self.stopped = False
        
        
        self.font = OsdFont(config.font_path)
        self.osd = OSDFile(config.osd_path, self.font)
        self.video = VideoFile(config.video_path)
        self.output = config.output_path
        os.mkdir(self.output)

        self.osdGenStatus = OsdGenStatus()
        self.osdGenStatus.update(0, self.video.get_total_frames(), 0)

    def start(self):
        Thread(target=self.main, args=()).start()
        return self

    def stop(self):
        self.stopped = True


    @staticmethod
    def __render_osd_frame(osd_frame_glyphs):
        render = cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in osd_frame_glyphs])
        return render

    def __overlay_osd(self, video_frame, osd_frame):

        alpha_mask = osd_frame[:, :, 3] / 255.0
        img_overlay = osd_frame[:, :, :3]
        h, w, a = osd_frame.shape
        hh, ww, aa = video_frame.shape
        xoff = round((ww - w) / 2)
        self.overlay_image_alpha(video_frame, img_overlay, xoff, 0, alpha_mask)

        return video_frame


    def main(self): 
        cps = CountsPerSec().start()
        pr = cProfile.Profile()
        pr.enable()

        
        osd_time = -1
        osd_frame = []
        current_frame = 1
        while True:
            if self.stopped:
                print("Process canceled.")
                break

            video_frame = self.video.read_frame()
            video_time = self.video.get_current_time()
            current_frame+=1

            if not video_frame:
                break

            if osd_time < video_time:
                raw_osd_frame = self.osd.read_frame()
                if not raw_osd_frame:
                    break
                osd_frame = self.__render_osd_frame(raw_osd_frame.get_osd_frame_glyphs())
                osd_time = raw_osd_frame.startTime

            cv2.imwrite("%s/ws_%09d.png" % (self.output, current_frame), osd_frame)
            # cv2.imshow('frame', result)
            # if cv2.waitKey(1) == ord('q'):
            #     break

            cps.increment()
            total_frames = self.video.get_total_frames()
            fps = int(cps.countsPerSec())
            self.osdGenStatus.update(current_frame, total_frames, fps)

            if current_frame % 200 == 0:
                
                print("Current: %s/%s (fps: %d)" % (current_frame, total_frames, fps))
        
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        print("Done.")

