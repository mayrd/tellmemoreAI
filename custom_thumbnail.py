import podcast2video
import media
import yt
import os
import utils


if __name__ == "__main__":
    # add video ids where the thumbnail should be regenerated
    video_list = []

    playlists = utils.get_ytplaylists()
    for video_id in video_list:

        for playlist in playlists:
            if yt.is_video_in_playlist(playlist["playlistId"], video_id):
                category = playlist["title"]

        md = yt.get_video_metadata(video_id)
        snippet = md.get("snippet", {})
        title = snippet.get("title", "N/A")
        description = snippet.get("description", "N/A")
        short_title = podcast2video.gen_short_title(title)

        if title == "N/A":
            print("could not get metadata for {video_id} abort.")
            continue

        print(f"generate new thumbnail for {video_id} - {short_title} ({category})")

        podcast2video.gen_thumbnail(
            description,
            short_title,
            category,
            video_id+".jpg"
        )
        yt.set_thumbnail(video_id, video_id+".jpg")
        os.remove(video_id+".jpg")
        print(f"\t{video_id} done")