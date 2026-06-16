#!/usr/bin/env python3
"""
youtube_analytics.py — YouTube Analytics API v2 for Tell Me More AI! channel.

Uses the YouTube Analytics API (not Data API) to pull real performance metrics
for each Short, then generates a structured report for the weekly optimizer.

Usage:
    python3 youtube_analytics.py --report weekly
    python3 youtube_analytics.py --report video --video-id X_agwfzn-8I
    python3 youtube_analytics.py --report channel
    python3 youtube_analytics.py --report retention --video-id X_agwfzn-8I

Requirements:
    - google-api-python-client, google-auth (in /opt/data/.venvs/youtube-analytics)
    - YouTube OAuth token with yt-analytics.readonly scope at /opt/data/youtube_token.json
    - google_client_secret.json at /opt/data/google_client_secret.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

VENV_PYTHON = "/opt/data/.venvs/youtube-analytics/bin/python3"
TOKEN_FILE = Path("/opt/data/youtube_token.json")
CLIENT_SECRET_FILE = Path("/opt/data/google_client_secret.json")
TOPICS_FILE = Path("/opt/data/youtube_shorts_topics.json")
REPORTS_DIR = Path("/opt/data/analytics_reports")
REPORTS_DIR.mkdir(exist_ok=True)


def load_credentials():
    """Load OAuth credentials from token file + client secret."""
    from google.oauth2.credentials import Credentials

    token_data = json.loads(TOKEN_FILE.read_text())
    secret = json.loads(CLIENT_SECRET_FILE.read_text())
    installed = secret.get("installed", secret.get("web", secret))

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
    )
    return creds


def build_service(creds):
    """Build the YouTube Analytics API service."""
    from googleapiclient.discovery import build
    return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def get_channel_id(creds):
    """Get the channel ID associated with the credentials."""
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    resp = yt.channels().list(part="id,snippet,statistics", mine=True).execute()
    if resp.get("items"):
        ch = resp["items"][0]
        return ch["id"], ch["snippet"]["title"], ch["statistics"]
    return None, None, None


def report_channel(args):
    """Get overall channel metrics."""
    creds = load_credentials()
    channel_id, channel_title, stats = get_channel_id(creds)

    if not channel_id:
        print("ERROR: Could not determine channel ID")
        return

    print(f"Channel: {channel_title} ({channel_id})")
    if stats:
        print(f"  Subscribers: {stats.get('subscriberCount', 'N/A')}")
        print(f"  Total views: {stats.get('viewCount', 'N/A')}")
        print(f"  Video count: {stats.get('videoCount', 'N/A')}")

    # Pull last 30 days of channel analytics
    ya = build_service(creds)
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    query = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched,subscribersGained,averageViewDuration,likes,comments,shares",
        "dimensions": "day",
        "sort": "day",
    }

    resp = ya.reports().query(**query).execute()

    print(f"\n=== Last 30 Days Channel Performance ===")
    print(f"{'Date':<12} {'Views':>8} {'MinWatch':>10} {'Subs+':>6} {'AvgDur':>8} {'Likes':>6} {'Comments':>9} {'Shares':>7}")

    total_views = 0
    total_minutes = 0
    total_subs = 0

    for row in resp.get("rows", []):
        date, views, mins, subs, avg_dur, likes, comments, shares = row
        total_views += int(views)
        total_minutes += float(mins)
        total_subs += int(subs)
        print(f"{date:<12} {int(views):>8,} {float(mins):>10.1f} {int(subs):>6} {float(avg_dur):>8.1f}s {int(likes):>6} {int(comments):>9} {int(shares):>7}")

    print(f"\n{'TOTAL':<12} {total_views:>8,} {total_minutes:>10.1f} {total_subs:>6}")
    print(f"\nReport period: {start_date} to {end_date}")

    # Save report
    report = {
        "type": "channel",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel_id,
        "channel_title": channel_title,
        "period": {"start": start_date, "end": end_date},
        "totals": {
            "views": total_views,
            "estimated_minutes_watched": round(total_minutes, 1),
            "subscribers_gained": total_subs,
        },
        "daily": [
            {
                "date": row[0], "views": int(row[1]), "minutes_watched": float(row[2]),
                "subscribers_gained": int(row[3]), "avg_view_duration_s": float(row[4]),
                "likes": int(row[5]), "comments": int(row[6]), "shares": int(row[7]),
            }
            for row in resp.get("rows", [])
        ],
    }

    out_file = REPORTS_DIR / f"channel_{end_date}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"\nSaved to {out_file}")


def report_video(args):
    """Get analytics for a specific video."""
    creds = load_credentials()
    ya = build_service(creds)

    # First get channel ID
    channel_id, channel_title, _ = get_channel_id(creds)
    if not channel_id:
        print("ERROR: Could not determine channel ID")
        return

    video_id = args.video_id
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Start from video publish date (or 30 days ago)
    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    # Core metrics
    query = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained,estimatedRevenue",
        "filters": f"video=={video_id}",
    }

    resp = ya.reports().query(**query).execute()

    print(f"=== Video Analytics: {video_id} ===")
    print(f"Channel: {channel_title}")

    if resp.get("rows"):
        row = resp["rows"][0]
        views, mins, avg_dur, likes, comments, shares, subs, revenue = row
        print(f"  Views: {int(views):,}")
        print(f"  Watch time: {float(mins):.1f} min")
        print(f"  Avg view duration: {float(avg_dur):.1f}s")
        print(f"  Likes: {int(likes):,}")
        print(f"  Comments: {int(comments):,}")
        print(f"  Shares: {int(shares):,}")
        print(f"  Subscribers gained: {int(subs):,}")
        print(f"  Est. revenue: €{float(revenue):.2f}")
    else:
        print("  No data available (video may be too new or have 0 views)")

    # Traffic sources
    print(f"\n--- Traffic Sources ---")
    tq = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "filters": f"video=={video_id}",
        "dimensions": "insightTrafficSourceType",
        "sort": "-views",
    }
    tresp = ya.reports().query(**tq).execute()
    for row in tresp.get("rows", []):
        source, tviews, tmins = row
        print(f"  {source:<30} {int(tviews):>6,} views  {float(tmins):>8.1f} min")

    # Save
    report = {
        "type": "video",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "channel_id": channel_id,
        "period": {"start": start_date, "end": end_date},
        "metrics": {
            "views": int(resp["rows"][0][0]) if resp.get("rows") else 0,
            "minutes_watched": float(resp["rows"][0][1]) if resp.get("rows") else 0,
            "avg_view_duration_s": float(resp["rows"][0][2]) if resp.get("rows") else 0,
            "likes": int(resp["rows"][0][3]) if resp.get("rows") else 0,
            "comments": int(resp["rows"][0][4]) if resp.get("rows") else 0,
            "shares": int(resp["rows"][0][5]) if resp.get("rows") else 0,
            "subscribers_gained": int(resp["rows"][0][6]) if resp.get("rows") else 0,
        },
        "traffic_sources": [
            {"source": row[0], "views": int(row[1]), "minutes_watched": float(row[2])}
            for row in tresp.get("rows", [])
        ],
    }
    out_file = REPORTS_DIR / f"video_{video_id}_{end_date}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"\nSaved to {out_file}")


def report_retention(args):
    """Get audience retention curve for a specific video."""
    creds = load_credentials()
    ya = build_service(creds)
    channel_id, _, _ = get_channel_id(creds)

    if not channel_id:
        print("ERROR: Could not determine channel ID")
        return

    video_id = args.video_id
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    # Retention data — elapsedVideoTimeRatio (0.0 to 1.0)
    query = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "audienceWatchRatio,relativeRetentionPerformance",
        "filters": f"video=={video_id}",
        "dimensions": "elapsedVideoTimeRatio",
        "sort": "elapsedVideoTimeRatio",
    }

    resp = ya.reports().query(**query).execute()

    print(f"=== Audience Retention: {video_id} ===")
    print(f"{'Progress':>10} {'Watch%':>10} {'Retention':>12}")
    print("-" * 35)

    retention_data = []
    for row in resp.get("rows", []):
        ratio, watch_ratio, rel_retention = row
        pct = float(ratio) * 100
        watch_pct = float(watch_ratio) * 100
        rel_ret = float(rel_retention) * 100 if rel_retention else 0
        retention_data.append({
            "progress_pct": round(pct, 1),
            "audience_watch_ratio": round(watch_pct, 1),
            "relative_retention": round(rel_ret, 1),
        })
        if pct % 10 == 0 or pct < 5:  # Print every 10% + first 5%
            print(f"{pct:>9.1f}% {watch_pct:>9.1f}% {rel_ret:>11.1f}%")

    if not retention_data:
        print("  No retention data available")

    # Save
    report = {
        "type": "retention",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "channel_id": channel_id,
        "retention_curve": retention_data,
    }
    out_file = REPORTS_DIR / f"retention_{video_id}_{end_date}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"\nSaved to {out_file}")


def report_weekly(args):
    """Generate a comprehensive weekly report for all recent Shorts."""
    creds = load_credentials()
    ya = build_service(creds)
    channel_id, channel_title, stats = get_channel_id(creds)

    if not channel_id:
        print("ERROR: Could not determine channel ID")
        return

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"=== Weekly Report: {channel_title} ===")
    print(f"Period: {start_date} to {end_date}")
    print(f"Channel ID: {channel_id}")
    if stats:
        print(f"Subscribers: {stats.get('subscriberCount', 'N/A')}")
        print(f"Total views: {stats.get('viewCount', 'N/A')}")
    print()

    # 1. Channel-level weekly metrics
    cq = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched,subscribersGained,averageViewDuration,likes,comments,shares",
        "dimensions": "day",
        "sort": "day",
    }
    cresp = ya.reports().query(**cq).execute()

    print("--- Daily Breakdown ---")
    print(f"{'Date':<12} {'Views':>8} {'MinWatch':>10} {'Subs+':>6} {'AvgDur':>8} {'Likes':>6} {'Comments':>9} {'Shares':>7}")

    weekly_totals = {"views": 0, "minutes": 0, "subs": 0, "likes": 0, "comments": 0, "shares": 0}
    for row in cresp.get("rows", []):
        date, views, mins, subs, avg_dur, likes, comments, shares = row
        weekly_totals["views"] += int(views)
        weekly_totals["minutes"] += float(mins)
        weekly_totals["subs"] += int(subs)
        weekly_totals["likes"] += int(likes)
        weekly_totals["comments"] += int(comments)
        weekly_totals["shares"] += int(shares)
        print(f"{date:<12} {int(views):>8,} {float(mins):>10.1f} {int(subs):>6} {float(avg_dur):>8.1f}s {int(likes):>6} {int(comments):>9} {int(shares):>7}")

    print(f"\n{'WEEKLY TOTAL':<12} {weekly_totals['views']:>8,} {weekly_totals['minutes']:>10.1f} {weekly_totals['subs']:>6}")
    print()

    # 2. Per-video performance for all videos in topics.json
    topics_data = json.loads(TOPICS_FILE.read_text()) if TOPICS_FILE.exists() else {"topics": []}
    topics_list = topics_data.get("topics", topics_data) if isinstance(topics_data, dict) else topics_data
    if isinstance(topics_list, dict):
        topics_list = list(topics_list.values())

    videos = []
    for t in topics_list:
        if isinstance(t, dict) and t.get("video_id"):
            videos.append({"video_id": t["video_id"], "title": t.get("title", "?"), "date": t.get("date", "?")})

    if videos:
        print("--- Per-Video Performance (last 7 days) ---")
        print(f"{'Video ID':<16} {'Title':<55} {'Views':>7} {'AvgDur':>8} {'Likes':>6} {'Subs+':>5}")
        print("-" * 95)

        video_reports = []
        for v in videos:
            vq = {
                "ids": f"channel=={channel_id}",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained",
                "filters": f"video=={v['video_id']}",
            }
            vresp = ya.reports().query(**vq).execute()

            if vresp.get("rows"):
                row = vresp["rows"][0]
                views, mins, avg_dur, likes, comments, shares, subs = row
                v["metrics"] = {
                    "views": int(views), "minutes_watched": float(mins),
                    "avg_view_duration_s": float(avg_dur), "likes": int(likes),
                    "comments": int(comments), "shares": int(shares),
                    "subscribers_gained": int(subs),
                }
                title_short = v["title"][:52] + "..." if len(v["title"]) > 55 else v["title"]
                print(f"{v['video_id']:<16} {title_short:<55} {int(views):>7,} {float(avg_dur):>7.1f}s {int(likes):>6} {int(subs):>5}")
            else:
                v["metrics"] = None
                title_short = v["title"][:52] + "..." if len(v["title"]) > 55 else v["title"]
                print(f"{v['video_id']:<16} {title_short:<55} {'N/A':>7}")

            video_reports.append(v)

        # 3. Top performers
        print()
        print("--- Top 5 by Views ---")
        scored = [(v["metrics"]["views"], v["title"], v["video_id"]) for v in video_reports if v.get("metrics")]
        scored.sort(reverse=True)
        for i, (views, title, vid) in enumerate(scored[:5], 1):
            title_short = title[:50] + "..." if len(title) > 53 else title
            print(f"  {i}. {title_short:<55} {int(views):>7,} views  ({vid})")

        print()
        print("--- Top 5 by Avg View Duration ---")
        scored_dur = [(v["metrics"]["avg_view_duration_s"], v["title"], v["video_id"]) for v in video_reports if v.get("metrics")]
        scored_dur.sort(reverse=True)
        for i, (dur, title, vid) in enumerate(scored_dur[:5], 1):
            title_short = title[:50] + "..." if len(title) > 53 else title
            print(f"  {i}. {title_short:<55} {float(dur):>7.1f}s  ({vid})")

    # Save full report
    report = {
        "type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": channel_id,
        "channel_title": channel_title,
        "period": {"start": start_date, "end": end_date},
        "weekly_totals": weekly_totals,
        "daily": [
            {
                "date": row[0], "views": int(row[1]), "minutes_watched": float(row[2]),
                "subscribers_gained": int(row[3]), "avg_view_duration_s": float(row[4]),
                "likes": int(row[5]), "comments": int(row[6]), "shares": int(row[7]),
            }
            for row in cresp.get("rows", [])
        ],
        "videos": video_reports,
    }

    out_file = REPORTS_DIR / f"weekly_{end_date}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"\nFull report saved to {out_file}")
    return report


def main():
    parser = argparse.ArgumentParser(description="YouTube Analytics for Tell Me More AI!")
    parser.add_argument("--report", required=True, choices=["channel", "video", "retention", "weekly"],
                        help="Type of report to generate")
    parser.add_argument("--video-id", help="Video ID for video-specific reports")
    args = parser.parse_args()

    if args.report == "channel":
        report_channel(args)
    elif args.report == "video":
        if not args.video_id:
            print("ERROR: --video-id required for video report")
            sys.exit(1)
        report_video(args)
    elif args.report == "retention":
        if not args.video_id:
            print("ERROR: --video-id required for retention report")
            sys.exit(1)
        report_retention(args)
    elif args.report == "weekly":
        report_weekly(args)


if __name__ == "__main__":
    main()
