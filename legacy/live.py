# Gets one playlist and livestreams it on youtube

import os
import utils
import media
import dotenv
import sys

dotenv.load_dotenv()


def _gather_videos_from_md_json(category: str) -> list:
    # take the ones from metadata.json in output folder
    videos = []
    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        try:
            #check if there is a metadata.json
            md_file = os.path.join(folder, "metadata.json")
            if os.path.exists(md_file):
                md = utils.fromFile(md_file)
                if md['category'] != category:
                    continue

                video_file = os.path.join(folder, "video.mp4")
                if os.path.exists(video_file):
                    videos.append(video_file)
        except Exception as e:
            print(e)

    return videos

def gen_playlist(category: str) -> list[str]:
    return _gather_videos_from_md_json(category)


def stream(category: str, stream_key: str):
    videos = gen_playlist(category)
    media.playlist2stream(videos, stream_key)


if __name__ == "__main__":
    if len(sys.argv)!=3:
        print("need two args: Category and Stream_key")
        exit(1)
    stream(sys.argv[1], sys.argv[2])