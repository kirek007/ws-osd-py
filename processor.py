import cProfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import io
import logging
import multiprocessing
import os
from datetime import datetime
import platform
from pstats import SortKey
import pstats
import queue
from struct import unpack
import subprocess
from threading import Thread
import cv2
import numpy as np
import ffmpeg
import srt
from PIL import ImageFont, ImageDraw, Image


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

    def get_srt_font_size(self):
        if self.is_hd():
            return 32
        else:
            return 24


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
            case _:
                return "Unknown"


class Frame:
    frame_w = 53
    frame_h = 20

    def __init__(self, data, font: OsdFont):
        raw_time = data[0:4]
        self.startTime = unpack("<L", raw_time)[0]
        self.rawData = data[4:]
        self.font = font

        self.glyph_hide_start = [
            3,  # gps
            4,  # gps
            16,  # home distance
            345,  # alt symb

        ]
        self.glyph_hide_len = [
            6,
            6,
            3,
            3,
        ]
        self.mask_glyph_no = ord("*")
        self.curent_mask_index = -1
        self.curent_mask_counter = 0

    def __convert_to_glyphs(self, hide):
        glyphs_arr = []
        for x in range(0, len(self.rawData), 2):
            index, page = unpack("<BB", self.rawData[x:x + 2])
            glyph_index = index + page * 256

            if hide and glyph_index in self.glyph_hide_start:
                self.curent_mask_index = self.glyph_hide_start.index(
                    glyph_index)

            if hide and self.curent_mask_index > -1:
                if self.curent_mask_counter < self.glyph_hide_len[self.curent_mask_index]:

                    if self.curent_mask_counter > 0:
                        glyph_index = self.mask_glyph_no
                    self.curent_mask_counter += 1
                else:
                    self.curent_mask_counter = 0
                    self.curent_mask_index = -1

            glyph = self.font.get_glyph(glyph_index)
            glyphs_arr.append(glyph)

        return glyphs_arr

    def get_osd_frame_glyphs(self, hide):
        glyphs = self.__convert_to_glyphs(hide)
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
        height = self.videoFile.get(
            cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
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
    def __init__(self, video_path, osd_path, font_path, srt_path, output_path, offset_left, offset_top, osd_zoom, render_upscale, include_srt, hide_sensitive_osd, use_hw, fast_srt) -> None:
        self.video_path = video_path
        self.osd_path = osd_path
        self.font_path = font_path
        self.srt_path = srt_path
        self.output_path = output_path
        self.offset_left = offset_left
        self.offset_top = offset_top
        self.osd_zoom = osd_zoom
        self.render_upscale = render_upscale
        self.include_srt = include_srt
        self.hide_sensitive_osd = hide_sensitive_osd
        self.use_hw = use_hw
        self.fast_srt = fast_srt


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
        scale_percent = zoom  # percent of original size
        width = int(overlay.shape[1] * scale_percent / 100)
        height = int(overlay.shape[0] * scale_percent / 100)
        dim = (width, height)
        img_overlay_res = cv2.resize(
            overlay, dim, interpolation=cv2.INTER_CUBIC)
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
        scale_percent = zoom  # percent of original size
        width = int(img_overlay.shape[1] * scale_percent / 100)
        height = int(img_overlay.shape[0] * scale_percent / 100)
        dim = (width, height)
        img_overlay_res = cv2.resize(
            img_overlay, dim, interpolation=cv2.INTER_CUBIC)

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

    @staticmethod
    def overlay_srt_line(fast, img, line, font_size, left_offset):
        if fast:
            return Utils.overlay_srt_line_fast(img, line, font_size, left_offset)
        else:
            return Utils.overlay_srt_line_slow(img, line, font_size, left_offset)

    @staticmethod
    def overlay_srt_line_slow(img, line, font_size, left_offset):
        pos_calc = (left_offset, img.shape[0] - 15)
        pil_im = Image.fromarray(img)
        draw = ImageDraw.Draw(pil_im, 'RGBA')
        font = ImageFont.truetype("font.ttf", font_size)

        draw.text(pos_calc, line, font=font, fill=(
            255, 255, 255, 255), anchor="lb")
        return Utils.to_numpy(pil_im)

        # pos_calc = (20, img.shape[0] - 30)
        # cv2.putText(img, line, pos_calc, cv2.FONT_ITALIC, 1/10 * font_size, (255, 255, 255, 255), 1)

        # return img
        
    @staticmethod
    def overlay_srt_line_fast(img, line, font_size, left_offset):
        left_offset = 200 if img.shape[1] > 1300 else 100 
        pos_calc = (left_offset, img.shape[0] - 30)
        cv2.putText(img, line, pos_calc, cv2.FONT_HERSHEY_COMPLEX, 1/40 * font_size, (255, 255, 255, 255), 1)

        return img
    @staticmethod
    def to_numpy(im):
        im.load()
        # unpack data
        e = Image._getencoder(im.mode, 'raw', im.mode)
        e.setimage(im.im)

        # NumPy buffer for the result
        shape, typestr = Image._conv_type_shape(im)
        data = np.empty(shape, dtype=np.dtype(typestr))
        mem = data.data.cast('B', (data.data.nbytes,))

        bufsize, s, offset = 65536, 0, 0
        while not s:
            l, s, d = e.encode(bufsize)
            mem[offset:offset + len(d)] = d
            offset += len(d)
        if s < 0:
            raise RuntimeError("encoder error %d in tobytes" % s)
        return data


class OsdPreview:

    def __init__(self, config: OsdGenConfig):
        self.stopped = False

        self.font = OsdFont(config.font_path)
        self.osd = OSDFile(config.osd_path, self.font)
        self.video = VideoFile(config.video_path)
        if config.srt_path:
            self.srt = SrtFile(config.srt_path)
        else:
            self.srt = None
        self.output = config.output_path
        self.config = config

    def str_line_to_glyphs(self, line):
        filler = self.font.get_glyph(32)
        rssi = self.font.get_glyph(1)
        glyphs = [filler, rssi]
        for char in line:
            gi = ord(char)
            g = self.font.get_glyph(gi)
            glyphs.append(g)

        for x in range(len(glyphs), 53):
            glyphs.append(filler)

        return glyphs[:53]

    def generate_preview(self, osd_pos, osd_zomm):

        video_frame = self.video.read_frame().data

        for skipme in range(20):
            self.osd.read_frame()
            if self.srt:
                srt_data = self.srt.next_data()

        osd_frame_glyphs = self.osd.read_frame().get_osd_frame_glyphs(
            hide=self.config.hide_sensitive_osd)

        osd_frame = cv2.vconcat([cv2.hconcat(im_list_h)
                                for im_list_h in osd_frame_glyphs])
        if self.srt and self.config.include_srt:
            srt_line = srt_data["line"]
            video_frame = Utils.overlay_srt_line(
                self.config.fast_srt, video_frame, srt_line, self.font.get_srt_font_size(), (150 if self.font.is_hd() else 100))
        Utils.overlay_image_alpha(
            video_frame, osd_frame, osd_pos[0], osd_pos[1], osd_zomm)
        result = cv2.resize(video_frame, (640, 360),
                            interpolation=cv2.INTER_AREA)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

        return result
        # return result


class SrtFile():
    def __init__(self, path):
        self.index = 0
        with open(path, "r") as f:
            self.subs = list(srt.parse(f, True))

    def next_data(self) -> dict:
        if self.index >= len(self.subs):
            self.index = len(self.subs) - 1
        sub = self.subs[self.index]
        data = dict(x.split(":") for x in sub.content.split(" "))
        d = dict()
        d["startTime"] = sub.start.seconds * 1000 + sub.start.microseconds / 1000
        d["data"] = data  # sub.start.seconds / 1000 * sub.start.microseconds
        d["line"] = "Signal:%1s   Delay:%5s   Bitrate:%7s   Distance:%5s" % (
            data["Signal"], data["Delay"],  data["Bitrate"], data["Distance"])
        self.index += 1
        return d


class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, maxsize=50, *args, **kwargs):
        super(ThreadPoolExecutorWithQueueSizeLimit,
              self).__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)


@dataclass()
class CodecItem:
    supported_os: list
    name: str

@dataclass
class CodecsList:
    codecs: list[CodecItem] = field(default_factory=list)

    def getbyOS(self, os_name: str) -> list[CodecItem]:
        return list(filter(lambda codec: os_name in codec.supported_os, self.codecs))


class OsdGenerator:

    def __init__(self, config: OsdGenConfig):
        self.stopped = False

        self.font = OsdFont(config.font_path)
        self.osd = OSDFile(config.osd_path, self.font)
        self.video = VideoFile(config.video_path)
        self.output = config.output_path
        self.config = config
        self.osdGenStatus = OsdGenStatus()
        self.render_done = False
        self.use_hw = config.use_hw
        self.codecs = CodecsList(self.load_codecs())

        if config.srt_path:
            self.srt = SrtFile(config.srt_path)
        else:
            self.srt = None
        self.osdGenStatus.update(0, self.video.get_total_frames(), 0)
        try:
            os.mkdir(self.output)
        except:
            pass

    def load_codecs(self):

        macos = "darwin"
        windows = "windows"
        linux = "linux"
        codecs = []
        if self.use_hw:
            codecs.append(CodecItem(name="hevc_videotoolbox", supported_os=[macos]))
            codecs.append(CodecItem(name="hevc_nvenc", supported_os=[windows, linux]))
            codecs.append(CodecItem(name="hevc_amf", supported_os=[windows]))
            codecs.append(CodecItem(name="hevc_vaapi", supported_os=[linux]))
            codecs.append(CodecItem(name="hevc_qsv", supported_os=[linux, windows]))
            codecs.append(CodecItem(name="hevc_mf", supported_os=[windows]))
            codecs.append(CodecItem(name="hevc_v4l2m2m", supported_os=[linux]))

        codecs.append(CodecItem(name="libx265", supported_os=[macos, windows, linux]))

        return codecs

    def get_working_encoder(self):
        available_codecs = self.codecs.getbyOS(platform.system().lower())
        run_line = "ffmpeg -y -hwaccel auto -f lavfi -i nullsrc -c:v %s -frames:v 1 -f null -"
        for codec in available_codecs:
            runme = (run_line % codec.name).split(" ")
            ret = subprocess.run(runme, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            if ret.returncode == 0:
                logging.info("Found a working codec (%s)" % codec.name)
                return codec.name
            
        raise Exception("There is no valid codedc. It should not happen")
        
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
        render = cv2.vconcat([cv2.hconcat(im_list_h)
                             for im_list_h in osd_frame_glyphs])
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

        input_args = {
            "hwaccel": "auto",
        }

        video = (
            ffmpeg
            .input(self.config.video_path, **input_args)
            .filter("scale", **ff_size, force_original_aspect_ratio=1, )
        )
        encoder_name = self.get_working_encoder()
        output_args = {
            "c:v": encoder_name,
            "preset": "fast",
            "crf": 0,
            "b:v": "40M",
            "acodec": "copy"
        }
        self.render_done = False
        process = (
            video
            .filter("pad", **ff_size, x=-1, y=-1, color="black")
            .overlay(osd_frame, x=0, y=0)
            .output("%s_osd.mp4" % (self.output),  **output_args)
            .overwrite_output()
            .run()
        )
        self.render_done = True

    def main(self):
        cps = CountsPerSec().start()
        pr = cProfile.Profile()
        pr.enable()

        osd_time = -1
        osd_frame = []
        current_frame = 1
        srt_time = -1
        video_fps = self.video.get_fps()
        total_frames = self.video.get_total_frames()
        video_size = self.video.get_size()
        img_height, img_width = video_size[0], video_size[1]
        n_channels = 4
        transparent_img = np.zeros(
            (img_height, img_width, n_channels), dtype=np.uint8)
        frame = transparent_img.copy()
        executor = ThreadPoolExecutorWithQueueSizeLimit(
            max_workers=multiprocessing.cpu_count()-1, maxsize=2000)

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
                osd_frame = self.__render_osd_frame(
                    raw_osd_frame.get_osd_frame_glyphs(hide=self.config.hide_sensitive_osd))
                osd_time = raw_osd_frame.startTime
                Utils.merge_images(frame, osd_frame, self.config.offset_left,
                                   self.config.offset_top, self.config.osd_zoom)
                osd_frame_no_srt = osd_frame
                
            if self.srt and self.config.include_srt:
                if srt_time < calc_video_time:
                    srt_data = self.srt.next_data()
                    srt_time = srt_data["startTime"]

                    frame_osd_srt = Utils.overlay_srt_line(self.config.fast_srt, osd_frame_no_srt, srt_data["line"], self.font.get_srt_font_size(
                        ), (150 if self.font.is_hd() else 100))
                    result = frame_osd_srt
            else:
                result = frame_osd_srt
                
            # logging.debug(f"frame':{current_frame},'total':{total_frames},'srt':{srt_time},'osd':{osd_time},'video':{calc_video_time}")
            out_path = os.path.join(self.output, "ws_%09d.png" % (current_frame))
            executor.submit(cv2.imwrite, out_path, result)

            current_frame += 1
            cps.increment()
            fps = int(cps.countsPerSec())
            self.osdGenStatus.update(current_frame - 1, total_frames, fps)

            if current_frame % 200 == 0:
                logging.debug("Current: %s/%s (fps: %d)" %
                              (current_frame, total_frames, fps))

        logging.info("Waiting for jobs to complete")
        executor.shutdown(cancel_futures=False, wait=True)
        logging.info("Save complete")
        self.osdGenStatus.update(total_frames, total_frames, fps)
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        logging.debug(s.getvalue())
