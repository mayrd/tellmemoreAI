#!/bin/python3
# Takes playlists and wiki articles used to find new ideas are return as JSON

import os
import datetime
# own modules
import genai
import wiki
import yt
import media
import utils
import dotenv

dotenv.load_dotenv()

def gather_wiki_urls(category) -> list:
    # take the ones from metadata.json in output folder
    # (TODO)append the ones from database.json which are queued
    urls = []
    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        try:
            #check if there is a metadata.json
            md_file = os.path.join(folder, "metadata.json")
            if os.path.exists(md_file):
                md = utils.fromFile(md_file)
                if md['category'] == category:
                    continue
                if 'pageid' in md:
                    page = wiki.get_page_by_id(md['pageid'])
                else:
                    page = wiki.get_page_by_title(md['wiki_title'])
                
                urls.append(page.url)
        except Exception as e:
            print(e)
    return urls

def gen_next_video_url(category, description, used_urls):
    response = genai.gemini(
        f"We created podcast called \"{category}\". {description} "
        f"Can you find one english wikipedia article which could be the base for the next episode of the podcast? "
        f"Please only reply with one url to the english wikipedia article. "
        f"These articles already have been used: " + " ".join(used_urls)
    ).strip()
    return response

if __name__ == "__main__":
    if not os.path.isfile("ytplaylists.json"):
        print("no ytplaylists.json, so no playlist to traverse")
        exit(1)

    playlists = utils.fromFile("ytplaylists.json")
    for playlist in playlists["list"]:
        urls_used = gather_wiki_urls(playlist["title"])
        print(playlist["title"])
        print(gen_next_video_url(playlist["title"], playlist["short_description"], urls_used))
