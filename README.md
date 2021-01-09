# Tools

Download reddit videos  
`downloadRedditVideos(subreddit, time=1000, filter="month", output="output.mp4")`

Merge all videos in /videos folder  
`mergeVideos(output="output/video.mp4")`

Upload to youtube  
`uploadVideo(title, description="", source="output/video.mp4", status="private", thumbnail="")`  
(needs client_secret.json and credentials.storage)

Create a narrated video of submissions from a subreddit  
`ttsVideo(subreddit="entitledparents", filter="month", limit=5)`
