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
    return genai.genai_text(
        f"We created a suspenseful podcast about the happenings. "
        f"Can you propose a great YouTube video title for the podcast? "
        f"Only respond with the proposed title and add some hashtags in the title. "
        f"The title should not have more than 100 characters. "
        f"This is the article content the podcast is based on: {wiki_article}"
    ).replace("\"", "")

def gen_short_title(wiki_article: str) -> str:
        return genai.genai_text(
        f"We need a short title for: {wiki_article}"
    ).replace("\"", "")

def gen_yt_description(wiki_article: str) -> str:
    return genai.genai_text(
        f"We created a suspenseful podcast about the happenings. "
        f"Can you propose a great YouTube video description for the podcast? "
        f"The description should not have more than 5000 characters. "
        f"This is the article content the podcast is based on: {wiki_article}"
    )

def gen_yt_tags(wiki_article: str) -> list[str]:
    response = genai.genai_text(
        f"We created a suspenseful podcast about the happenings. "
        f"Can you propose a great YouTube tags for the podcast (comma-separated)? "
        f"This is the article content the podcast is based on: {wiki_article}"
    )
    return [word.strip() for word in response.split(",")]

def gen_thumbnail(yt_description: str, title: str, subtitle: str, filename: str) -> None:
    url = genai.genai_image(
        f"We created a suspenseful podcast about the happenings and this is the description. "
        f"Can you generate a thumbnail supporting the podcast? "
        f"Add \"{title}\" as big text on the thumbnail and also add \"{subtitle}\" as text on the thumbnail. "
        f"This is the description what the podcast is about: {yt_description}"
        )
    utils.download_file(url, filename + ".webp")
    media.convert(filename + ".webp", filename)


def podcast2video(folder_name: str) -> bool:
    print(f"checking {folder_name}")
    # read metadata file, and abort if not exists
    md_file = os.path.join(folder_name, "metadata.json")
    if not os.path.isfile(md_file):
        print(f"{md_file} not found - skipping.")
        return False

    md =  utils.fromFile(md_file)
    if "yt_video_id" in md and len(md["yt_video_id"])>=11:
        print(f"video already published as " + md["yt_video_id"])
        return True
    
    print(md)

    article = wiki.fetch_wiki_article(md["wiki_title"])
    if len(article)  > 60000:
        article = wiki.get_wiki_summary(md["wiki_title"])

    # define yt metadata
    if "short_title" not in md:
        md["short_title"] = gen_short_title(article)
    if "yt_title" not in md:
        md["yt_title"] = gen_yt_title(article)
    if "yt_description" not in md: 
        md["yt_description"] = gen_yt_description(article)
    if "yt_tags" not in md:
        md["yt_tags"] = gen_yt_tags(article)

    utils.toFile(md, md_file)

    # create thumbnail images
    for i in range(1,4):
        img_file = os.path.join(folder_name, f"img{i}.jpg")
        if not os.path.isfile(img_file):
            print(f"create {img_file}")
            gen_thumbnail(md["yt_description"], md["category"], md["short_title"], img_file)

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

    print("upload")
    md["yt_video_id"] = yt.upload_video(video_file, md["yt_title"], md["yt_description"], md["yt_tags"])

    print(utils.toJSON(md))
    utils.toFile(md, md_file)
    
    print("Done")
    return True


# main
if __name__ == "__main__":
    # go through the different folders in OUTPUT_FOLDER
    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        podcast2video(folder)