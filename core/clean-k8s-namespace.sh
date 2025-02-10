#!/bin/bash

NAMESPACE="default"

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "Namespace $NAMESPACE does not exist"
    exit 1
fi

echo "Cleaning namespace: $NAMESPACE"

# Delete deployments
echo "Deleting deployments..."
kubectl delete deployments --all -n "$NAMESPACE"

# Delete services
echo "Deleting services..."
kubectl delete services --all -n "$NAMESPACE"

# Delete pods
echo "Deleting pods..."
kubectl delete pods --all -n "$NAMESPACE"

# Delete configmaps
echo "Deleting configmaps..."
kubectl delete configmaps --all -n "$NAMESPACE"

# Delete secrets
echo "Deleting secrets..."
kubectl delete secrets --all -n "$NAMESPACE"

# Delete PVCs
echo "Deleting persistent volume claims..."
kubectl delete pvc --all -n "$NAMESPACE"

# Delete PVs (cluster-wide resource)
echo "Deleting persistent volumes..."
kubectl delete pv --all

# Delete statefulsets
echo "Deleting statefulsets..."
kubectl delete statefulsets --all -n "$NAMESPACE"

# Wait for all resources to be deleted
echo "Waiting for all resources to be deleted..."
kubectl wait --for=delete pods --all -n "$NAMESPACE" --timeout=60s || true

echo "Namespace $NAMESPACE has been cleaned"