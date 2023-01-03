import argparse
import cProfile
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from pstats import SortKey
import pstats
from struct import unpack
from subprocess import TimeoutExpired
from threading import Thread
import time

import cv2
import numpy as np
import ffmpeg

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

    READ_SIZE = 2124

    def __init__(self, path, font: OsdFont):
        self.osdFile = open(path, "rb")
        self.fcType = self.osdFile.read(4).decode("utf-8")
        self.magic = self.osdFile.read(36)
        self.font = font

    def peek_frame(self, frame_no):
        frame_start = frame_no * self.READ_SIZE
        current_pos = self.osdFile.tell()
        self.osdFile.seek(frame_start)
        frame = self.read_frame()
        self.osdFile.seek(current_pos)

        return frame

    def read_frame(self):
        
        rawData = self.osdFile.read(self.READ_SIZE)
        if len(rawData) < self.READ_SIZE:
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
    def __init__(self, video_path, osd_path, font_path, output_path, offset_left, offset_top, osd_zoom, render_upscale) -> None: 
        self.video_path = video_path
        self.osd_path = osd_path
        self.font_path = font_path
        self.output_path = output_path
        self.offset_left = offset_left
        self.offset_top = offset_top
        self.osd_zoom = osd_zoom
        self.render_upscale = render_upscale

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

class Utils:
    
    @staticmethod
    def merge_images(img, overlay, x, y, zoom):
        scale_percent = zoom # percent of original size
        width = int(overlay.shape[1] * scale_percent / 100)
        height = int(overlay.shape[0] * scale_percent / 100)
        dim = (width, height)
        img_overlay_res = cv2.resize(overlay, dim, interpolation = cv2.INTER_CUBIC)
        # img_crop = img_overlay_res[y:img.shape[0],x:img.shape[1]]

        # Image ranges
        y1, y2 = max(0, y), min(img.shape[0], y + img_overlay_res.shape[0])
        x1, x2 = max(0, x), min(img.shape[1], x + img_overlay_res.shape[1])

        # Overlay ranges
        y1o, y2o = max(0, -y), min(img_overlay_res.shape[0], img.shape[0] - y)
        x1o, x2o = max(0, -x), min(img_overlay_res.shape[1], img.shape[1] - x)

        img_crop = img[y1:y2, x1:x2]
        img_overlay_crop = img_overlay_res[y1o:y2o, x1o:x2o]

        img_crop[:] = img_overlay_crop + img_crop
        img = img_crop
        # img[y:y+img_crop.shape[0], x:x+img_crop.shape[1]] = img_crop
        

    @staticmethod
    def overlay_image_alpha(img, img_overlay, x, y, zoom):
        scale_percent = zoom # percent of original size
        width = int(img_overlay.shape[1] * scale_percent / 100)
        height = int(img_overlay.shape[0] * scale_percent / 100)
        dim = (width, height)
        img_overlay_res = cv2.resize(img_overlay, dim, interpolation = cv2.INTER_CUBIC)

        # Mask
        alpha_mask = img_overlay_res[:, :, 3] / 255.0
        img_overlay_res = img_overlay_res[:, :, :3]

        # Image ranges
        y1, y2 = max(0, y), min(img.shape[0], y + img_overlay_res.shape[0])
        x1, x2 = max(0, x), min(img.shape[1], x + img_overlay_res.shape[1])

        # Overlay ranges
        y1o, y2o = max(0, -y), min(img_overlay_res.shape[0], img.shape[0] - y)
        x1o, x2o = max(0, -x), min(img_overlay_res.shape[1], img.shape[1] - x)

        # Exit if nothing to do
        if y1 >= y2 or x1 >= x2 or y1o >= y2o or x1o >= x2o:
            return

        # Blend overlay within the determined ranges
        img_crop = img[y1:y2, x1:x2]
        img_overlay_crop = img_overlay_res[y1o:y2o, x1o:x2o]
        alpha = alpha_mask[y1o:y2o, x1o:x2o, np.newaxis]
        alpha_inv = 1.0 - alpha

        img_crop[:] = alpha * img_overlay_crop + alpha_inv * img_crop

class OsdPreview:

    def __init__(self, config: OsdGenConfig):
        self.stopped = False
        
        
        self.font = OsdFont(config.font_path)
        self.osd = OSDFile(config.osd_path, self.font)
        self.video = VideoFile(config.video_path)
        self.output = config.output_path
        self.config = config



    def generate_preview(self, osd_pos, osd_zomm):

        video_frame = self.video.read_frame().data

        for skipme in range(100):
            self.osd.read_frame()

        osd_frame_glyphs =  self.osd.read_frame().get_osd_frame_glyphs()
        osd_frame = cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in osd_frame_glyphs])

        Utils.overlay_image_alpha(video_frame, osd_frame, osd_pos[0], osd_pos[1], osd_zomm)
        result = cv2.resize(video_frame, (1280, 720), interpolation = cv2.INTER_CUBIC)

        cv2.imshow("Preview", result)
        cv2.waitKey(1)


class OsdGenerator:

    def __init__(self, config: OsdGenConfig):
        self.stopped = False

        self.font = OsdFont(config.font_path)
        self.osd = OSDFile(config.osd_path, self.font)
        self.video = VideoFile(config.video_path)
        self.output = config.output_path
        self.config = config
        self.osdGenStatus = OsdGenStatus()
        self.osdGenStatus.update(0, self.video.get_total_frames(), 0)
        try:
            os.mkdir(self.output)
        except:
            pass



    def start_video(self, upscale: bool):
        Thread(target=self.render, args=()).start()
        return self

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

    def render(self):
        self.osdGenStatus.update(0, 1, 0)

        video_size = self.video.get_size()
        if self.config.render_upscale:
            ff_size = {"w": 2560, "h": 1440}
        else:
            ff_size = {"w": video_size[1], "h": video_size[0]}


        out_path = os.path.join(self.output, "ws_%09d.png")
        osd_frame = (
            ffmpeg
            .input(out_path, framerate=60)
            .filter("scale", **ff_size, force_original_aspect_ratio=0)
        )

        video = (
            ffmpeg
            .input(self.config.video_path)
            .filter("scale", **ff_size, force_original_aspect_ratio=1)
        )

        self.render_done = False
        process = (
            video
            .filter("pad", **ff_size, x=-1, y=-1, color="black")
            .overlay(osd_frame, x=0, y=0)
            .output("%s_osd.mp4" % (self.output), video_bitrate="40M")
            .overwrite_output() 
            .run()
        )

        self.render_done = True

    def render_example(self):
        frame = []
        return frame

    def main(self): 
        cps = CountsPerSec().start()
        pr = cProfile.Profile()
        pr.enable()

        
        osd_time = -1
        osd_frame = []
        current_frame = 1
        video_fps = self.video.get_fps()
        total_frames = self.video.get_total_frames()
        video_size = self.video.get_size()
        img_height, img_width = video_size[0], video_size[1]
        n_channels = 4
        transparent_img = np.zeros((img_height, img_width, n_channels), dtype=np.uint8) 
        frame = transparent_img.copy()
        while True:
            if self.stopped:
                print("Process canceled.")
                break

         

            frames_per_ms = 1 / video_fps * 1000
            calc_video_time = int((current_frame - 1) * frames_per_ms)

            if current_frame >= total_frames:
                break

            if osd_time < calc_video_time:
                raw_osd_frame = self.osd.read_frame()
                if not raw_osd_frame:
                    break
                frame = transparent_img.copy()
                osd_frame = self.__render_osd_frame(raw_osd_frame.get_osd_frame_glyphs())
                Utils.merge_images(frame, osd_frame, self.config.offset_left, self.config.offset_top, self.config.osd_zoom)
                osd_time = raw_osd_frame.startTime

            out_path = os.path.join(self.output, "ws_%09d.png" % (current_frame))
            cv2.imwrite(out_path, frame)


            current_frame+=1
            cps.increment()
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

