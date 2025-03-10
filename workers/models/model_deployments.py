
from sqlmodel import Field, Session, SQLModel, create_engine, select, Relationship
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from enum import Enum
from sqlalchemy import JSON, Column
from datetime import datetime
from pydantic import field_validator

class ModelType(str, Enum):
     SINGLE = "single"
     MULTI = "multi"

class Model(BaseModel):
     type: ModelType
     bucket: str 
     prefix: str 


class InferenceType(str, Enum):
     CPU = "cpu"
     GPU = "gpu"

class Resource(BaseModel):
     cpu: str = None 
     memory: str = None 
     gpu: int = None 

class Status(str, Enum):
     CREATING = "creating"
     ACTIVE = "active"
     UPDATING = "updating"
     DELETING = "deleting"
     DELETED = "deleted"
     FAILED = "failed"
     
     
class ModelDeployment(SQLModel, table=True):
     id: int | None = Field(default=None, primary_key=True)
     type: InferenceType = Field(default=InferenceType.CPU)
     status: Status = Field(default=Status.CREATING)
     model: Model = Field(sa_column=Column(JSON))
     #model: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
     url: Optional[str] = None 
     replicas: int = Field(default=1)
     request_res: Resource = Field(sa_column=Column(JSON))
     limit_res: Resource = Field(sa_column=Column(JSON))
     created_at: datetime = Field(default_factory=datetime.utcnow)
     updated_at: datetime = Field(default_factory=datetime.utcnow)

     # Establish relationship (1-to-Many with Post)
     deploymentjobs: List["DeploymentJobs"] = Relationship(back_populates="modeldeployment")

     class Config:
          json_exclude = {"deploymentjobs"}

     
     @field_validator("model")
     @classmethod
     def validate_model(cls, value):
        if not isinstance(value, Dict) or not value:
            raise ValueError("Model must be a valid JSON object and not null")
        return value

          

class DeploymentJobs(SQLModel, table=True):
     id: int | None = Field(default=None, primary_key=True)
     workflow_job_id: str | None = Field(default=None, index=True)
     model_deployment_id: int = Field(foreign_key="modeldeployment.id")
     created_at: datetime = Field(default_factory=datetime.utcnow)
     updated_at: datetime = Field(default_factory=datetime.utcnow)

     modeldeployment: Optional[ModelDeployment] = Relationship(back_populates="deploymentjobs")

     
