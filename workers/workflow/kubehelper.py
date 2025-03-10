from kubernetes import client, config
from workers.models.model_deployments import ModelDeployment, Model, Resource
from typing import Any
import logging
import subprocess
import requests
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class KHelper:

    def __init__(self, app_config: Any):
        self.app_config = app_config
        if app_config["DEFAULT"].env != "Local":
            cluster = self.app_config["KUBERNETES"]["EKS_CLUSTER_NAME"]
            region = self.app_config["KUBERNETES"]["AWS_REGION"]

            subprocess.run(["aws", "eks", "update-kubeconfig", 
                            "--name", cluster, "--region", region], check=True)
        
        config.load_kube_config() 
        self.kclient = client.CustomObjectsApi()
        self.NetClient = client.NetworkingV1Api()
        self.appClient = client.AppsV1Api()

    def create_kserve_service(self, modelDep: ModelDeployment):
        model = Model(**modelDep.model)
        req_resource = Resource(**modelDep.request_res)
        limit_resource = Resource(**modelDep.limit_res)

        req_body = {
            "apiVersion": "serving.kserve.io/v1beta1",
            "kind": "InferenceService",
            "metadata": {
                "name": f"md-{modelDep.id}", 
                "namespace": self.app_config["KUBERNETES"]["SERVICE_NAMESPACE"],
                "annotations": {
                    "sidecar.istio.io/inject": "false"
                }
                
            },
            "spec": {
                "predictor": {
                "serviceAccountName": "sa",
                "minReplicas": modelDep.replicas,
                "model": {
                        "modelFormat": {"name": "xgboost"},
                        "storageUri": f"{model.bucket}/{model.prefix}",
                        "resources": {
                            "requests": {
                                "cpu": req_resource.cpu,
                                "memory": req_resource.memory
                            },
                            "limits": {
                                "cpu": limit_resource.cpu,
                                "memory": limit_resource.memory
                            }
                        }
                    }
                }
            }
        }

        return self.kclient.create_namespaced_custom_object(
            group="serving.kserve.io",
            version="v1beta1",
            namespace=self.app_config["KUBERNETES"]["SERVICE_NAMESPACE"],
            plural="inferenceservices",
            body=req_body
        )
    
    def check_status_service(self, modelDep: ModelDeployment):
        service_namne = f"md-{modelDep.id}-predictor"
        try:

            dep = self.appClient.read_namespaced_deployment(service_namne, "default")
            conditions = dep.status.conditions or []
            for condition in conditions:
                if condition.type == "Available" and condition.status == "True":
                    return True 

        except Exception as e:
            logging.error(f"K8s API Exception {str(e)}")
            return False 
        
    def create_ingress(self, modelDep: ModelDeployment):
        service_namne = f"md-{modelDep.id}-predictor"
        try:

            alb_status = json.dumps({
                "type": "fixed-response",
                "fixedResponseConfig": {
                    "contentType": "application/json",
                    "statusCode": "200",
                    "messageBody": "OK"
                }
            })

            ingress = client.V1Ingress(
                metadata=client.V1ObjectMeta(
                    name=service_namne,
                    annotations={
                        "alb.ingress.kubernetes.io/scheme": "internet-facing",
                        "alb.ingress.kubernetes.io/target-type": "ip",
                        "alb.ingress.kubernetes.io/actions.healthz-response": alb_status
                    }
                ),
                spec=client.V1IngressSpec(
                    ingress_class_name="alb",
                    rules=[
                        client.V1IngressRule(
                            http=client.V1HTTPIngressRuleValue(
                                paths=[
                                    client.V1HTTPIngressPath(
                                        path=f"/v2/health/live",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=service_namne,
                                                port=client.V1ServiceBackendPort(
                                                    number=80
                                                )
                                            )
                                        )
                                    ), 
                                    client.V1HTTPIngressPath(
                                        path=f"/v2/models/md-{modelDep.id}/infer",
                                        path_type="Prefix",
                                        backend=client.V1IngressBackend(
                                            service=client.V1IngressServiceBackend(
                                                name=service_namne,
                                                port=client.V1ServiceBackendPort(
                                                    number=80
                                                )
                                            )
                                        )
                                    ) 
                                ]
                            )
                        )
                    ]
                )
            )

            self.NetClient.create_namespaced_ingress(
                namespace="default",
                body=ingress
            )
            return True
        except Exception as e:
            logging.error(f"K8s API error {e}")
            return False
        
    def wait_ingress_recon(self, modelDep: ModelDeployment):
        service_namne = f"md-{modelDep.id}-predictor"
        ingress_status = self.NetClient.read_namespaced_ingress(service_namne, "default")
        if ingress_status.status.load_balancer and ingress_status.status.load_balancer.ingress:
            return ingress_status.status.load_balancer.ingress[0].hostname
        return None
    
    def wait_for_routing(self, modelDep: ModelDeployment):
        try:
            if not modelDep.url: return False 
            baseUrl = modelDep.url.split("/v2")[0]
            healthUrl = baseUrl + f"/v2/health/live"
            logging.info(f"health url {healthUrl}")
            response = requests.get(healthUrl, timeout=5)
            if response.status_code == 200: 
                logging.info("Model routing healthy")
                return True 
        except Exception as e:
            logging.error(e)
            return False 



        



