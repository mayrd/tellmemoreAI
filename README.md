# tellmemore
An AI-automated YouTube channel pipeline

## Setup

Install python dependencies
```
pip install -r requirements.txt
```

Put following in your `.env` file
```
# general
OUTPUT_FOLDER=<FOLDER TO OUTPUT YOUR PODCAST, METADATA, IMAGES AND VIDEO>

# chrome
CHROME_PROFILE_FOLDER = <FOLDER OF YOUR CHROME PROFILE FOR SELENIUM>
CHROME_DOWNLOAD_FOLDER = <DOWNLOAD FOLDER WHICH IS SCANNED FOR PODCAST WAVEFILE>

# openai
OPENAI_API_KEY=<YOUR OPENAI API KEY>
OPENAI_TEXT_MODEL=<YOUR PREFERRED TEXT MODEL e.g. "gpt-3.5-turbo">
OPENAI_IMAGE_MODEL=<YOUR PREFERRED IMAGE MODEL e.g. "dall-e-3">

#youtube
YT_CLIENT_SECRETS=<PATH TO YOUR client_secrets.json>
```

## Howto

### Generate Podcast sound file from Wikipedia Article

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
        "category": "Disaster",
        "title": "Assassination of John F. Kennedy"
    }
]}
```

### Create YouTube Video from sound file

`python podcast2video.py` scans for subfolders in your `OUTPUT_FOLDER`.
In your subfolder, there is usually a `metadata.json` file.
This contains at least `category` and `wiki_title` (can be generated when `podcastgenerator.py` creates the podcast sound file).
When traversing the different subfolders, it fills yt metadata with Gen AI and generates thumbnails in JPG format.
After all is generated, it uses ffmpeg to sitch the audio together with the thumbnails as slide show, creating a video.mp4.
This video.mp4 is then uploaded to YouTube.