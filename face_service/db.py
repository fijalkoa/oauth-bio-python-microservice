from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class UserEmbedding(Base):
    __tablename__ = "user_embeddings"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    embedding = Column(JSON, nullable=False)

def init_db():
    from os import getenv
    url = getenv("DATABASE_URL")
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def save_embedding(session, user_id, embedding):
    entry = UserEmbedding(user_id=user_id, embedding=embedding)
    session.add(entry)
    session.commit()

def get_embeddings(session, user_id):
    res = session.query(UserEmbedding).filter_by(user_id=user_id).all()
    return [r.embedding for r in res]
