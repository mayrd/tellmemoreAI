#!/bin/python3
# needs to run on linux

import os
import shutil
import sys
import datetime
import time
# own modules
import genai
import wiki
import yt
import media
import utils

def gen_yt_title(wiki_article: str) -> str:
    response = genai.genai_text(
        f"We created a podcast about the happenings. "
        f"Can you propose a great YouTube video title for the podcast? "
        f"Only respond with the proposed title and add some hashtags in the title. "
        f"The title should not have more than 100 characters. "
        f"This is the article content the podcast is based on: {wiki_article}"
    ).replace("\"", "")
    if len(response) < 100:
        return response
    return gen_yt_title(wiki_article)

def gen_short_title(wiki_article: str) -> str:
        return genai.genai_text(
            f"We need a short title in 1-3 words. Keep as short as possible. "
            f"If it is about a person, reply only with the name of the person. "
            f"If it is about an object, reply only with the name for the object. "
            f"Do not add History, Journey, Evolution, Podcast, Story or similar in the title. "
            f"Reply only with the short title for: {wiki_article}"
    ).replace("\"", "").strip()

def gen_yt_description(wiki_article: str) -> str:
    response = genai.genai_text(
        f"We created a podcast about the happenings. "
        f"Can you propose a great YouTube video description for the podcast? "
        f"The description should not have more than 5000 characters. "
        f"Only reply with the description. "
        f"This is the article content the podcast is based on: {wiki_article}"
    )
    if len(response) < 5000:
        return response
    return gen_yt_title(wiki_article)

def gen_yt_tags(wiki_article: str) -> list[str]:
    response = genai.genai_text(
        f"We created a podcast about the happenings. "
        f"Can you propose a great set of 20 YouTube tags for the podcast (comma-separated)? "
        f"Only reply with the tags. "
        f"This is the article content the podcast is based on: {wiki_article}"
    )
    arr = [word.strip() for word in response.split(",")]
    if len(arr) > 20:
        arr = arr[:20]
    return arr

def gen_thumbnail_prompt(short_title: str, yt_description: str, style: str, podcast_color: str) -> str:
    prompt = (
        f"Create an image for a podcast episode in {style} style. "
        f"Use the color {podcast_color}, but you can still use other colors to emphasize objects. "
        f"Do not write text on the image. "
        f"The image should be full size, no blanks or borders. "
        #f"Add \"{title}\" as large text and also add \"{category}\". " # does not work, write mechanical instead
        f"The episode has the title \"{short_title}\". "
        f"here is the description: {yt_description}"
    )
    expanded_thumbnail_prompt = genai.expand_image_prompt(prompt)
    return expanded_thumbnail_prompt

def add_text_to_thumbnail(image_file: str, short_title: str, category: str) -> None:
    playlist = utils.get_ytplaylist(category)
    if category == "True Crime":
        category = "True Crime & Disasters"

    if len(short_title)>=19:
        last_a_index = short_title.rfind(" ")
        if last_a_index != -1:
            short_title = short_title[:last_a_index] + "\n" + short_title[last_a_index + 1:]

    media.image_add_text(
        image_file, category,
        os.path.join("fonts", playlist['font_file']), playlist['font_size_title'],
        10, 0,
        border_width=5
    )
    media.image_add_text_centered(
        image_file, short_title,
        os.path.join("fonts", playlist['font_file']), playlist['font_size_episode'],
        offset_y=playlist['font_size_episode_offset_y'],
        border_width=5
    )
    
def gen_thumbnail(yt_description: str, short_title: str, category: str, filename: str, add_text: bool = True) -> None:
    playlist = utils.get_ytplaylist(category)
    prompt = gen_thumbnail_prompt(short_title, yt_description, playlist["style"], playlist["color"])
    if "GENERATE_IMAGE_SYSTEM_OVERWRITE" in playlist:
        print("GENERATE_IMAGE_SYSTEM_OVERWRITE to openai")
        image = genai.openai_image(prompt)
    else:
        image = genai.genai_image(prompt)

    if add_text is True:
        add_text_to_thumbnail(image, short_title, category)

    shutil.move(image, filename)


def gen_metadata(md: dict, article: str) -> dict:
    if "short_title" not in md:
        md["short_title"] = gen_short_title(article)
    if "yt_title" not in md:
        md["yt_title"] = gen_yt_title(article)
    if "yt_description" not in md: 
        md["yt_description"] = gen_yt_description(article)
    if "yt_tags" not in md:
        md["yt_tags"] = gen_yt_tags(article)

    return md

def get_article(md: dict)-> str:
    if "pageid" in md and md["pageid"] is not None:
        article = wiki.fetch_wiki_article_by_id(md["pageid"])
        if len(article) > 60000:
            page = wiki.get_page_by_id(md["pageid"])
            article = page.summary
    else:
        article = wiki.fetch_wiki_article(md["wiki_title"])
        if len(article)  > 60000:
            article = wiki.get_wiki_summary(md["wiki_title"])

    return article

def gen_thumbnails(md: dict, folder_name: str)-> str:
    for i in range(1, 2):
        img_file = os.path.join(folder_name, f"img{i}.jpg")
        if not os.path.isfile(img_file):
            print(f"create {img_file}")
            gen_thumbnail(md["yt_description"], md["short_title"], md["category"], img_file)


def add_to_playlist(videoId: str, category: str) -> bool:
    playlist = utils.get_ytplaylist(category)
    try:
        yt.add_video_to_playlist(playlist["playlistId"], videoId)
        return True
    except Exception as e:
        print("could not add to playlists: "+str(e))

    return False


def schedule(video_id: str, category: str) -> datetime.datetime:
    playlist = utils.get_ytplaylist(category)
    try:
        latest_pub = yt.get_latest_scheduled_publish_time(playlist["playlistId"])
        if latest_pub is None:
            latest_pub = datetime.datetime.now()
        next_pub = latest_pub + datetime.timedelta(days=1)
        yt.schedule_video(video_id, next_pub)
        return next_pub
    except Exception as e:
        print("could not schedule video: "+str(e))

    return None


def print_last_pubs():
    print("\nSchedules:")
    playlists = utils.get_ytplaylists()
    for item in playlists:
        latest_pub = yt.get_latest_scheduled_publish_time(item["playlistId"])
        if latest_pub is None:
            print(item["title"] + ": nothing scheduled")
        else:
            print(item["title"] + ": "+ latest_pub.isoformat())


def podcast2video(folder_name: str, pause_for_review: bool = False) -> bool:
    print(f"checking {folder_name}")
    md_file = os.path.join(folder_name, "metadata.json")
    if not os.path.isfile(md_file):
        print(f"  {md_file} not found - skipping.")
        return False

    md =  utils.fromFile(md_file)
    if "yt_video_id" in md and md["yt_video_id"] is not None and len(md["yt_video_id"])>=11:
        print(f"  video already published as " + md["yt_video_id"])
        return True

    article = get_article(md)
    md = gen_metadata(md, article)
    utils.toFile(md, md_file)

    gen_thumbnails(md, folder_name)

    # check for podcast.wav
    podcast_file = os.path.join(folder_name, "podcast.wav")
    if not os.path.isfile(podcast_file):
        print(f"{podcast_file} not found.")
        return False

    # create video
    video_file = os.path.join(folder_name, "video.mp4")
    if not os.path.isfile(video_file):
        print(f"create {video_file}")
        media.podcast2video(podcast_file, os.path.join(folder_name, "img*.jpg"), video_file)

    if pause_for_review:
        print("Pause for review, before uploading. Hit Enter to continue. ")
        input()

    md["yt_video_id"] = yt.upload_video(video_file, md["yt_title"], md["yt_description"], md["yt_tags"])
    if md["yt_video_id"]:
        print(f"  uploaded to YT as " + md["yt_video_id"])
        yt.set_thumbnail(md["yt_video_id"], os.path.join(folder_name, "img1.jpg"))
        add_to_playlist(md["yt_video_id"], md["category"])
        pub_time = schedule(md["yt_video_id"], md["category"])
        if pub_time is not None:
            md["pub_time"] = pub_time.isoformat()
            print(f"  scheduled for " + pub_time.isoformat())
    else:
        print(f"  upload failed. No video Id given")

    utils.toFile(md, md_file)
    return True


if __name__ == "__main__":
    PAUSE_FOR_REVIEW = False
    if len(sys.argv)>1 and sys.argv[1] == "review":
        PAUSE_FOR_REVIEW = True

    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        if folder.startswith(os.path.join(os.getenv("OUTPUT_FOLDER"),"__")):
            continue
        try:
            podcast2video(folder, PAUSE_FOR_REVIEW)
        except Exception as e:
            print(e)

    # print pipeline for last publications
    print_last_pubs()