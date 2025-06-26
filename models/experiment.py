from tokenize import String
from sqlalchemy import Column, Integer, Float, Boolean, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, column_property
from models import Base, Plate
from datetime import datetime


class Experiment(Base): 

    #following variables are sqlalchemy objects related to the Experiment table in the database

    __tablename__ = "Experiment"
    id = Column(Integer, primary_key=True)
    plate_id = Column(Integer, ForeignKey("Plate.id"))
    description = Column(String)
    notes = Column(String)
    creation_date_time = Column(DateTime)
    dispensing_start_date_time = Column(DateTime)
    dispensing_finish_date_time = Column(DateTime)
    sample = relationship(
        "Sample",
        backref="parent",
        cascade="all, delete-orphan",
        single_parent=True,)

class Sample(Base):
    __tablename__ = "Sample"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("Experiment.id"))
    well_row = Column(Integer)
    well_column = Column(Integer)
    mix_cycles = Column(Integer)
    mix_speed = Column(Float)
    mix_volume = Column(Float)
    mix_height = Column(Float)
    pipette = Column(String)
    image = relationship("Image", backref="sample", cascade="all, delete-orphan", single_parent=True)






