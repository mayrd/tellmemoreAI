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

def gather_wiki_urls(category: str) -> list:
    return list(set(_gather_wiki_urls_from_md_json(category) + _gather_wiki_urls_from_database_json(category)))

def _gather_wiki_urls_from_md_json(category: str) -> list:
    # take the ones from metadata.json in output folder
    urls = []
    folders = utils.get_subfolders(os.getenv("OUTPUT_FOLDER"))
    for folder in folders:
        try:
            #check if there is a metadata.json
            md_file = os.path.join(folder, "metadata.json")
            if os.path.exists(md_file):
                md = utils.fromFile(md_file)
                if md['category'] != category:
                    continue
                if 'pageid' in md:
                    page = wiki.get_page_by_id(md['pageid'])
                else:
                    page = wiki.get_page_by_title(md['wiki_title'])
                
                urls.append(page.url)
        except Exception as e:
            print(e)
    return urls

def _gather_wiki_urls_from_database_json(category: str):
    # read urls from database.json
    urls = []
    db = utils.fromFile("database.json")
    for item in db["list"]:
        if item['category'] != category:
            continue
        urls.append(item['url'])
    return urls

def append_to_database_json(category: str, title: str, url: str):
    db = utils.fromFile("database.json")
    db["list"].append({
        "category": category,
        "title": title,
        "url": url
    })
    utils.toFile(db, "database.json")


def gen_next_video_url(category: str, description: str, used_urls: list) -> str:
    response = genai.gemini(
        f"We created podcast called \"{category}\". {description} "
        f"Can you find one english wikipedia article which could be the base for the next episode of the podcast? "
        f"Please only reply with one url to the english wikipedia article. "
        f"These articles already have been used: " + " ".join(used_urls)
    ).strip()
    return response


def gen_for_playlist(playlist_title: str, qty: int = 1) -> bool:
    urls_used = gather_wiki_urls(playlist_title)
    for i in range(qty):
        try:
            next_url = gen_next_video_url(playlist_title, playlist["short_description"], urls_used)
            print(next_url)

            if next_url in urls_used:
                print("\talready listed.")
                continue

            page_id = wiki.get_page_id(next_url)
            if page_id is None:
                print("\twiki page not found.")
                continue

            append_to_database_json(playlist_title, next_url.replace("https://en.wikipedia.org/wiki/",""), next_url)
            urls_used.append(next_url)
            return True
        except Exception as ex:
            print(f"ERROR: {ex}")
            return False

if __name__ == "__main__":
    playlists = utils.get_ytplaylists()
    for playlist in playlists:
        if playlist["active"] is True:
            print(playlist["title"])
            gen_for_playlist(playlist["title"])