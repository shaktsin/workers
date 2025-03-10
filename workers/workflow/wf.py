from tenacity import retry, stop_after_attempt, wait_fixed
from workers.workflow.kubehelper import KHelper
from workers.models.model_deployments import Status
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class Workflow:
    def __init__(self, config, khelper, dbhelper, modelDep):
        self.config = config
        self.khelper = khelper
        self.dbhelper = dbhelper
        self.modelDep = modelDep
        self.steps = []
       

    def add_step(self, name, func, *args, **kwargs):
        """Adds a new step to the workflow"""
        self.steps.append((name, func, args, kwargs))

    def run(self):
        """Executes the workflow step-by-step"""

        succeeeded = True 
        modeldep = None
        for step_num, (name, func, args, kwargs) in enumerate(self.steps, start=1):
            try:
                result = func(*args, **kwargs)
                logging.info(f"step {name}, Success, {result} ")
            except Exception as e:
                logging.error(e)
                succeeeded = False 
                break  # Stop workflow on failure

        if succeeeded:
            status = Status.ACTIVE
            logging.info("Model Deployment is live")
        else:
            status = Status.FAILED
            logging.info("Failed to create model deployment")

        self.update_status(self.modelDep.id, self.modelDep.url, status)

    def update_status(self, id, url, status):
        self.dbhelper.update_model_deployment(id, url, status)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def create_kserve_service(self, modelDep: Any):
        """Kserve Inference Service Step"""
        logging.info("Kserve Inference Service Step Completed")
        try:
            self.khelper.create_kserve_service(modelDep)
            logging.info("deployment pods created")
        except Exception as e:
            logging.error(e)
            raise e
        return "Done"

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(60))
    def wait_for_kserve_service(self, modelDep: Any):
        """Wait Step for Kserve Inference Service to come healthy"""
        logging.info("Wait for pod to be healthy")
        healthy = self.khelper.check_status_service(modelDep)
        if not healthy:
            raise Exception("deployment pods not healthy")
        else:
            logging.info("deployment pods healthy")
        return "Done"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def create_ingress(self, modelDep: Any):
        """K8s ingress object creation step"""
        logging.info("creating k8s ingress")
        healthy = self.khelper.create_ingress(modelDep)
        if not healthy:
            raise Exception("Retry, inference service not healthy")
        else:
            logging.info("ingress created")
        return "Done"
    
    @retry(stop=stop_after_attempt(10), wait=wait_fixed(60))
    def wait_ingress_recon(self, modelDep: Any):
        """K8s ingress object creation step"""
        logging.info("wait for ingress to be ready")
        url = self.khelper.wait_ingress_recon(modelDep)
        if not url:
            raise Exception("Retry, inference service not healthy")
        else:
            logging.info("ingress ready")
        self.modelDep.url = f"http://{url}/v2/models/md-{modelDep.id}/infer"
        return "Done"
    
    @retry(stop=stop_after_attempt(10), wait=wait_fixed(30))
    def wait_for_routing(self, modelDep: Any):
        """K8s ingress object creation step"""
        logging.info("Wait for routing through LB to be healthy")
        resp = self.khelper.wait_for_routing(self.modelDep)
        if not resp:
            raise Exception("Retry, inference service not healthy")
        else:
            logging.info("inference service is healthy")
        return "Done"
    