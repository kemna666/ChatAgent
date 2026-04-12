from datetime import datetime,timezone,timedelta
from ..services.databaseservice import Base
from sqlalchemy import Column, DateTime



class Thread(Base):
    __tablename__ = 'Thread'

    id:str = Column(primary_key=True)
    created_at:datetime = Column(DateTime(timezone=False),default=lambda:datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None))
