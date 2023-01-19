
from dataclasses import dataclass, field
import logging
import os
import platform
import subprocess


@dataclass()
class CodecItem:
    supported_os: list
    name: str

@dataclass
class CodecsList:
    codecs: list[CodecItem] = field(default_factory=list)

    def getbyOS(self, os_name: str) -> list[CodecItem]:
        return list(filter(lambda codec: os_name in codec.supported_os, self.codecs))
    
def load_codecs():

    macos = "macos"
    windows = "windows"
    linux = "linux"
    codecs = []

    codecs.append(CodecItem(name="h264_videotoolbox", supported_os=[macos]))
    codecs.append(CodecItem(name="h264_cuvid", supported_os=[windows, linux]))
    codecs.append(CodecItem(name="h264_nvenc", supported_os=[windows, linux]))
    codecs.append(CodecItem(name="h264_amf", supported_os=[windows]))
    codecs.append(CodecItem(name="h264_vaapi", supported_os=[linux]))
    codecs.append(CodecItem(name="h264_qsv", supported_os=[linux, windows]))
    codecs.append(CodecItem(name="h264_mf", supported_os=[windows]))
    codecs.append(CodecItem(name="h264_v4l2m2m", supported_os=[linux]))

    codecs.append(CodecItem(name="libx264", supported_os=[macos, windows, linux]))
    logging.info("tesT")

    return codecs

def get_working_encoder():
    available_codecs = codecs.getbyOS(platform.system().lower())
    logging.info("Got these: %s", available_codecs)
    # ffmpeg -hwaccel auto -f lavfi -i nullsrc -c:v hevc_nvenc -frames:v 1 test.mp4

codecs = CodecsList(load_codecs())
aa= codecs.getbyOS(platform.system().lower())
run_line = "ffmpeg -y -hwaccel auto -c:v %s -f lavfi -i nullsrc -c:v %s -frames:v 1 -f null -"
for codec in aa:
    runme = (run_line % (codec.name, codec.name)).split(" ")
    ret = subprocess.run(runme)
    # , 
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.DEVNULL)

    if ret.returncode == 0:
        print(codec)
        
        
        
            # ret = os.system(run_line % codec.name)
