#!/bin/python3

import subprocess
import os
from PIL import Image, ImageDraw, ImageFont

def ffmpeg(command_args: list[str]) -> bool:
    try:
        command = ["ffmpeg"] + command_args
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return False


def convert(input_file: str, output_file: str) -> None:
    try:
        command = ["convert", input_file, output_file]
        subprocess.run(command, check=True)
        os.remove(input_file)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def image_add_text(
    image_file:str, text: str,
    font_file: str, font_size: int,
    pos_x: int, pos_y: int,
    text_color = (255, 255, 255),
    border_color = (0, 0, 0,), border_width: int = 0
    ) -> bool:
    img = Image.open(image_file)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_file, font_size)

    for offset_border_x in range(-border_width, border_width + 1):
        for offset_border_y in range(-border_width, border_width + 1):
            if offset_border_x == 0 and offset_border_y == 0:
                continue
            d.text((pos_x + offset_border_x, pos_y + offset_border_y), text, font=font, fill=border_color)

    d.text((pos_x, pos_y), text, fill=text_color, font=font)
    img.save(image_file)
    return True

def image_add_text_centered(
    image_file: str, text:str,
    font_file: str, font_size: int,
    text_color = (255, 255, 255),
    border_color = (0, 0, 0,), border_width: int = 0,
    offset_x: int = 0, offset_y: int = 0
    ) -> bool:
    img = Image.open(image_file)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_file, font_size)

    # Calculate total text size for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (img.width - text_width) / 2
    y = (img.height - text_height) / 2

    for offset_border_x in range(-border_width, border_width + 1):
        for offset_border_y in range(-border_width, border_width + 1):
            if offset_border_x == 0 and offset_border_y == 0:
                continue
            draw.text((x + offset_border_x + offset_x, y + offset_border_y + offset_y), text, font=font, fill=border_color)

    draw.text((x + offset_x, y + offset_y), text, font=font, fill=text_color)
    img.save(image_file)
    return True


def podcast2video(podcast_audio: str, images: str, videofile: str) -> bool:
    return ffmpeg([
        "-y",
        "-hide_banner",
        "-loglevel", "quiet",
        "-framerate", "1/15",
        "-pattern_type", "glob",
        "-i", images,
        "-i", podcast_audio,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        videofile
    ])

def playlist2stream(videos: list[str], stream_key: str):
    return ffmpeg([
        #"-re","-f","concat","-safe","0",
        "-i",videos[1],
        #"-c:v","copy","-c:a","copy",
        "-c:v","libx264","-preset","veryfast","-b:v","3000k","-maxrate","3000k","-bufsize","6000k",
        "-vf","format=yuv420p,scale=1280:720","-r","30","-g","50",
        "-c:a","aac","-b:a","128k","-ar","44100",
        "-hide_banner",
        #"-loglevel", "quiet",
        "-f","flv", f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    ])