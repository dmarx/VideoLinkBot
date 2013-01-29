import praw
import database as db
from datamodel import *
import re

db.init_db()
s = Session()

# connection to reddit is global to leverage
# praw's control over API rate limiting
_ua = "YoutubeLinkBot by /u/shaggorama"
r = praw.Reddit(_ua)
    
class Bot(object):
    def __init__(self):                   
        pass
        
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
    
    def scrape_submission(self, link_id):
        ''' 
        Assumes a submision has been identified
        as a candidate for youtube links and therefore
        has already been logged in the database.
        
        Stores comments to db, returns a list of db.comment objects.
        
        Current implementation does not look for previously reviewed comments.
        Also, does not actively ignore comments posted by this bot, which it should.
            --> could look up id in database, if it exists
            -- more simply, just check comment author.
        Should definitely add that in.
        '''
        pass
        global r
        subm = r.get_submission(submission_id = link_id)
        print subm
        results = []
        commit_iter = 0 # commit after every commit_limit database writes
        commit_limit = 1 #let's just commit after every link we find, for now.
        for c in subm.all_comments_flat:
            #print c
            if c.author == r.user.name # ignore comments posted by this bot.
                continue
            yt_links = parse_links(c)
            if len(yt_links) > 0:
                for link in yt_links:
                    comment = Comment(c, link)
                    results.append(comment)
                    s.add(comment)
                    commit_iter +=1
                    if commit_iter >= commit_limit:
                        s.commit()
        s.commit() # catch any stragglers
        return results
        
    def post_found_links(self, _link_id):
        """
        Write a comment or edit an existing comment to promote discovered yt links.
        """
        links = scrape_submission(_link_id)
        bot_comment   = s.query(BotComment).filter_by(link_id = _link_id).first()
        if bot_comment is None:
            #self.make_comment(_link_id, links) ### I'm thinking of using make_comment and edit_comment methods.
            comment_str = ''
        else:
            comment_str = bot_comment.body # make sure we don't loose the existing comment.
        


def parse_links(comment):
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

        
if '__name__' == '__main__':
    yt_bot = Bot()
    yt_bot.login()        
    yt_bot.scrape_submission(link_id='178ki0') # sandbox submission


