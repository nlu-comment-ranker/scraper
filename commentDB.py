##
# Social Web Comment Ranking
# CS224U Spring 2014
# Stanford University 
#
# Database interface, using SQLAlchemy
#
# Ian F. Tenney
# May 10, 2014
##

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker

Base = declarative_base()

#################################
# Miscellaneous type converters #
# and helper functions          #
#################################

# USE THIS as primary key: no extra network request required
# since reddit API provides username in comment/submission JSON
def get_author_name(obj):
    try: return obj.author.name # human-readable username
    except: return None

# Timestamp converter
from datetime import datetime
def time_from_ms(t_ms):
    dt = datetime.utcfromtimestamp(t_ms)
    return dt.strftime('%Y-%m-%d %H:%M:%S')



#####################################
# Object Classes :: Database Schema #
# ORM mappings defined for:         #
# - Submission                      #
# - Comment                         #
# - User                            #
#####################################

class Submission(Base):
    __tablename__ = 'submissions'
    
    # Metadata
    # id = Column(Integer, primary_key=True)
    sub_id = Column(String, primary_key=True)   # reddit submission ID
    subreddit_id = Column(String)           # reddit subreddit ID
    timestamp = Column(DateTime)            # post time

    # Set up one->many relationship with comments
    comments = relation("Comment", backref="submission")
    # Reference posting user
    user_name = Column(String, ForeignKey('users.name')) # reddit author.name

    # Core data
    title = Column(String, nullable=False)
    text = Column(String, nullable=False)
    score = Column(Integer)
    
    # Additional post info
    stickied = Column(Boolean)      # sticky post
    distinguished = Column(String)  # ???
    gilded = Column(Integer)        # reddit gold

    # Domain and URL info
    domain = Column(String)
    short_link = Column(String)
    permalink = Column(String)

    def __init__(self, praw_obj=None, **kwargs):
        if not praw_obj: 
            return super(Submission, self).__init__(**kwargs)
        
        # If a PRAW submission object is given
        s = praw_obj
        
        self.sub_id = s.fullname    # full identifier: type_id
        self.user_name = get_author_name(s)     # reddit author.name
        self.subreddit_id = s.subreddit_id      # subreddit identifier
        self.timestamp = datetime.utcfromtimestamp(s.created_utc)

        self.title = s.title
        self.text = s.selftext
        self.score = s.score

        self.stickied = s.stickied
        self.distinguished = s.distinguished
        self.gilded = s.gilded

        self.domain = s.domain
        self.short_link = s.short_link
        self.permalink = s.permalink

    def __repr__(self):
        return "Submission(%s,\"%s\"):  %.140s" % (self.sub_id, 
                                                   self.title, 
                                                   self.text)
    
class Comment(Base):
    __tablename__ = 'comments'

    # Metadata
    # id = Column(Integer, primary_key=True)
    com_id = Column(String, primary_key=True)   # reddit comment ID
    subreddit_id = Column(String)           # reddit subreddit ID
    parent_id = Column(String)              # reddit parent ID (submission, or other comment)
    timestamp = Column(DateTime)            # post time

    # Relationship: reference submission, user
    sub_id = Column(String, ForeignKey('submissions.sub_id'))
    user_name = Column(String, ForeignKey('users.name')) # reddit author.name

    # Core data
    text = Column(String, nullable=False)
    score = Column(Integer)
    
    # Additional post info
    distinguished = Column(String)  # ???
    gilded = Column(Integer)        # reddit gold
    is_root = Column(Boolean)       # top-level comment

    # URL info
    permalink = Column(String)

    def __init__(self, praw_obj=None, **kwargs):
        if not praw_obj: 
            return super(Comment, self).__init__(**kwargs)
    
        # If a PRAW submission object is given
        c = praw_obj
        
        self.com_id = c.fullname    # full identifier: type_id
        self.user_name = get_author_name(c)     # reddit author.name        
        self.subreddit_id = c.subreddit_id      # subreddit identifier
        self.parent_id = c.parent_id            # parent identifier
        self.timestamp = datetime.utcfromtimestamp(c.created_utc)

        self.text = c.body
        self.score = c.score

        self.distinguished = c.distinguished
        self.gilded = c.gilded
        self.is_root = c.is_root

        self.permalink = c.permalink

    def __repr__(self):
        return "Comment(%s):  %.140s" % (self.com_id, 
                                          self.text)

class User(Base):
    __tablename__ = 'users'

    # Metadata
    name = Column(String, primary_key=True) # author.name
    user_id = Column(String) # author.fullname

    # Set up one->many relationship with comments and submissions
    comments = relation("Comment", backref="user")
    submission = relation("Submission", backref="user")

    # Info
    comment_karma = Column(Integer)
    link_karma = Column(Integer)
    is_mod = Column(Boolean)
    is_gold = Column(Boolean)

    ##
    # Additional User Statistics
    # (fill these in later)
    placeholder1 = Column(Integer)
    placeholder2 = Column(Integer)


    def __init__(self, praw_obj=None, **kwargs):
        """
        NOTE: If using a PRAW Redditor object from a
        comment or submission, use the default constructor
        as User(name=s.author.name) to avoid extra network access!
        All fields except name require an additional API call.
        """
        if not praw_obj: 
            return super(User, self).__init__(**kwargs)
    
        # If a PRAW submission object is given
        a = praw_obj

        self.name = a.name
        self.user_id = a.fullname

        self.comment_karma = a.comment_karma
        self.link_karma = a.link_karma
        self.is_mod = a.is_mod
        self.is_gold = a.is_gold

    def __repr__(self):
        return "User(%s): %s" % (self.name, self.user_id)