# tellmemore
An AI-automated YouTube channel pipeline

## Setup

Install python dependencies
```
pip install -r requirements.txt
```
Alternatively, use virtualenv (recommended).

Copy `.env.example` to `.env` and configure your setup.

Install additional Software
```
apt install ffmpeg imagemagick firefox
```

## Howto

### (1) Generate Next Episode Ideas for your podcast

`python ideagenerator.py` can be used to search for the potential next episode for your podcast.
It will traverse `ytplaylists.json` and scan `database.json` and each `metadata.json` in your OUTPUT_FOLDER
for the used wikipedia article. It will use the list of URLs and the short_description in your `ytplaylist.json`
to ask for the next episode and return the wiki URL as podcast source. This URL will be automatically added to
the list in `database.json`, so you can simply run step (2).

### (2) Generate Podcast sound file from Wikipedia Article

`python podcastgenerator.py` reads the `database.json` file as pipeline.
All items are tranversed and if the item does not have a `folder` defined, the script tries to create the podcast.
For that, a chrome session is spun up with selenium webdriver, and creates a new notebook in notebookLM,
adds the wikipedia article as source and provides podcast prompt until it eventually generates a podcast.
This podcast is then downloaded and scanning the DOWNLOADS_FOLDER - when done it creates a subfolder in OUTPUT_FOLDER
and moves the podcast.wav and adds the metadata.json

database.json
```
{ "list":[
    {
        "category": "The Life Of",
        "title": "Taylor Swift"
    }
]}
```

### (3) Create and publish YouTube Video from audio file

`python podcast2video.py` scans for subfolders in your `OUTPUT_FOLDER`.
In your subfolder, there is usually a `metadata.json` file.
This contains at least `category` and `wiki_title` (can be generated when `podcastgenerator.py` creates the podcast sound file).
When traversing the different subfolders, it fills yt metadata with Gen AI and generates thumbnails in JPG format.
After all is generated, it uses ffmpeg to sitch the audio together with the thumbnails as slide show, creating a video.mp4.
This video.mp4 is then uploaded to YouTube and scheduled/configured how it is configured in `ytplaylists.json`.