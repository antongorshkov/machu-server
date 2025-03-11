import os
import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter

load_dotenv()

def get_channel_videos(channel_url):
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    print(YOUTUBE_API_KEY)
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    
    channel_id = channel_url.split("/")[-1]
    
    print(f"Getting videos for channel {channel_id}")
    channel_response = youtube.channels().list(
        part="contentDetails",
        forHandle=channel_id
    ).execute()

    playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    videos = []
    next_page_token = None

    while True:
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        videos += playlist_response["items"]
        
        next_page_token = playlist_response.get("nextPageToken")
        if next_page_token is None:
            break

    return videos

def extract_transcripts(videos):
    for video in videos:
        video_id = video["snippet"]["resourceId"]["videoId"]
        video_title = video["snippet"]["title"]
        print(f"Video ID: {video_id}\nTitle: {video_title}\n")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            formatter = TextFormatter()
            text_formatted = formatter.format_transcript(transcript)
            # Now we can write it out to a file.
            with open(video_id + ".txt", 'w', encoding='utf-8') as txt_file:
                txt_file.write(text_formatted)
        except TranscriptsDisabled:
            print(f"Error: Transcripts are disabled for video ID {video_id}")
        except NoTranscriptFound:
            print(f"Error: No transcripts found for video ID {video_id}")
    return None

channel_url = "https://www.youtube.com/@lavidaverdepodcast"
videos = get_channel_videos(channel_url)
print(f"Found {len(videos)} videos for channel {channel_url}")
extract_transcripts(videos)