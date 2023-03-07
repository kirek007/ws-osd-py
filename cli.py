import logging
import os
import shutil
import secrets
from argparse import ArgumentParser

from processor import OsdGenConfig, OsdGenerator, Utils


def implicit_path(video_path, ext):
    """
    Attempts to find a path for the OSD and SRT files implicitly
    file_path: path to the video (mp4) file
    ext: file type suffix (e.g. osd or srt)
    """
    folder, _ = os.path.splitext(video_path)
    implied_path = f"{folder}.{ext}"
    if not os.path.isfile(implied_path):
        raise FileNotFoundError(f'Tried to find {ext} file at '
                                f'"{implied_path}" based off {video_path}'
                                f' but file not found')
    return implied_path


def default_output_path(video_path):
    """
    Determines a default path for the output PNGs and files
    """
    random_hex = secrets.token_hex(3)
    _, video_file = os.path.split(video_path)
    file, ext = os.path.splitext(video_file)
    return f"{os.getcwd()}/{file}-{random_hex}"


def video_osd_srt_parser(args):
    """
    This function takes arguments and works out if the values provided are
    usable. For example, if three video paths are provided by only two OSD,
    This should raise an error
    """
    if args.include_srt and args.srt_path is not None:
        srt_paths = args.srt_path

    else:
        srt_paths = []
        logging.debug("Include SRT specified but no path given")
        for video_file in args.video_path:
            srt_paths.append(implicit_path(video_file, 'srt'))

    if args.osd_path is not None:
        osd_paths = args.osd_path
    else:
        osd_paths = []
        logging.debug("No OSD Paths specified")
        for video_file in args.video_path:
            osd_paths.append(implicit_path(video_file, 'osd'))

    if args.include_srt:
        if not (len(args.video_path) == len(srt_paths) == len(osd_paths)):
            logging.debug(str(args.video_path))
            logging.debug(str(srt_paths))
            logging.debug(str(osd_paths))
            msg = f"{len(args.video_path)} video paths, {len(srt_paths)} srt " \
                  f"paths and {len(osd_paths)} osd paths provided"
            raise ValueError(msg)
    else:
        if not (len(args.video_path) == len(osd_paths)):
            logging.debug(str(args.video_path))
            logging.debug(str(osd_paths))
            msg = f"{len(args.video_path)} video paths and {len(osd_paths)} " \
                  f"osd paths provided"
            raise ValueError(msg)
    return args.video_path, osd_paths, srt_paths


if __name__ == '__main__':

    parser = ArgumentParser(
        description="CLI tool for OSD generator",
        epilog='Example: python .\cli.py --video-path "video.mp4" --font-path "sneaky_font.png"',
    )
    parser.add_argument('--video-path', help='Path to the video file',
                        required=True, nargs='+')
    parser.add_argument('--osd-path', help='Path to the OSD file. If none '
                                           'specified, it will look in the same'
                                           ' directory as the video path',
                        nargs='?')
    parser.add_argument('--srt-path', help='Path to SRT file. If none '
                                           'specified, it will look in the same'
                                           ' directory as the video path',
                        nargs='?')
    parser.add_argument('--font-path', required=True,
                        help='Path to font file - e.g (INAV_36.png)')
    parser.add_argument('--output-file',
                        help='Output path for PNG folder and finished video')
    parser.add_argument('--remove-png', default=False, action='store_true',
                        help='Delete PNGs after rendering video. Option only '
                             'works if rendering video')
    parser.add_argument('--no-video', default=False, action='store_true',
                        help='Do not render video, only create the PNGs. '
                             'Default Behavior is to render video')
    parser.add_argument('--offset-top', type=int, default=0,
                        help='Offset from top for OSD')
    parser.add_argument('--offset-left', help='Offset from left for OSD',
                        default=0, type=int)
    parser.add_argument('--osd-zoom', type=int, default=100,
                        help='Scaling of OSD elements')
    parser.add_argument('--render-upscale', default=False,
                        help='Increase video dimensions to 1440p')
    parser.add_argument('--include-srt', action='store_true', default=False,
                        help='Include SRT data from VTX')
    parser.add_argument('--hide-sensitive-osd', action='store_true',
                        help='Hide Sensitive Elements like lat, lon, altitude, '
                             'home', default=False)
    parser.add_argument('--no-hw-accel', action='store_true', default=False,
                        help='Disable Hardware Acceleration of ffmpeg if flag '
                             'specified. By default and without this flag, '
                             'Hardware acceleration will be used')
    parser.add_argument('--fast-srt', action='store_true', default=False,
                        help='')
    parser.add_argument('--no-concat', action='store_true', default=False,
                        help='If multiple files are provided, by default they '
                             'will be concatenated at the end. using this flag'
                             ' will prevent concatenation')

    args = parser.parse_args()

    video, osd, srt = video_osd_srt_parser(args)

    png_folders = [default_output_path(x) for x in video]
    video_outputs = [f"{x}_osd.mp4" for x in png_folders]

    if not args.no_concat and not args.output_file and len(video) > 1:
        # if we are concatenating, we will need an output_path
        raise ValueError('Multiple videos provided. Please provide '
                         '--output-path')

    for video, osd, srt, png_folder in zip(video, osd, srt, png_folders):
        generator_config = OsdGenConfig(
            video_path=video,
            osd_path=osd,
            srt_path=srt,
            font_path=args.font_path,
            output_path=png_folder,
            offset_top=args.offset_top,
            offset_left=args.offset_left,
            osd_zoom=args.osd_zoom,
            render_upscale=args.render_upscale,
            include_srt=args.include_srt,
            hide_sensitive_osd=args.hide_sensitive_osd,
            use_hw=not args.no_hw_accel,
            fast_srt=args.fast_srt
        )

        gen = OsdGenerator(generator_config)
        gen.main()
        if not args.no_video:
            try:
                gen.render()
            finally:
                # will always clean-up PNGs, if flag is specified
                if args.remove_png:
                    shutil.rmtree(png_folder)

    if not args.no_concat and len(video_outputs) > 1:
        Utils.concatenate_output_files(
            video_outputs,
            args.output_path
        )
        for file in video_outputs:
            os.remove(file)
