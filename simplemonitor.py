"""
Monitors /r/all for comments containing video links.
When one is encountered, sends the bot over to that 
post to do its thang.

Keeps track of comments we've already seen to make sure we don't double count.

The code below treats the simplebot2 module as though it were a class instance
which is probably bad form, but this certainly works fine. Should modify this 
in the future to take command line args: e.g. a subreddit or multisub to focus
on instead of /r/all, a different user-agent string, user/pass.... you know what?
None of these additional features really even requires I refactor this as a class
except the user-agent string, but really that shouldn't be modified anyway.
"""
import simplebot as s
from collections import deque  
import time

if not s.r.user:
    s.login()

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
            if c.author.name == s.r.user.name: # skip our own comments.
                continue
            sub = c.subreddit.display_name
            links = s.get_video_links_from_html(c.body_html)
            #if len( links )>0:
            for link in links:
                try:
                    print u'\n\n\nScraping "{sub}" found a link-comment by {auth} on "{post}"'.\
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
                s.post_aggregate_links(c.submission.id)
                print "\n\n\n"
                # That's it. I think we have a bot! With memos, even!
                # Sort of weird how I use the bot as though it were a 
                # class but it isn't really. Might not be the best idea
                # but whatever.
            #print n, len(memo)
            if n%100 == 0:
                print n
