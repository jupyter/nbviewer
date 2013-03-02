from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import declarative_base

from datetime import datetime as dt


Base = declarative_base()

class Notebook(Base):
    __tablename__ = 'notebooks'

    id = Column(Integer, primary_key=True)
    url = Column(String,unique=True)
    creationtime = Column(DateTime)

    def __init__(self, url):
        self.url = url
        self.creationtime = dt.now()


    def __repr__(self):
       return "<Notebook('%s','%s','%s')>" % (self.id,self.url, self.creationtime)

class AccessTime(Base):
    __tablename__ = 'accesstime'
    id = Column(Integer, primary_key=True)
    accesstime = Column(DateTime,nullable=True)
    notebook_id = Column(Integer,ForeignKey('notebooks.id'))

    notebook = relationship('Notebook', backref=backref('accesstime', order_by=id))

    def __init__(self, datetime=None):
        if not datetime :
            datetime = dt.now()
        self.accesstime = datetime

    def __repr__(self):
        return "<AccessTime('%s')>"% self.accesstime


#engine = create_engine('sqlite:///foo.db', echo=False)
#Session = sessionmaker(bind=engine)
#session = Session()

class NotebookStats(object):

    def __init__(self,session,url):
        try :
           self._stat  = session.query(Notebook).filter_by(url=url).one()
        except NoResultFound : 
           self._stat = Notebook(url)
        except Exception:
            return
        self.session=session
        session.add(self._stat)
        session.commit()

    def access(self):
        self._stat.accesstime.append(AccessTime(dt.now()))
        self.session.commit()

class Stats(object): 

    def __init__(self,engine):
        try :
            self.engine = engine
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()
            Base.metadata.create_all(engine) 
            #counting number of acces...
            # in the access time table, we group by notebook id, and count the reapeating occurences
            # we construct a 
            # :notebook_id: , :count: table
            self.stmt = self.session.query(AccessTime.notebook_id, func.count('*').\
                        label('access_count')).\
                        group_by(AccessTime.notebook_id).subquery()
        except Exception:
            pass

    def get(self,url):
        return NotebookStats(self.session, url)




    def most_accessed(self,count=10):
        # now we join this with the notebook table to get
        # :notebook:, :count:
        return [(count,u) for u,count in self.session.query(Notebook, self.stmt.c.access_count).\
            outerjoin(self.stmt, Notebook.id==self.stmt.c.notebook_id).\
            order_by(self.stmt.c.access_count.desc()).limit(count)]

#n=Notebook('http://www.google.com')
#session.add(n)
#session.commit()
