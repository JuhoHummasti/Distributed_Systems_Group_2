# Telco-Edge CDN for Latency-Sensitive Video Streaming

# System design

![System design](images/system_design.png)



# Kubernetes

## Clean cluster

How todelete all pods and related configurations in kubernmetes cluster and prevent the pods from restarting.
To delete all pods and related configurations in a Kubernetes cluster and prevent the pods from restarting, you can follow these steps:

Delete Deployments, StatefulSets, and DaemonSets: These resources manage the lifecycle of pods. Deleting them will stop the pods from being recreated.

```bash
kubectl delete deployments --all
kubectl delete statefulsets --all
kubectl delete daemonsets --all
```
Delete Pods: This will remove all running pods. Since the managing resources (Deployments, StatefulSets, DaemonSets) are already deleted, the pods will not be recreated.

```bash
kubectl delete pods --all
```
Delete Services, ConfigMaps, and Secrets: These resources are often associated with the pods and their configurations.

```bash
kubectl delete services --all
kubectl delete configmaps --all
kubectl delete secrets --all
```
Delete PersistentVolumeClaims (PVCs) and PersistentVolumes (PVs): If you have any persistent storage, you might want to delete these as well.

```bash
kubectl delete pvc --all
kubectl delete pv --all
```
Delete Namespaces: If you want to clean up specific namespaces, you can delete them. This will remove all resources within those namespaces.

```bash
kubectl delete namespace <namespace-name>
```

## Update kubernetes cluster with new containers

```bash
dockcer compose push  # On development machine

# On kubernetes controller node
git pull
sh core/update_k8s_pods.sh
```


# Integration tests

## Setup

1. Create and activate a Python virtual environment:
```sh
python -m venv .venv
source .venv/activate 

pip install -r requirements.txt
```

## Run test with docker compose

```bash
# All test cases
pytest -s -v
# invidual test cases
pytest -s -v  test/core/file-storage-service/test_file_storage_service.py
```
## Run test with kubernetes deployment

```bash
# All test cases
TEST_ENV=kubernetes pytest -s -v
# invidual test cases
TEST_ENV=kubernetes pytest -s -v  test/core/file-storage-service/test_file_storage_service.py
```