import os
from argparse import ArgumentParser

from processor import OsdGenConfig, OsdGenerator


def implicit_path(args, ext):
    """
    Attempts to find a path for the OSD and SRT files implicitly
    file_path: path to the video (mp4) file
    ext: file type suffix (e.g. osd or srt)
    """
    if ext not in {'osd', 'srt'}:
        raise ValueError('Invalid file type, only srt or osd')
    if getattr(args, f'{ext}_path') is None:
        folder, _ = os.path.splitext(args.video_path)
        return f"{folder}.{ext}"
    else:
        return args[f'{ext}_path']


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('--video-path', help='Path to the video file',
                        required=True)
    parser.add_argument('--osd-path', help='Path to the OSD file. If none '
                                           'specified, it will look in the same'
                                           ' directory as the video path')
    parser.add_argument('--srt-path', help='Path to SRT file. If none '
                                           'specified, it will look in the same'
                                           ' directory as the video path')
    parser.add_argument('--font-path', required=True,
                        help='Path to font file - e.g (INAV_36.png)')
    parser.add_argument('--output-path', default=os.getcwd(),
                        help='Output path for PNG folder and finished video')
    parser.add_argument('--no-video', default=False,
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
    parser.add_argument('--use-hw', action='store_true', default=False,
                        help='Use Hardware Acceleration for Encoding')
    parser.add_argument('--fast-srt', action='store_true', default=False,
                        help='')

    args = parser.parse_args()

    generator_config = OsdGenConfig(
        video_path=args.video_path,
        osd_path=implicit_path(args, 'osd'),
        srt_path=implicit_path(args, 'srt'),
        font_path=args.font_path,
        output_path=args.output_path,
        offset_top=args.offset_top,
        offset_left=args.offset_left,
        osd_zoom=args.osd_zoom,
        render_upscale=args.render_upscale,
        include_srt=args.include_srt,
        hide_sensitive_osd=args.hide_sensitive_osd,
        use_hw=args.use_hw,
        fast_srt=args.fast_srt
    )

    gen = OsdGenerator(generator_config)
    gen.main()
    if not args.no_video:
        gen.render()
