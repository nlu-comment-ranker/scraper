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

class Subreddit(Base):
    __tablename__ = 'subreddits'

    subreddit_id = Column(String, primary_key=True) # api ID
    name = Column(String, unique=True) # human-readable

    # Set up one->many relationship with submissions
    submissions = relation("Submission", backref='subreddit')

    def __init__(self, praw_obj=None, **kwargs):
        if not praw_obj: 
            return super(Subreddit, self).__init__(**kwargs)
        
        # If a PRAW submission object is given
        s = praw_obj

        self.subreddit_id = s.fullname
        self.name = s.display_name

    def __repr__(self):
        return "Subreddit(%s): %s" % (self.subreddit_id, self.name)


class Submission(Base):
    __tablename__ = 'submissions'
    
    # Metadata
    # id = Column(Integer, primary_key=True)
    sub_id = Column(String, primary_key=True)   # reddit submission ID
    subreddit_id = Column(String, ForeignKey('subreddits.subreddit_id'))           # reddit subreddit ID
    timestamp = Column(DateTime)            # post time

    # Set up one->many relationship with comments
    comments = relation("Comment", backref="submission")
    # Reference posting user
    user_name = Column(String, ForeignKey('users.name')) # reddit author.name

    # Core data
    title = Column(String, nullable=False)
    text = Column(String, nullable=False)
    score = Column(Integer)
    ups = Column(Integer)
    downs = Column(Integer)
    
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
        self.text = s.selftext   # might need to do s.selftext.encode('ascii', 'ignore')
        self.score = s.score
        self.ups = s.ups
        self.downs = s.downs

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
    ups = Column(Integer)
    downs = Column(Integer)
    best_rank = Column(Integer) # ranking, from reddit's "Best" display order
 
    # Additional post info
    num_reports = Column(Integer)   # number of 'inappropriate' reports
    distinguished = Column(String)  # ???
    gilded = Column(Integer)        # reddit gold
    is_root = Column(Boolean)       # top-level comment
    num_replies = Column(Integer)   # number of immediate replies
    convo_depth = Column(Integer)   # max comment tree depth

    # URL info
    permalink = Column(String)

    def __init__(self, praw_obj=None, 
                 rank=None, num_replies=0, convo_depth=1, 
                 **kwargs):
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
        self.ups = c.ups
        self.downs = c.downs
        self.best_rank = rank 
        
        self.num_reports = c.num_reports
        self.distinguished = c.distinguished
        self.gilded = c.gilded
        self.is_root = c.is_root
        self.num_replies = num_replies
        self.convo_depth = convo_depth

        self.permalink = c.permalink

    def __repr__(self):
        return "Comment(%s):  %.140s" % (self.com_id, 
                                          self.text)

class User(Base):
    __tablename__ = 'users'

    # Metadata
    name = Column(String, primary_key=True) # author.name
    user_id = Column(String) # author.fullname
    timestamp = Column(DateTime) # author.created_utc

    # Set up one->many relationship with comments and submissions
    comments = relation("Comment", backref="user")
    submission = relation("Submission", backref="user")

    # Info
    comment_karma = Column(Integer)
    link_karma = Column(Integer)   # does not include karma from self submissions
    is_mod = Column(Boolean)
    is_gold = Column(Boolean)
    has_verified_email = Column(Boolean)
    
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
        self.timestamp = datetime.utcfromtimestamp(a.created_utc)

        self.comment_karma = a.comment_karma
        self.link_karma = a.link_karma
        self.is_mod = a.is_mod
        self.is_gold = a.is_gold
        self.has_verified_email = a.has_verified_email


    def __repr__(self):
        return "User(%s): %s" % (self.name, self.user_id)


class UserActivity(Base):
    __tablename__ = 'user_activities'

    id = Column(Integer, primary_key=True) # dummy ID
    user_name = Column(String, 
                       ForeignKey('users.name'), 
                       nullable=False) # reddit author.name
    subreddit_id = Column(String, nullable=False)
    subreddit_name = Column(String) 

    # Enforce constraint that (subreddit_id,subreddit_name) must match a subreddit entry
    __table_args__ = (ForeignKeyConstraint([subreddit_id, subreddit_name], 
                                           ['subreddits.subreddit_id','subreddits.name']),)

    # set up many->one relation to subreddits
    subreddit = relation("Subreddit", backref="activities",
                         foreign_keys=[subreddit_id, subreddit_name])
    user = relation("User", backref="activities")


    # Comment stats
    comment_count = Column(Integer)       # max 1000
    comment_pos_karma = Column(Integer)   
    comment_neg_karma = Column(Integer)
    comment_net_karma = Column(Integer)   # for last 1000 comments
    comment_avg_pos_karma = Column(Float)
    comment_avg_neg_karma = Column(Float)
    comment_avg_net_karma = Column(Float)
    
    # Submission stats
    sub_count = Column(Integer)       # max 1000
    sub_pos_karma = Column(Integer)   
    sub_neg_karma = Column(Integer)
    sub_net_karma = Column(Integer)   # for last 1000 submissions 
    sub_avg_pos_karma = Column(Float)
    sub_avg_neg_karma = Column(Float)
    sub_avg_net_karma = Column(Float)

    def __init__(self,
                 user=None,
                 subreddit=None,
                 user_name=None, 
                 subreddit_id=None, 
                 subreddit_name=None,
                 comment_stats=None, 
                 submission_stats=None,
                 **kwargs):
        """Constructor: call as 
        UserActivity(<User>,<Subreddit>, comment_stats, submission_stats),
        where <User> is an instance of commentDB.User,
        and <Subreddit> is an instance of commentDB.Subreddit,
        or with specific keyword arguments."""

        if user != None: # If User object passed
            self.user = user
            self.user_name = user.name
        else:
            self.user_name = user_name

        if subreddit != None: # If Subreddit object passed
            self.subreddit = subreddit
            self.subreddit_id = subreddit.subreddit_id
            self.subreddit_name = subreddit.name
        else:
            self.subreddit_id = subreddit_id
            self.subreddit_name = subreddit_name

        if comment_stats != None:
            self.comment_count = comment_stats['count']
            self.comment_pos_karma = comment_stats['pos_karma']
            self.comment_neg_karma = comment_stats['neg_karma']
            self.comment_net_karma = comment_stats['net_karma']
            self.comment_avg_pos_karma = comment_stats['avg_pos_karma']
            self.comment_avg_neg_karma = comment_stats['avg_neg_karma']
            self.comment_avg_net_karma = comment_stats['avg_net_karma']

        if submission_stats != None:
            self.sub_count = submission_stats['count']
            self.sub_pos_karma = submission_stats['pos_karma']
            self.sub_neg_karma = submission_stats['neg_karma']
            self.sub_net_karma = submission_stats['net_karma']
            self.sub_avg_pos_karma = submission_stats['avg_pos_karma']
            self.sub_avg_neg_karma = submission_stats['avg_neg_karma']
            self.sub_avg_net_karma = submission_stats['avg_net_karma']

    def __repr__(self):
        return "UserActivity(%s, %s, %s)" % (self.user_name,
                                             self.subreddit_id,
                                             self.subreddit_name)
