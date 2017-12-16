from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from enum import Enum
import dateutil.parser

engine = create_engine('sqlite:///baza.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

MAX_TASKS_PER_USER = 5


class TaskType(Enum):
    lock = 0
    alarm = 1
    crypto = 2


class Result(Enum):
    OK = 1
    Warn = 2
    Ban = 3


class Task(Base):
    """
    nick, host, type, added, execution, targeted, arguments
    """
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    nick = Column(String)
    host = Column(String)
    type = Column(Integer)
    added = Column(String)  # data dodania
    execution = Column(String)  # data wykonania
    arguments = Column(String)
    targeted = Column(Integer)


def create_tables():
    Base.metadata.create_all(engine)


def add_task(nick, host, type, execution, arguments, targeted):
    db = Session()
    tasks_per_user = db.query(Task).filter(Task.host == host).count()
    new_task = None
    if tasks_per_user == MAX_TASKS_PER_USER:
        new_task = add_lock(nick, host, targeted)
        result = Result.Warn
    elif tasks_per_user > MAX_TASKS_PER_USER:
        warn = db.query(Task).filter(Task.type == 0)[0]
        warn_time = dateutil.parser.parse(warn.added)
        if warn_time >= datetime.now() - timedelta(minutes=5):
            result = Result.Ban
        else:
            db.delete(warn)
            new_task = add_lock(nick, host, targeted)
            result = Result.Warn
    else:
        new_task = Task(nick=nick, host=host, type=type, added=datetime.now().isoformat(' '), execution=execution, arguments=arguments, targeted=targeted)
        result = Result.OK
    if new_task is not None:
        db.add(new_task)
        db.commit()
        db.close()
    return result


def add_lock(nick, host, targeted):
    lock_until = datetime.now() + timedelta(hours=1)
    new_task = Task(nick=nick, host=host, type=TaskType.lock.value, added=datetime.now().isoformat(' '), execution=lock_until.isoformat(' '), targeted=targeted)
    return new_task
