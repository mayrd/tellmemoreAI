#!/bin/python3

import subprocess
import os


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