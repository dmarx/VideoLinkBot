import praw
from praw.errors import APIException
import re
import urlparse as up
from urllib2 import Request, urlopen

try:
    from BeautifulSoup import BeautifulSoup
except:
    from bs4 import BeautifulSoup

_ua = "YoutubeLinkBot by /u/shaggorama"
r = praw.Reddit(_ua)

def login(fname='loginCredentials.txt', _user=None, _pass=None):
    if _user is None and _pass is None:
        with open(fname,'r') as f:
            _user = f.readline().strip()
            _pass = f.readline().strip()
    print "Logging in as: {0} / {1}".format(_user, _pass)
    r.login(username=_user, password=_pass)

def get_video_links_from_html(text):
    """
    Strips video link from a string in html format
    by looking for the href attribute.
    """
    # could also just use BeautifulSoup, but this regex works fine
    link_pat   = re.compile('href="(.*?)"') 
    #pat_domain = re.compile('http://([^/]*?)/')
    #links
    links = link_pat.findall(text)
    yt_links = []
    for l in links:
        parsed = up.urlparse(l)
        #parsed.netloc.lower() #not really necessary
        for elem in parsed.netloc.split('.'):
            if elem in ('youtube','youtu','ytimg'):
                yt_links.append(l)
                break
    return yt_links

def get_title(url):
    """
    returns the title of a webpage given a url
    (e.g. the title of a youtube video)
    """
    request  = Request(url)
    response = urlopen(request)
    data     = response.read()
    soup = BeautifulSoup(data)
    title = soup.title.string[:-10] # strip out " - YouTube"
    # Need to strip out pipes since they muck up the reddit formatting.
    return title.replace('|','')

# Would like to post context sentence along with link to comment and link to video.
def sentence_tokenizer(text):
    """
    Very simple tokenizer.
    """
    # need to figure out good way to tokenize sentences that retains links.
    pass
        
# What I'd like to do is     
def parse_comment_html_for_links(html):
    """
    Takes a text in the form of praw.Comment.body_html, returns a list of sentences that contain
    youtube links (for context), the correspinding links, and the 
    video titles corresponding to the links.
    
    Actually, no it doesn't. That's what it should do. For now, just
    returns links and their corresponding video titles.
    """
    links = get_video_links_from_html(html)
    pairs = []
    for link in links:
        try:
            pairs.append( (get_title(link), link) )
        except:
            continue        
    return pairs
    
def build_comment_text(comment_dict, formatstr='|[{author}]({permalink}) | [{title}]({url})|'):
    """
    Returns the apporpriate text to relate the links in a particular comment.
    Given a comment containing several links, each link will be represented
    on a separate row in accordance to the provided formatstr. 
    
    Default format is a reddit table with two columns: left column is a link 
    to the comment titled by its author, the right column is a link to the 
    video titled by the video's title.
    
    @comment:   a praw.Comment object
    @formatstr: desired output format. Currently supports:
        @author:    comment author,
        @permalink: comment permalink
        @title:     video title
        @url:       video url
    """
    #links = parse_comment_html_for_links(comment.body_html)
    _title, _url = 0,1
    return "\n".join([formatstr.format(author=comment.author.name
                            ,title=link[_title]
                            ,url=link[_url]
                            ,permalink=comment.permalink) for link in links])

def scrape(submission):
    """
    Given a submission id, scrapes that submission and returns a list of comments
    associated with their links
    
    @submission: a 
    """        
    # just for convenience
    if type(submission) == type(''):
        submission = r.get_submission(submission_id = submission)
    collected_links = {}
    print "got %d comments" % len(submission.all_comments_flat)
    for i, comment in enumerate(submission.all_comments_flat):
        if i%10 == 0:
            print "Scraped %d comments." % i
        try:
            if comment.author.name != r.user.name:
                links = get_video_links_from_html(comment.body_html)
                for link in links:
                    try:
                        if collected_links[link]['created_utc'] < comment.created_utc:
                            collected_links[link] = {'author':comment.author.name, 'created_utc':comment.created_utc, 'permalink':comment.permalink}
                    except KeyError:
                        collected_links[link] = {'author':comment.author.name, 'created_utc':comment.created_utc, 'permalink':comment.permalink}
        except Exception, e:
            # ignore deleted comments and comments by deleted users.
            print e
            continue
    print "Found %d links" % len(collected_links)
    return collected_links
    

    return formatted_text

def build_comment(collected_links):
    text = '''Here are the collected video links posted in response to this post (deduplicated to the best of my ability):

|Source Comment|Video Link|
|:-------|:-------|\n'''    
    
    video_urls = [k for k in collected_links]
    authors = [collected_links[url]['author'] for url in video_urls]
    permalinks = [collected_links[url]['permalink'] for url in video_urls]
    titles = [get_title(url) for url in video_urls]    
    
    # pass comments to formatter as a list of dicts
    for link in [ {'author':a, 'permalink':p, 'title':t, 'url':u} for a,p,t,u in zip(authors, permalinks, titles, video_urls)]:
        #formatted_text+='|[{author}]({permalink}) | [{title}]({url})|'.format(link)
        text+='| [%(author)s](%(permalink)s) | [%(title)s](%(url)s) |\n' % link 
    return text
    
def post_aggregate_links(link_id='178ki0', text=None):    
    subm = r.get_submission(submission_id = link_id)  
    if text is None:             
        links = scrape(subm)
        text = build_comment(links)
    if text[-5:] == '----|':
        print 'No links to post'
    else:
        try:
            subm.add_comment(text) # need to handle comments that are too long.
        except APIException:
            trim_comment(text)
    
def trim_comment(text):
    """
    If comment is longer than 10000 chars, reddit won't let us post it. This boils down to around 50 links (I think).
    """
    # Removing permalink's to comments would significantly reduce the size of my comments.
    # could still post a link to the user's commenting history
    # Alternatively, could post a shortlink (?)
    while len(text)> 10000:
        text = '\n'.join(text.split('\n')[-1])[2:]
    return text
        
    