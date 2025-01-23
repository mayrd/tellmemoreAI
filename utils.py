#!/bin/python3

import re
import os
import json
import requests


def download_file(url, filename):
  response = requests.get(url, stream=True)
  response.raise_for_status()
  with open(filename, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
      if not chunk:
        break
      f.write(chunk)


def get_subfolders(folder_path: str) -> list[str]:
  subfolders = []
  for root, dirs, files in os.walk(folder_path):
    for dir in dirs:
      subfolders.append(os.path.join(root, dir))
  return subfolders
  

def create_folder(folder_path: str) -> None:
  if not os.path.exists(folder_path):
    os.makedirs(folder_path)


def build_folder_name(topic: str) -> str:
  string = topic.lower()
  string = re.sub(r'\s+', '', string)
  string = re.sub(r'\([^()]*\)', '', string)
  return os.path.join(os.getenv("OUTPUT_FOLDER"), string)


def fromJSON(json: str) -> dict:
  return json.loads(json)

def fromFile(filename: str) -> dict:
  with open(filename, 'r') as f:
    return json.load(f)

def toJSON(md: dict) -> str:
  return json.dumps(md, ensure_ascii=False, indent=4)

def toFile(md: dict, filename: str) -> None:
  with open(filename, 'w', encoding='utf-8') as f:
    json.dump(md, f, ensure_ascii=False, indent=4)


## methods for ytplaylists.json

def get_ytplaylists():
  if not os.path.isfile("ytplaylists.json"):
    print("no ytplaylists.json")
    return None

  return utils.fromFile("ytplaylists.json")  

def get_ytplaylist(category: str):
  playlists = get_ytplaylists()
  for item in playlists["list"]:
    if item["title"] == category:
      return item
  return None