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
    repeats = Column(Integer)
    status = Column(String)  # e.g., "in_progress", "completed", "failed"
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
    sample_detail = relationship("SampleDetail", backref="sample", cascade="all, delete-orphan", single_parent=True)
    image = relationship("Image", backref="sample", cascade="all, delete-orphan", single_parent=True)

class SampleDetail(Base):
    __tablename__ = "SampleDetail"
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey("Sample.id"))
    parameter_id = Column(Integer, ForeignKey("Parameter.id"))
    value = Column(String)

class Parameter(Base):
    __tablename__ = "Parameter"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)





