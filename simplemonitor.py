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
from urllib2 import HTTPError, URLError

LASTUPDATED = time.time()

def update_hot_comments(upd_interval):
    """
    Revisit bot's "Hot" comments every <interval> minutes.
    This should really be handled by a separate thread, but this works ok.
    
    PARAMETERS
    
    upd_interval (int): minutes between updates.
    """
    global LASTUPDATED
    now = time.time()
    if now - LASTUPDATED > upd_interval*60:
        print "\n\n\n~~Updating comments, sorted by Hot"
        print "Last updated %s" % time.strftime('%X', time.localtime(LASTUPDATED) )
        hot = s.r.user.get_comments(sort='hot', time='day')
        scrape(hot, skip_bot=False)
        LASTUPDATED = time.time()
        elapsed = LASTUPDATED - now
        print "\n\nFinished updating bot comments."
        print "%d minutes elapsed.\n\n" % int(elapsed/60)

n=0
memo = deque(maxlen=200) #could probably even be shorter, but I'm ok with it.    
def scrape(comments, skip_bot = True, upd_comment_thresh_score =2):   
    global n 
    for c in comments:        
        if c.id in memo:
            time.sleep(10)
            break
        else:
            n+=1
            memo.append(c.id)
            try:
                if c.author.name == s.r.user.name: 
                    if skip_bot: # skip our own comments.
                        continue
                    elif c.score < upd_comment_thresh_score: # If updating hot comments, exit when we hit a comment with score < threshhold.
                        return
            except:
                continue
            sub = c.subreddit.display_name
            if sub in blacklist:
                continue
            links = s.get_video_links_from_html(c.body_html)
            #if len( links )>0:
            #for link in links:  #NO WONDER WE KEEP SCRAPING THE SAME SUBMISSIONS OVER AND OVER!!!
            if links:
                try:
                    print u'\n{sub} | {auth} | {post}'.\
                        format(sub=c.subreddit.display_name
                              ,auth=c.author
                              ,post=c.submission.title)
                except:
                    # Even accounting for unicode, still getting some funkiness.
                    print u'\n\n\n{sub} | {auth} | {post}'.\
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

cfg = ConfigParser()

cfg.read('vlb_config.ini')
username = cfg.get('LoginCredentials','username')
password = cfg.get('LoginCredentials','password')

with open(cfg.get('blacklist','filename'),'r') as f:
    blacklist = f.read().split()


if not s.r.user:
    s.login(username, password)


while True:
    print "Top of loop"
    try:
        update_hot_comments(60)
        all = s.r.get_all_comments(limit = None, url_data = {'limit':100})
        scrape(all)
    except (HTTPError, URLError) as e:
        wait_time = 300
        print e
        print "sleeping ", wait_time
        time.sleep(wait_time) # wait 5min after, resume scrape
