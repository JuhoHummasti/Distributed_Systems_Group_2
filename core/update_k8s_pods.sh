#!/bin/bash

# Function to apply Kubernetes manifests
apply_manifests() {
  echo "Applying Kubernetes manifests..."
  kubectl apply -f core/k8s/
}

# Function to rollout restart deployments
restart_deployments() {
  echo "Restarting deployments..."
  kubectl rollout restart deployment -n default
}

# Main function
main() {
  apply_manifests
  restart_deployments
  echo "All Kubernetes pods have been updated for configuration changes."
}

# Execute main function
main