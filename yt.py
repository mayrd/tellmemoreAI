#!/bin/python3
#from: https://developers.google.com/youtube/v3/guides/uploading_a_video

import httplib2
import http.client as httplib
import os
import random
import sys
import time
import dotenv
import datetime
import googleapiclient

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

dotenv.load_dotenv()

httplib2.RETRIES = 1
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

CLIENT_SECRETS_FILE = os.getenv("YT_CLIENT_SECRETS")
YOUTUBE_SCOPES = [
  "https://www.googleapis.com/auth/youtube.force-ssl",
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.readonly"
  ]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

class Options:
  pass

def get_authenticated_service():
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    scope=YOUTUBE_SCOPES,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("tellmemoreai-oauth2.json")
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    args = Options()
    args.logging_level = "WARNING"
    args.noauth_local_webserver = True
    credentials = run_flow(flow, storage, args)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def initialize_upload(youtube, options)-> str:
  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=options.tags
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  insert_request = youtube.videos().insert(
    part=",".join(body.keys()),
    body=body,
    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )
  return resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request)-> str:
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      status, response = insert_request.next_chunk()
      if response is not None:
        if 'id' in response:
          return response['id']
        else:
          exit("The upload failed with an unexpected response: %s" % response)
    except HttpError as e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                             e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS as e:
      error = "A retriable error occurred: %s" % e

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print("Sleeping %f seconds and then retrying..." % sleep_seconds)
      time.sleep(sleep_seconds)


def upload_video(video_file: str, title: str, description: str, tags: list[str]) -> str:
  options = Options()
  options.file = video_file
  options.title = title
  options.description = description
  options.tags = tags
  options.privacyStatus = "private"
  youtube = get_authenticated_service()
  try:
    return initialize_upload(youtube, options)
  except HttpError as e:
    print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
  return None


def set_thumbnail(video_id: str, thumbnail_file: str) -> bool:
  youtube = get_authenticated_service()
  try:
    with open(thumbnail_file, 'rb') as f:
      response = youtube.thumbnails().set(
          videoId=video_id,
          media_body=f,
          media_mime_type='image/jpeg'
      ).execute()
  except HttpError as e:
    print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
  return False


def is_video_in_playlist(playlist_id: str, video_id: str) -> bool:
  """Checks if a video is already in a playlist."""
  try:
    youtube = get_authenticated_service()
    request = youtube.playlistItems().list(
      part="snippet",
      playlistId=playlist_id,
      videoId=video_id
    )
    response = request.execute()
    return len(response.get("items", [])) > 0
  except googleapiclient.errors.HttpError as e:
    print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
    return False


def add_video_to_playlist(playlist_id, video_id) -> bool:
  """Adds a video to a playlist if it's not already there."""
  if not is_video_in_playlist(playlist_id, video_id):
    try:
      youtube = get_authenticated_service()
      request = youtube.playlistItems().insert(
        part="snippet",
        body={
          "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": video_id,
            }
          }
        }
      )
      request.execute()
      return True
    except googleapiclient.errors.HttpError as e:
      print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
      return False
  else:
    print(f"Video {video_id} is already in playlist {playlist_id}")
    return True


def get_latest_scheduled_publish_time(playlist_id: str) -> datetime.datetime:
  """Retrieves the latest scheduled publish time for videos in a YouTube playlist (handles pagination)."""
  try:
    youtube = get_authenticated_service()        
    scheduled_times = []
    next_page_token = None

    while True:  # Loop to handle pagination
      request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50,
        pageToken=next_page_token
      )
      response = request.execute()

      for item in response['items']:
        video_id = item['contentDetails']['videoId']
        video_request = youtube.videos().list(
          part="status",
          id=video_id
        )
        video_response = video_request.execute()
        video = video_response.get('items', [])
        if video:
          publish_at = video[0]['status'].get('publishAt')
          if publish_at:
            scheduled_times.append(publish_at)

      next_page_token = response.get('nextPageToken')
      if not next_page_token:
        break

    if scheduled_times:
      latest_scheduled_time = max(scheduled_times)
      return datetime.datetime.fromisoformat(latest_scheduled_time)
    else:
      return None

  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def schedule_video(video_id: str, publish_at: datetime.datetime) -> bool:
  try:
    youtube = get_authenticated_service()
    request = youtube.videos().update(
      part="status",
      body={
        "id": video_id,
        "status": {
          "publishAt": publish_at.isoformat().replace("+00:00","Z"),
          "privacyStatus": "private"
        }
      }
    )
    response = request.execute()
    return True
  except Exception as e:
    print(f"An error occurred: {e}")
    return False