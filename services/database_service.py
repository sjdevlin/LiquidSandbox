from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from models import *
from services import Logger, AppConfig

class DatabaseService:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

##Temperature Profile


    def get_all_plates(self):
        with self.Session() as session: 
           return session.query(Plate).options(joinedload(Plate.well)).all()

    def get_plate_by_id(self, plate_id):
        with self.Session() as session: 
           return session.query(Plate).options(joinedload(Plate.well)).filter_by(id=plate_id).first()

##Experiments

    def add_experiment(self, experiment):
        with self.Session() as session:
            session.add(experiment)
            session.commit()
            return experiment.id
        
    def get_experiment_by_id(self, exp_id):
        with self.Session() as session: 
           return session.query(Experiment).options(joinedload(Experiment.sample)).filter_by(id=exp_id).first()

    def get_all_experiments(self):
        with self.Session() as session:
            return session.query(Experiment).options(joinedload(Experiment.sample)).all()
          
    def update_experiment(self, experiment):
        with self.Session() as session:
            session.merge(experiment)  # Merges the detached object into the session
            session.commit()
            return True
                    
    def delete_experiment(self, experiment_id):
        with self.Session() as session:
            experiment = session.query(Experiment).filter_by(id=experiment_id).first()
            session.delete(experiment)
            session.commit()

#####

    def get_image_set_by_id(self, exp_id):
        with self.Session() as session: 
           return session.query(ImageSet).options.filter_by(id=exp_id).first()

    def get_all_image_sets(self):
        with self.Session() as session:
            return session.query(ImageSet).all()



"""
    def update_experiment(self, experiment_id, new_status):
        with self.Session() as session:  # ✅ Automatically closes session
            experiment = session.query(Experiment).filter_by(id=experiment_id).first()
            if experiment:
                experiment.anneal_status = new_status
                session.commit() """