"""
Monitors /r/all for comments containing video links. When one is encountered, 
sends the bot to that post to do its thang.

Keeps track of comments we've already seen to make sure we don't double count.

The code below treats simplebot module as though it were a class instance
which is probably bad practice, but it certainly works fine and the code seems
pretty readable to me. 
"""
import simplebot as s
from collections import deque  
import time
from ConfigParser import ConfigParser

cfg = ConfigParser()

cfg.read('vlb_config.ini')
username = cfg.get('LoginCredentials','username')
password = cfg.get('LoginCredentials','password')

with open(cfg.get('blacklist','filename'),'r') as f:
    blacklist = f.read().split()


if not s.r.user:
    s.login(username, password)

n=0
memo = deque(maxlen=200) #could probably even be shorter, but I'm ok with it.
while True:
    print "Top of loop"
    all = s.r.get_all_comments(limit = None, url_data = {'limit':100})
    for c in all:        
        if c.id in memo:
            time.sleep(10)
            break
        else:
            n+=1
            memo.append(c.id)
            try:
                if c.author.name == s.r.user.name: # skip our own comments.
                    continue
            except:
                continue
            sub = c.subreddit.display_name
            if sub in blacklist:
                continue
            links = s.get_video_links_from_html(c.body_html)
            #if len( links )>0:
            for link in links:
                try:
                    print u'\nScraping "{sub}" found a link-comment by {auth} on "{post}"'.\
                        format(sub=c.subreddit.display_name
                              ,auth=c.author
                              ,post=c.submission.title)
                except:
                    # Even accounting for unicode, still getting some funkiness.
                    print u'\n\n\nScraping "{sub}" found a link-comment by {auth} on "{post}"'.\
                        format(sub=c.subreddit.id
                              ,auth=c.author.id
                              ,post=c.submission.id)
                print "Directing bot to scrape post for video links."
                #s.add_memo_entry(comment, link) This feels like a good idea, but is sort of turning out to be a pain in the ass. We'll rescrape the one comment.
                try:
                    s.post_aggregate_links(c.submission.id)
                except:
                    continue #handle any arbitrary errors.
            #print n, len(memo)
            if n%100 == 0:
                print n, len(s.botCommentsMemo)
