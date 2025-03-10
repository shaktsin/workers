from celery import Celery
import time
import logging
from dynaconf import Dynaconf
from workers.workflow.wf import Workflow
from workers.workflow.kubehelper import KHelper
from workers.models.db_handler import DBHandler
from workers.models.model_deployments import ModelDeployment
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure Celery with Redis as the broker
main = Celery(
    "tasks",
    broker="redis://localhost:6379/0",  # Redis as the message queue
    backend="redis://localhost:6379/0"  # Store results in Redis
)

config = Dynaconf(settings_files=["settings.toml"])
#print(config.as_dict())
#print(config["DEFAULT"]["env"])
khelper = KHelper(config)
DBhelper = DBHandler(config)
DBhelper.create_db_tables()

@main.task
def process_job(job_id, modelDep):
    modelDep = ModelDeployment(**modelDep)
    logging.info(f"Processing job: {job_id} with data: {modelDep}")
    wfl = Workflow(config=config, khelper=khelper, dbhelper=DBhelper, modelDep=modelDep)
    wfl.add_step("KServe Inference Service Creation Step", wfl.create_kserve_service, modelDep)
    wfl.add_step("Wait Kserve Inference Service Step", wfl.wait_for_kserve_service, modelDep)
    wfl.add_step("K8s Ingress Service Creation Step", wfl.create_ingress, modelDep)
    wfl.add_step("Wait for Predict Url to be ready", wfl.wait_ingress_recon, modelDep)
    wfl.add_step("Wait for Predict Url to be ready", wfl.wait_for_routing, modelDep)
    wfl.run()
    return {"job_id": job_id, "status": "completed", "processed_data": modelDep.model_dump(mode="json")}