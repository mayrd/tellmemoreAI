#!/bin/python3
# needs to run on linux

import os
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
        f"We need a short title for: {wiki_article}"
    ).replace("\"", "")

def gen_yt_description(wiki_article: str) -> str:
    response = genai.genai_text(
        f"We created a podcast about the happenings. "
        f"Can you propose a great YouTube video description for the podcast? "
        f"The description should not have more than 5000 characters. "
        f"This is the article content the podcast is based on: {wiki_article}"
    )
    if len(response) < 5000:
        return response
    return gen_yt_title(wiki_article)

def gen_yt_tags(wiki_article: str) -> list[str]:
    response = genai.genai_text(
        f"We created a podcast about the happenings. "
        f"Can you propose a great set of 20 YouTube tags for the podcast (comma-separated)? "
        f"This is the article content the podcast is based on: {wiki_article}"
    )
    arr = [word.strip() for word in response.split(",")]
    if len(arr) > 20:
        arr = arr[:20]
    return arr
    
def gen_thumbnail(yt_description: str, title: str, subtitle: str, filename: str) -> None:
    url = genai.genai_image(
        f"We created a podcast about the happenings and this is the description. "
        f"Can you generate a thumbnail supporting the podcast? "
        f"Add \"{title}\" as big text on the thumbnail and also add \"{subtitle}\" as text on the thumbnail. "
        f"This is the description what the podcast is about: {yt_description}"
        )
    utils.download_file(url, filename + ".webp")
    media.convert(filename + ".webp", filename)


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
    for i in range(1,4):
        img_file = os.path.join(folder_name, f"img{i}.jpg")
        if not os.path.isfile(img_file):
            print(f"create {img_file}")
            gen_thumbnail(md["yt_description"], md["category"], md["short_title"], img_file)


def add_to_playlist(videoId: str, category: str) -> bool:
    if not os.path.isfile("ytplaylists.json"):
        print("no ytplaylists.json, so no playlist to add item to")
        return False

    playlists = utils.fromFile("ytplaylists.json")
    for item in playlists["list"]:
        if item["title"] == category:
            try:
                yt.add_video_to_playlist(item["playlistid"], videoId)
                print("added to playlist")
                return True
            except Exception as e:
                print("could not add to playlists: "+str(e))
    return False

def podcast2video(folder_name: str) -> bool:
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

    md["yt_video_id"] = yt.upload_video(video_file, md["yt_title"], md["yt_description"], md["yt_tags"])
    if md["yt_video_id"]:
        print(f"  uploaded to YT as " + md["yt_video_id"])
        add_to_playlist(md["yt_video_id"], md["category"])
    else:
        print(f"  upload failed. No video Id given")

    utils.toFile(md, md_file)
    return True


if __name__ == "__main__":
    # go through the different folders in OUTPUT_FOLDER
    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        if folder.startswith(os.path.join(os.getenv("OUTPUT_FOLDER"),"__")):
            continue
        try:
            podcast2video(folder)
        except Exception as e:
            print(e)