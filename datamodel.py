from database import *
from sqlalchemy import Table, Column, Boolean, Float, Integer, String, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation, backref
import time

class Submission(Base):
    """
    Connects select fields of a praw.Submission object to the db.
    """
    __tablename__ = 'submissions'
    id           = Column(String, primary_key=True)
    title        = Column(String)
    created_utc  = Column(Integer)
    last_scraped = Column(Integer)
    comments = relation("Comment") # If this isn't necessary, we don't need it. ADding it for now just in case
    bot_comment  = relation("BotComment") # This one is a little more useful, but still shouldn't really be necessary
    
    def __init__(self,post):
        self.id           = post.id
        self.link_title   = post.title
        self.created_utc  = post.created_utc
        self.last_scraped = int( time.time() ) # this doesn't really need to be an int. Also, we should probably rename this as first_scraped. I don't think we even need this column at all.
    
class Comment(Base):
    """
    Connects select fields of a praw.Comment object to the db.
    
    video_link stores a video (youtube) link if one was present in
    the comment. For the vast bulk of comments, this will be null.
    
    bot_commented is a check to see if the bot has already added
    this comment/link to the bots comment in the post. This field
    is iniatilized null, then the bot grabs all null values associated
    to a post and adds them to its comment.
    
    Current format: a particular comment with multiple links will get
    multiple entries in this table. 
    """

    __tablename__   = 'comments'
    id              = Column(String , primary_key=True)
    permalink       = Column(String)
    #link_id         = Column(String)
    link_id         = Column(String, ForeignKey('submissions.id'))
    author          = Column(String)
    created_utc     = Column(Integer)
    video_link      = Column(String, primary_key=True)
    bot_commented   = Column(String) # log whether or not the bot has commented. To be updated after scraping.
                                     # initialized null
    
    def __init__(self, comment, video_link):
        self.id             = comment.id
        self.permalink      = comment.permalink
        self.author         = comment.author.name
        self.created_utc    = comment.created_utc
        self.link_id        = comment.link_id[3:]
        self.video_link     = video_link           # in form: [text](hyperlink)

class BotComment(Base):
    """
    Connects select fields of a praw.Submission object to the db
    
    For ensuring that the bot only writes a single
    comment to a particular submission. Comment will be populated
    with links from comments sharing link_id and with video_link
    populated.
    """
    
    __tablename__   = 'botcomments'
    id              = Column(String) # this should really be the pk, but we only want one comment per link_id
    #link_id         = Column(String, primary_key=True)
    link_id         = Column(String, ForeignKey('submissions.id'), primary_key=True) # I wonder if this will work?
    created_utc     = Column(Integer)
    body            = Column(String)
    
    def __init__(self, comment):
        self.id     = comment.id        
        self.link_id        = comment.link_id[3:]
        self.created_utc    = comment.created_utc
        self.body           = comment.body
    
    
    
    
    
    
    
    




    
