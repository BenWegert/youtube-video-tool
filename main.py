from dotenv import load_dotenv

load_dotenv()
import os
import re
from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
    TextClip,
    ImageClip,
)
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    concatenate_audioclips,
)

import praw
import requests
from simple_youtube_api.Channel import Channel
from simple_youtube_api.LocalVideo import LocalVideo

from gtts import gTTS
from better_profanity import profanity
from collections import Iterable

if not os.path.exists("videos"):
    os.mkdir("videos")
if not os.path.exists("tmp"):
    os.mkdir("tmp")
if not os.path.exists("output"):
    os.mkdir("output")
if not os.path.exists("tts"):
    os.mkdir("tts")
    os.mkdir("tts/tmp")
    os.mkdir("tts/videos")
    os.mkdir("tts/audio")
    os.mkdir("tts/final")

else:
    if not os.path.exists("tts/videos"):
        os.mkdir("tts/videos")
    if not os.path.exists("tts/audio"):
        os.mkdir("tts/audio")
    if not os.path.exists("tts/tmp"):
        os.mkdir("tts/tmp")
    if not os.path.exists("tts/final"):
        os.mkdir("tts/final")

reddit = praw.Reddit(
    client_id=os.getenv("ID"),
    client_secret=os.getenv("SECRET"),
    password=os.getenv("PASS"),
    user_agent="youtube",
    username=os.getenv("USER"),
)

basepath = "./"
base_clip_path = "https://clips-media-assets2.twitch.tv/"


def retrieve_mp4_data(slug):
    T_CID = os.environ["T_CID"]
    T_TOKEN = os.environ["T_AT"]

    clip_info = requests.get(
        "https://api.twitch.tv/helix/clips?id=" + slug,
        headers={"Client-ID": T_CID, "Authorization": "Bearer {}".format(T_TOKEN)},
    ).json()
    thumb_url = clip_info["data"][0]["thumbnail_url"]

    title = clip_info["data"][0]["title"]
    slice_point = thumb_url.index("-preview-")
    mp4_url = thumb_url[:slice_point] + ".mp4"
    return mp4_url, title


def dl_clip(clip, i):
    slug = clip.split("/")[3].replace("\n", "")
    mp4_url, clip_title = retrieve_mp4_data(slug)
    v = requests.get(mp4_url)
    open("videos/" + i + ".mp4", "wb").write(v.content)


# Download reddit hosted and twitch hosted videos from subreddits
def downloadRedditVideos(subreddit, time=1000, filter="month", output="output.mp4"):
    for filename in os.listdir("videos/"):
        file_path = os.path.join("videos/", filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))

    addTime = 0
    i = 0
    if subreddit is 1:
        subreddit = "perfectlycutscreams"
    elif subreddit is 2:
        subreddit = "watchpeopledieinside"
    elif subreddit is 3:
        subreddit = "contagiouslaughter"
    elif subreddit is 4:
        subreddit = "livestreamfail"
    elif subreddit is 5:
        subreddit = "whatcouldgowrong"

    for submission in reddit.subreddit(subreddit).hot(limit=500):
        if submission.media is not None:
            if (
                "https://clips.twitch.tv/" in submission.url
                and "tt_" not in submission.url
            ):
                if addTime < time:
                    dl_clip(submission.url, str(i).rjust(2, "0"))
                    videoD = VideoFileClip(
                        "videos/" + str(i).rjust(2, "0") + ".mp4"
                    ).duration
                    addTime += videoD
                    i += 1
            elif "reddit_video" in submission.media:
                if (
                    addTime < time
                    and submission.media["reddit_video"]["duration"] < 200
                ):
                    video = submission.media["reddit_video"]["fallback_url"]
                    v = requests.get(video)

                    open("tmp/video.mp4", "wb").write(v.content)
                    a = requests.get(re.sub("[^/]*$", "audio", video, 1))
                    if a.status_code != 200:
                        b = requests.get(re.sub("[^/]*$", "DASH_audio.mp4", video, 1))
                        if b.status_code != 200:
                            open("videos/" + str(i).rjust(2, "0") + ".mp4", "wb").write(
                                v.content
                            )
                        else:
                            open("tmp/audio.mp4", "wb").write(b.content)
                            combined = VideoFileClip("tmp/video.mp4")
                            combined.audio = CompositeAudioClip(
                                [AudioFileClip("tmp/audio.mp4")]
                            )
                            combined.write_videofile(
                                "videos/" + str(i).rjust(2, "0") + ".mp4",
                                temp_audiofile="tmp/tmp_audio.mp3",
                            )

                    else:
                        open("tmp/audio.mp4", "wb").write(a.content)
                        combined = VideoFileClip("tmp/video.mp4")
                        combined.audio = CompositeAudioClip(
                            [AudioFileClip("tmp/audio.mp4")]
                        )
                        combined.write_videofile(
                            "videos/" + str(i).rjust(2, "0") + ".mp4",
                            temp_audiofile="tmp/tmp_audio.mp3",
                        )

                    os.unlink("tmp/video.mp4")
                    os.unlink("tmp/audio.mp4")

                    addTime += submission.media["reddit_video"]["duration"]
                    print("Video seconds: " + str(addTime))
                    i += 1


# Merge videos in videos/folder
def mergeVideos(output="output/video.mp4"):
    cliparray = []
    path = "./videos/"
    for file in os.listdir(path):
        resized = VideoFileClip(path + file).resize(height=1080)
        cliparray.append(resized)

    videoArray = concatenate_videoclips(cliparray, method="compose")
    if videoArray.size[0] < 1919:
        mar = round((1920 - videoArray.size[0]) / 2)
    else:
        mar = 0

    mask = videoArray.margin(opacity=0, left=mar, right=mar).resize(
        newsize=(1920, 1080)
    )
    mask.write_videofile(output, temp_audiofile="tmp/tmp_audio.mp3")


# upload any video tp youtube
def uploadVideo(
    title, description="", source="output/video.mp4", status="private", thumbnail=""
):
    # loggin into the channel
    channel = Channel()
    channel.login("client_secret.json", "credentials.storage")

    # setting up the video that is going to be uploaded
    video = LocalVideo(file_path=source)

    tags = []

    # setting snippet
    video.set_title(title)
    video.set_description(description)
    video.set_tags(tags)
    video.set_category("entertainment")

    # setting status
    video.set_embeddable(True)
    video.set_license("youtube")
    video.set_privacy_status(status)
    video.set_public_stats_viewable(True)

    # setting thumbnail
    if len(thumbnail) > 3:
        video.set_thumbnail_path(thumbnail)

    # uploading video and printing the results
    video = channel.upload_video(video)
    print(video.get_video_id())
    print(video)


def deleteTTS():
    for filename in os.listdir("tts/videos/"):
        file_path = os.path.join("tts/videos/", filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))
    for filename in os.listdir("tts/tmp/"):
        file_path = os.path.join("tts/tmp/", filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))
    for filename in os.listdir("tts/audio/"):
        file_path = os.path.join("tts/audio/", filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


# Creates a narrated video of top submissions of a selected subreddit
def ttsVideo(subreddit="entitledparents", filter="month", limit=5):
    deleteTTS()
    for filename in os.listdir("tts/final/"):
        file_path = os.path.join("tts/final/", filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))

    for submission in reddit.subreddit(subreddit).hot(limit=limit):
        path = "./tts/"
        videos = []

        if len(submission.selftext) > 100:
            ttsMerge(submission)
            cliparray = []
            audioarray = []
            for file in os.listdir(path + "videos/"):
                cliparray.append(VideoFileClip(path + "videos/" + file))

            for file in os.listdir(path + "audio/"):
                audioarray.append(AudioFileClip(path + "audio/" + file))

            audio = concatenate_audioclips(audioarray)

            final_clip = concatenate_videoclips(cliparray, method="compose")
            final_clip.audio = audio
            final_clip.write_videofile(
                path + "final/" + submission.id + ".mp4",
                temp_audiofile="tts/tmp/tmp_audio.mp3",
            )
            deleteTTS()

    for file in os.listdir(path + "final/"):
        videos.append(VideoFileClip(path + "final/" + file))

    final_clip = concatenate_videoclips(videos, method="compose")
    final_clip.write_videofile("output2.mp4", temp_audiofile="tmp/tmp_audio.mp3")


# Merge individual submission videos
def ttsMerge(
    submission,
    words=50,
    fontSize=60,
    title_fontSize=100,
    font="Quadrat-Grotesk-W01-Black",
    voice="en_uk",
):
    title = submission.title
    text = submission.selftext.lower()
    text = re.sub(r"https\S+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"#\w+ ?", "", text, flags=re.MULTILINE)
    whitelist = set(
        """1234567890abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ,.?!():#$%"'=-\n/@^"""
    )
    text = "".join(filter(whitelist.__contains__, text))

    titleSpeech = profanity.censor(title, " ")
    speech = profanity.censor(text, " ")
    title = profanity.censor(title, "*")
    print(text)

    tts = gTTS(titleSpeech + ". " + speech, lang=voice)
    tts.save("tts/audio/" + submission.id + ".mp3")

    text_list = text.split(" ")
    i = 0

    chunks = len(text_list) // words + (len(text_list) % words > 0)

    tts = gTTS(title, lang=voice)
    tts.save("tts/tmp/" + submission.id + ".mp3")
    intro = AudioFileClip("tts/tmp/" + submission.id + ".mp3").duration

    try:
        txt_clip = TextClip(
            title,
            font=font,
            fontsize=title_fontSize,
            color="white",
            size=(1920, 1080),
            method="caption",
            align="West",
            stroke_color="black",
            stroke_width=3,
        ).set_pos("center")

    except UnicodeEncodeError:
        txt_clip = TextClip(
            title.encode("utf-8"), fontsize=title_fontSize, color="white"
        ).set_duration(intro)
    img = ImageClip("./assets/bg.jpg")
    final_clip = CompositeVideoClip([img, txt_clip])
    final_clip.duration = intro
    final_clip.write_videofile(
        "tts/videos/" + submission.id + ".mp4",
        fps=30,
        temp_audiofile="tts/tmp/tmp_audio.mp3",
    )

    while i < chunks:
        text = " ".join(text_list[i * words : (i * words) + words])
        extra = 0
        if profanity.contains_profanity(text) is True:
            extra = 4
        text = profanity.censor(text, "*")
        if re.search("[a-zA-Z]", text) != None:
            if len(text_list[i * words : (i * words) + words]) < 49:
                print("last slide")
            else:
                text += "..."
            tts = gTTS(text, lang=voice)
            tts.save("tts/tmp/" + submission.id + str(i).rjust(2, "0") + ".mp3")
            duration = AudioFileClip(
                "tts/tmp/" + submission.id + str(i).rjust(2, "0") + ".mp3"
            ).duration
            try:
                txt_clip = TextClip(
                    text,
                    font=font,
                    fontsize=fontSize,
                    color="white",
                    size=(1920, 1080),
                    method="caption",
                    align="West",
                    stroke_color="black",
                    stroke_width=3,
                ).set_pos("center")

            except UnicodeEncodeError:
                txt_clip = TextClip(
                    text.encode("utf-8"), fontsize=fontSize, color="white"
                ).set_duration(duration - 0.7 - extra)
            img = ImageClip("./assets/bg.jpg")
            final_clip = CompositeVideoClip([img, txt_clip])
            final_clip.duration = duration - 0.5 - extra
            final_clip.write_videofile(
                "tts/videos/" + submission.id + str(i).rjust(2, "0") + ".mp4",
                fps=30,
                temp_audiofile="tts/tmp/tmp_audio.mp3",
            )
            i = i + 1


# def askReddit(id, sort="best"):
#     submission = reddit.submission(id=id)
#     submission.comment_sort = sort
#     comments = submission.comments.list()
#     i = 0
#     for comment in comments:
#         print(comment.body)
#         print("\n*****************")
#         replies = comment.replies
#         if i < 3:
#             for reply in replies:
#                 if isinstance(replies, Iterable) is True:
#                     print(reply)
#         i += 1
# if 'score' in reply and reply['score'] > 1000:
