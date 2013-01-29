import praw
import database as db
from datamodel import *
import re
import urlparse as up
from urllib2 import Request, urlopen
try:
    from BeautifulSoup import BeautifulSoup
except:
    from bs4 import BeautifulSoup


from sqlalchemy.orm.exc import FlushError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

db.init_db()
s = Session()

# connection to reddit is global to leverage
# praw's control over API rate limiting
_ua = "YoutubeLinkBot by /u/shaggorama"
r = praw.Reddit(_ua)
    
class Bot(object):
    def __init__(self):  
        self.yt_links     = {}  # for debugging
        self.last_scraped = {}  # for memoizing most recent ~~comment from a submission~~ could as easily be last time bot scraped post.
        self.botcomments  = {}  # for memoizing location of existing comments.
        self.rebuild_cache()
    def login(self, fname='loginCredentials.txt', _user=None, _pass=None):
        """
        Log into reddit.com. If credentials are
        stored in a file, pass filename. Otherwise,
        use _user and _pass parameters
        """        
        if _user is None and _pass is None:
            with open(fname,'r') as f:
                _user = f.readline().strip()
                _pass = f.readline().strip()
        global r
        print "Logging in as: {0} / {1}".format(_user, _pass)
        r.login(username=_user, password=_pass)
    
    def rebuild_cache(self):
        """
        Rebuilds self.last_scraped and self.botcomments dictionaries to prevent 
        duplicating work and IntegrityErrors that would otherwise result from 
        inserting comments we've already scraped.
        """
        past_day = int(time.time()) - 93600
        db_submissions = [row[0] for row in s.query(Submission.id).filter(Submission.created_utc > past_day).all()]
        if len(db_submissions) == 0:
            return
        #db_last_scraped = s.query(Submission.id, func.max(Comment.created_utc) ).join(Submission.comments).group_by(Submission.id).filter(Comment.video_link != None)
        db_last_scraped = s.query(Comment.link_id, func.max(Comment.created_utc)). \
                            filter(Comment.link_id.in_(db_submissions)). \
                            group_by(Comment.link_id).all()
                               #.filter(Comment.video_link is not None).\ # Wait...we actually don't want this filter.
                            
        db_botcomments   = s.query(BotComment).filter(BotComment.link_id.in_(db_submissions)).all() 
        
        for row in db_last_scraped:        
            self.last_scraped[row[0]] = row[1]
        
        # this is how it should be done, but I don't know how to get a specific comment based on its id alone.
        # Instead, I think we're going to have to scrape our own comment history and populate this memo with 
        # praw.Comment objects instead of just comment_ids
        for row in db_botcomments:        
            self.botcomments[row.link_id] = row.id
        
    def scrape_submission(self, link_id):
        """
        Assumes a submision has been identified
        as a candidate for youtube links and therefore
        has already been logged in the database.
        
        Stores comments to db, returns a list of db.comment objects.
        
        Current implementation does not look for previously reviewed comments.
        Also, does not actively ignore comments posted by this bot, which it should.
            --> could look up id in database, if it exists
            -- more simply, just check comment author.
        Should definitely add that in.
        """        
        #global r
        global s # this isn't really necessary.
        subm = r.get_submission(submission_id = link_id)
        try:
            last_scraped = self.last_scraped[link_id]  
            print last_scraped
        except KeyError: 
            print "Adding submission to db"
            last_scraped = 0
            submission = Submission(subm)
            try:
                s.add(submission)
                s.commit()
            except Exception, e: #(FlushError, IntegrityError):
                print e
                print "handling exception..."
                # In case we didn't properly rebuild the cache
                s = Session()
        latest_comment = last_scraped
        print subm
        results = []
        #commit_iter = 0    # commit after every commit_limit database writes
        #commit_limit = 1   # let's just commit after every link we find, for now.
         # use created_UTC of last posted comment in submission for later reference. This way we don't need to reference the comment ID against all scraped comments.
        for c in subm.all_comments_flat:
            if c.created_utc <= last_scraped:
                continue
            if str(c.author) == str(r.user.name): # ignore comments posted by this bot.
                continue            
            yt_links = parse_links(c)
            if len(yt_links) > 0:
                for link in yt_links:
                    comment = Comment(c, link)
                    results.append(comment) # hopefully accessing these comments later won't result in issuance of SQL, but I think it will.
                    s.add(comment) # originally, the idea was to scrape all comments so I know which I've seen already, but we can just use a timestamp for that. Not changing anything though: might be interesting for stats/targetting subreddits
                    #commit_iter +=1
                    # Need a better way to handle these errors. Problem arises when same comment contains the same link twice.
                    try:
                        #if commit_iter >= commit_limit:
                        #    s.commit()
                        s.commit()
                        print c.created_utc
                        if c.created_utc > latest_comment: #
                            print "updating latest_comment"
                            latest_comment = c.created_utc
                    except (FlushError, IntegrityError):       
                        #s.expunge_all() # this is only ok because we're currently committing the comments as we see them.
                        s = Session() #hopefully this works. 
        print "finished scraping"
        s.commit() # catch any stragglers
        self.last_scraped[link_id] = max(latest_comment, last_scraped) #putting max here is probably redundant
        self.yt_links[link_id] = results # will overwrite anything already scraped for this link.
        return results
        
    def scrape_and_post(self, link_id):
        """
        Write a comment or edit an existing comment to promote discovered yt links.
        """
        in_link_id = link_id #change variable name to reduce confusion with other methods that use same parameter name
        links = self.scrape_submission(in_link_id)
        bot_comment   = s.query(BotComment).filter_by(link_id = in_link_id).first() # should replace this with call to memo.
        if bot_comment is None:
            self.make_comment(in_link_id, links)
        else:
            print "edit comment condition satisfied."
            self.edit_comment(in_link_id, links)            
    def build_link_str(self, c):
        """
        Formats data for posting as a bot comment. Returns a single line.
        
        Assumes we're being passed datamodel.Comment objects, not praw.Comment objects.
        I guess I could build in a case to do different things for different types...
        Really, I should just change this to expect text.
        """
        return '* via [%s](%s): %s\n' % (c.author, c.permalink, c.video_link)
    def make_comment(self, link_id, links_list):
        """
        Posts a bot comment with aggregated video links. Should only be called by post_found_links
        
        Assumes we're being passed datamodel.Comment objects, not praw.Comment objects.
        I guess I could build in a case to do different things for different types...
        """
        print "posting a new comment to", link_id
        if len(links_list) == 0:    
            return
        global s # this is necessary to rebuild Sessions when we encounter an error
        comment_str = "Here's a collection of all the video links in this post's comments:\n\n"
        for c in links_list:
            comment_str += self.build_link_str(c)
        new_comment = r.get_submission(submission_id=link_id).add_comment(comment_str)
        botcomment = BotComment(new_comment)
        try:
            s.add(botcomment)
            s.commit()
            self.botcomments[link_id] = botcomment.id
        except (FlushError, IntegrityError), e:
            print "Error storing botcomment:"
            print e
            s = Session()
        
        # Last step: need to update database Comment.bot_commented flag
        
    def edit_comment(self, link_id, links_list):
        print links_list
        in_link_id = link_id
        botcomment = s.query(BotComment).filter(BotComment.link_id == in_link_id).first()
        comment_str = botcomment.body # make sure we don't loose the existing comment.
        
        pass

# Retire this function in favor of get_video_links_from_html(text)
def parse_links(comment):
    """
    Strips video links from the body of a praw.Comment object.
    Returns a list of links in format [text](url)
    
    Should probbaly generalize this to take a string as input and return
    a list of 2-tuples. 
    
    Currently only supports youtube links embedded in []() style links.
    """
    # Could make this fancier/more precise by
    # using urlparse to confirm youtube is domain.
    # Need to add in functionality to get links that were 
    # posted as raw urls. Consider using:
    #    p_link=re.compile('href="(.*?)"')
    #    p_domain=re.compile('http://([^/]*?)/')
    # Search comment.body_html instead of (or in addition to?) comment.body
    link_pat = re.compile('\[(.*?)\]\((.*?)\)')
    links = link_pat.findall(comment.body)
    yt_links = []
    for txt, url in links:
        if url.find('youtube') != -1: 
            yt_links.append('[%s](%s)' % (txt, url))
    return yt_links

def get_video_links_from_html(text):
    """
    Strips video link from a string in html format
    by looking for the href attribute.
    """
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
    return soup.title.string

if __name__ == '__main__':
    yt_bot = Bot()
    yt_bot.login()        
    #yt_bot.scrape_submission(link_id='178ki0') # sandbox submission
    yt_bot.scrape_and_post(link_id='178ki0')

