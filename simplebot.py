"""
Reddit bot that scrapes a post for videoo links
and posts the collection in a table as a comment.

This script is designed for scraping a single post.
Run as follows:

    import simplebot as s
    s.login(_user=username, _pass=password)
    post_aggregate_links(submisison_id)

To run the bot as a continuous scrape of 
/r/all/comments, use simplemonitor.py. 
"""

import praw
from praw.errors import APIException
import re
import urlparse as up
from HTMLParser import HTMLParser
from lxml import etree
import time
import pandas as pd
from video_host_utilities import youtube_link_cleaner, supported_domains, \
                                 link_cleaners, title_cleaners, get_host_code

_ua = "YoutubeLinkBot reddit bot by /u/shaggorama"
r = praw.Reddit(_ua)

botCommentsMemo = {}
scrapedCommentsMemo = {}
scrapedLinksMemo = {}

def login(_user=None, _pass=None, fname='loginCredentials.txt'):
    if _user is None and _pass is None:
        with open(fname,'r') as f:
            _user = f.readline().strip()
            _pass = f.readline().strip()
    print "Logging in as: {0} / {1}".format(_user, _pass)
    r.login(username=_user, password=_pass)

def fix_html_entities(html, parser=HTMLParser()):
    return parser.unescape( parser.unescape(html))

def get_video_links_from_html(text):
    """
    Strips video link from a string in html format
    by looking for the href attribute.
    """
    # could also just use BeautifulSoup, but this regex works fine
    link_pat   = re.compile('href="(.*?)"') 
    links = link_pat.findall(text)
    video_links = []
    for l in links:
        code = get_host_code(l)
        if code:
            clean = link_cleaners[code]
            if clean:
                link = clean(fix_html_entities(l))
                if link:
                    video_links.append(link)                
    return video_links

def get_title(url, default = None, hparser=etree.HTMLParser(encoding='utf-8')):
    """
    returns the title of a webpage given a url
    (e.g. the title of a youtube video)
    """
    def _get_title(_url):            
        htree=etree.parse(url, hparser)
        raw_title = htree.find(".//title").text        
        code = get_host_code(_url)
        title = title_cleaners[code](raw_title)
        title = re.sub('[\|\*\[\]\(\)~]','',title)
        return title
    try:
        title = _get_title(url)
    except Exception, e:
        print "Encountered some error getting title for video at", url
        print e
        time.sleep(2)
        try:
            title = _get_title(url)
        except:
            print 'OK then, let''s just call it "%s"' % default
            title = default
        if title is None:
            title = default
    return title

def scrape(submission):
    """
    Given a submission id, scrapes that submission and returns a list of comments
    associated with their links
    
    @submission: a 
    """        
    ### Should add in some functionality for recognizing when we've already maxed-out the comment length on a post.
    ### OH SHIT! better yet, figure out a way to RESPOND TO MY OWN COMMENT WITH ADDITIONAL LINKS.
    # just for convenience
    if type(submission) == type(''):
        submission = r.get_submission(submission_id = submission)
    # for updating links and whatever.
    if scrapedLinksMemo.has_key(submission.id):
        collected_links = scrapedLinksMemo[submission.id]
        scrapedCommentIDs = scrapedCommentsMemo[submission.id]
        print "We have already collected %d video links on this submission." % len(collected_links)
    else:
        scrapedCommentIDs = set()
        scrapedCommentsMemo[submission.id] = scrapedCommentIDs 
    print "got %d comments" % len(submission.all_comments_flat)
    for i, comment in enumerate(submission.all_comments_flat):
        try:
            if comment.author.name == r.user.name: # deleted comment handling doesn't seem to be working properly.
                # if we have already memoized a bot comment for this post, continue
                # otheriwse, confirm found bot comment contains links and if it does, 
                # memoize it.
                if botCommentsMemo.has_key(submission.id):
                    continue
                elif get_video_links_from_html(comment.body_html):
                    botCommentsMemo[submission.id] = comment
            else:
                links = get_video_links_from_html(comment.body_html)
                for link in links:
                    add_memo_entry(comment, link)
        except Exception, e:
            # ignore deleted comments and comments by deleted users.
            print "encountered some error in scrape()"
            print e
            continue # why do name attribute errors keep getting re-raised???
        scrapedCommentIDs.add(comment.id)
    collected_links = scrapedLinksMemo[submission.id]
    print "Scraped {0} comments, found {1} links".format(i, len(collected_links) )
    return collected_links  # this isn't really even necessary since we could just call it down from the memo.

def get_scraped_comments(link_id):
    """ to be retired in favor of call to memo"""
    print "building comments memo"
    if scrapedLinksMemo.has_key(link_id):
        collected_comments = scrapedCommentsMemo[link_id]
        scraped = set( [collected_comments[url]['id'] for url in collected_comments] )
    else:
        "Populating scrapedCommentsMemo with", link_id
        scraped = set()
        scrapedCommentsMemo[link_id] = {} 
    return  scraped
    
def add_memo_entry(comment, link):
    submission_id = comment.submission.id
    if not link:
        if not scrapedCommentsMemo.has_key(submission_id):
            scrapedCommentsMemo[submission_id] = set()      # this might be redundant
        scrapedCommentsMemo[submission_id].add(comment.id)
    try:
        username = comment.author.name
    except:
        username = None
    link_entry = {'author':username
                 ,'created_utc':comment.created_utc
                 ,'permalink':comment_shortlink(comment)
                 , 'id':comment.id
                 ,'score':comment.score
                 ,'title':None # This is lazy
                 }
    if scrapedLinksMemo.has_key(submission_id):
        collected_links = scrapedLinksMemo[submission_id]        
        try:
            if collected_links.ix[link, 'score'] < comment.score:
               # collected_links.ix[link, :] = link_entry ### I think this is causing the bug in issue # 25
               # This is a shitty fix, but it should solve the problem.
               for k in link_entry.keys():
                   collected_links.ix[link, k] = link_entry[k]
        except KeyError, e:
            new_rec = pd.DataFrame(link_entry, index=[link])
            collected_links = collected_links.append(new_rec)
            scrapedLinksMemo[submission_id] = collected_links
    else:
        scrapedLinksMemo[submission_id] = pd.DataFrame(link_entry, index=[link])

def comment_shortlink(c):
    return 'http://reddit.com/comments/'+ c.link_id[3:] + '/_/' + c.id 

def build_comment(collected_links, link_id=None):
    print "Building comment"
    head = '''Here is a list of video links collected from comments that redditors have made in response to this submission:

|Source Comment|Score|Video Link|
|:-------|:-------|:-------|\n'''    
    
    tail ="""\n* [VideoLinkBot FAQ](http://www.reddit.com/r/VideoLinkBot/wiki/faq)
* [Feedback](http://www.reddit.com/r/VideoLinkBot/submit)"""      
    
    titles = []
    print "Getting video titles"
    if link_id: # if we've been provided with a link_id, memoize the link titles.
        for url in collected_links.index:
            try:
                if not scrapedLinksMemo[link_id].ix[url,'title']:
                    scrapedLinksMemo[link_id].ix[url,'title'] = get_title(url)
                    print "got title for",url                
            except Exception, e:
                print "some problem getting title for", url
                print e
                continue
                
    print "Got video titles. Formatting text for each link."
    text=u''
    for _url, c in scrapedLinksMemo[link_id].sort(columns='score',ascending=False).iterrows():
        if c['title']:
            _title = c['title']
        else:
            _title = _url
    
        text += u'|[{author}]({permalink})|{score}|[{title}]({url})|\n'.format(
                 author=c['author']
                 ,permalink = c['permalink']
                 ,title = c['title']
                 ,url = _url
                 ,score= c['score']
                 )
        
    len_playlist = 82 # I think...
    print "Trimming content as needed"
    text = trim_comment(text, 10000-len(head)-len(tail)-len_playlist)    
    print "Comment built."
    return head+text+tail
    
def post_comment(link_id, subm, text):
    try:
        if botCommentsMemo.has_key(link_id):
            bot_comment = botCommentsMemo[link_id]
            print "editing", bot_comment.id
            bot_comment.edit(text)
            # need to overwrite existing comment object, otherwise we'll add playlist
            # using the pre-scrape text.
            # Manually overwrite 'body' attribute.
            bot_comment.body = text
            print "successfully updated comment."
        else:
            print "Posting new comment"
            bot_comment = subm.add_comment(text)
            botCommentsMemo[link_id] = bot_comment
            print "Successfully posted new comment."
        result = True
        print bot_comment.id
    except APIException, e:
        # need to handle comments that are too long. 
        # Really, this should probably be in build_comment()
        print e
        print "sleeping for 5 seconds, trimming comment"
        time.sleep(5)       # maybe the API is annoyed with
        trim_comment(text)  # maybe the comment is too long (this should have been handled already)
        result = False 
    return result
    
def trim_comment(text, targetsize=10000):
    """
    If comment is longer than 10000 chars, reddit won't let us post it. This boils down to around 50 links (I think).
    """
    # Removing permalink's to comments would significantly reduce the size of my comments.
    # could still post a link to the user's commenting history
    # Alternatively, could post a shortlink (?)
    print "Trimming comment down to %d chars." % targetsize
    while len(text)> targetsize:
        text = '\n'.join(text.split('\n')[:-1])#[2:]
    print "Processed comment length:",len(text)
    return text

def add_playlist(c):
    """
    Adds a radd.it playlist to an existing comment.
    """
    playlist = "http://radd.it/comments/{0}/_/{1}?only=videos&start=1".format(c.link_id[3:], c.id)
    text = c.body + "\n* [Playlist of videos in this comment]({0})".format(playlist)
    c.edit(text)    
    
def post_aggregate_links(link_id='178ki0', max_num_comments = 1000, min_num_comments = 8, min_num_links=5):   
    """Not sure which function to call? You probably want this one."""    
    subm = r.get_submission(submission_id = link_id)      
    if not min_num_comments < subm.num_comments < max_num_comments:
        print "[NO POST] Submission has %d comments. Not worth scraping." % subm.num_comments
        return None
    try:
        print u'Scraping "{0}"'.format(subm.title)
    except:
        print u'Scraping "{0}"'.format(subm.id)
    links = scrape(subm) # Theoretically, we could just pull this down from the memo.    
    n_links = len(links)
    if  n_links >= min_num_links:
        authors = links.author.unique()
        if len(authors) >1:
            try:
                print u'[POST] Posting {nlinks} links to "{sub}" post "{post}"'.\
                    format(nlinks = n_links
                          ,sub    = subm.subreddit.display_name
                          ,post   = subm.title)
            except:
                print u'[POST] Posting {nlinks} links to "{sub}" post "{post}"'.\
                    format(nlinks = n_links
                          ,sub    = subm.subreddit.id
                          ,post   = subm.id)
            text = build_comment(links, subm.id)
            print "comment built, trying to post."
            posted = False
            while not posted:
                posted = post_comment(link_id, subm, text)
            print "Appending playlist..."
            add_playlist(botCommentsMemo[link_id])
            print "Video links successfully posted."
        else:
            print "[NO POST] All links from same user. Need at least 2 different users to post."
    else: 
        print "[NO POST] Only found %d links. Need %d to post." % (n_links, min_num_links)

if __name__ == '__main__':
    login()
    post_aggregate_links()
    
