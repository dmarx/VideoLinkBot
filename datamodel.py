from database import *
from sqlalchemy import Table, Column, Boolean, Float, Integer, String, Unicode, DateTime, ForeignKey
from sqlalchemy.orm import relation,backref
import time

class Submission(Base):
    """
    Connects select fields of a praw.Submission object to the db.
    """
    __tablename__ = 'submissions'
    link_id      = Column(String, primary_key=True)
    link_title   = Column(String)
    created_utc  = Column(Integer)
    last_scraped = Column(Integer)
    
    def __init__(self,post):
        self.link_id      = post.link_id
        self.link_title   = post.link_title
        self.created_utc  = post.created_utc
        self.last_scraped = int( time.time() )
    
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
    comment_id      = Column(String , primary_key=True) # I would make this the PK, but then we can't use this table like this for comments with multiple links.
    link_id         = Column(String)
    author          = Column(String)
    created_utc     = Column(Integer)
    video_link      = Column(String, primary_key=True) #will this make a composite pk?
    bot_commented   = Column(String) # log whether or not the bot has commented. To be updated after scraping.
                                     # initialized null
    
    def __init__(self, comment, video_link):
        self.comment_id     = comment.name
        self.author         = comment.author.name
        self.created_utc    = comment.created_utc
        self.link_id        = comment.link_id
        self.video_link     = video_link           # in form: [text](hyperlink)

class BotComment(Base):
    """
    Connects select fields of a praw.Submission object to the db
    
    For ensuring that the bot only writes a single
    comment to a particular submission. Comment will be populated
    with links from comments sharing link_id and with video_link
    populated.
    """
    
    __tablename__ = 'botcomments'
    comment_id      = Column(String) # this should really be the pk, but we only want one comment per link_id
    link_id         = Column(String, primary_key=True)
    created_utc     = Column(Integer)
    body            = Column(String)
    
    def __init__(self, comment):
        self.comment_id     = comment.name        
        self.link_id        = comment.link_id
        self.created_utc    = comment.created_utc
        self.body           = comment.body
    
    
    
    
    
    
    
    




    
