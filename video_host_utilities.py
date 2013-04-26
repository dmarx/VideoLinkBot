import urlparse as up
import re

# compile regexs outside link cleaning functions to ensure it is only compiled
# once to make sure regexp compilation doesn't detract from performance
yt_video_id_pat = re.compile('v=([A-Za-z0-9_-]+)')

def youtube_link_cleaner(link):
    parsed = up.urlparse(link)
    short_link = None
    if parsed.netloc == 'www.youtube.com' or parsed.netloc == 'm.youtube.com':
        match = re.search(yt_video_id_pat, link)
        if match:
            video_id = match.group()[2:]
            short_link = 'http://youtu.be/' + video_id
    elif parsed.netloc == 'youtu.be':
        video_id = parsed.path[1:] # I feel like maybe I should split on '/' and then take item 0 instead
        short_link = 'http://youtu.be/' + video_id
    
    return short_link
#    return 'http://youtu.be/' + video_id

# netloc:VLB_domain_code
# Codes: yt=youtube
supported_domains = {'youtube':'yt','youtu':'yt'} #,'ytimg':'yt'} 
link_cleaners     = {'yt':youtube_link_cleaner}  
