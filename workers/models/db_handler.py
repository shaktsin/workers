from sqlmodel import Session, SQLModel, create_engine, JSON
from workers.models.model_deployments import ModelDeployment, DeploymentJobs, Status
from typing import Dict, Any
from pydantic import BaseModel
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")



class DBHandler:

    def __init__(self, config):
        self.sqlite_file = config["DEFAULT"]["DB"]
        self.sqlite_url = f"sqlite:///{self.sqlite_file}"
        logging.info(f"reading db file {self.sqlite_url}")
        connect_args = {"check_same_thread": False}
        self.engine = create_engine(self.sqlite_url, connect_args=connect_args)

    def create_db_tables(self):
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            return session
        

    def update_model_deployment(self, id, url, status) -> Any:
        try:
            with self.get_session() as session:
                modelDep1 = session.get(ModelDeployment, id)
                modelDep1.status = status
                modelDep1.url = url

                session.commit()
                session.refresh(modelDep1)
                logging.info("passed")
            return True
        except Exception as e:
            logging.error(e) # replace with proper logger class
            return False 


