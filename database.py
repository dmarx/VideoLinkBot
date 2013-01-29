from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///ytbot.db')
Session = sessionmaker()
Base = declarative_base(bind=engine)

def init_db():
    import datamodel
    Base.metadata.create_all()
