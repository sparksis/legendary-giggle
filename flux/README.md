# Deploying the VoIP.ms Sync Script with Flux CD

This directory contains the Kubernetes manifests required to deploy the call recording synchronization script using a GitOps approach with [Flux CD](https://fluxcd.io/).

The setup is designed to be secure and production-ready, using an init container to handle configuration at runtime.

## Overview of Resources

This Kustomize base defines the following Kubernetes resources:

- `PersistentVolumeClaim` (`pvc.yaml`): Creates a persistent volume to store the downloaded recordings and the `state.json` file, ensuring data is not lost between job runs.
- `CronJob` (`cronjob.yaml`): Schedules the synchronization script to run every hour. It uses an init container to securely generate the configuration file from a Kubernetes secret.

## Prerequisites

1.  A running Kubernetes cluster.
2.  [Flux CD](https://fluxcd.io/flux/installation/) installed and configured on your cluster.
3.  The Docker image for this application pushed to a container registry that your Kubernetes cluster can access.

## Configuration Steps

### 1. Update the Container Image

In `cronjob.yaml`, you **must** update the `image` field to point to the container image you built and pushed to your registry.

```yaml
# flux/cronjob.yaml
...
containers:
  - name: voipms-sync-container
    image: your-repo/voipms-sync:latest # <-- CHANGE THIS
...
```

### 2. Create the Credentials Secret

This `CronJob` requires a Kubernetes `Secret` named `voipms-credentials` to exist in the `voip-sync` namespace. This secret must contain your VoIP.ms API username and password.

You can create this secret by applying a manifest like the one below.

**Important**: The `username` and `password` values must be **base64-encoded**.

```yaml
# voipms-credentials-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: voipms-credentials
  namespace: voip-sync
type: Opaque
data:
  # echo -n 'YOUR_USERNAME' | base64
  username: WVdSUl9VU0VSTkFNRQ==
  # echo -n 'YOUR_PASSWORD' | base64
  password: WVdSUl9QQVNTV09SRA==
```

Apply this file to your cluster: `kubectl apply -f voipms-credentials-secret.yaml`.

For a more secure, GitOps-friendly approach, it is highly recommended to manage this secret using a tool like [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) or [SOPS](https://github.com/mozilla/sops).

## Deployment with Flux

To deploy this application using Flux, you will create a `Kustomization` resource on your cluster that points to this directory in your Git repository.

Here is a sample `Kustomization` manifest. This manifest demonstrates **variable substitution** (interpolations), a feature of Flux, to dynamically set the target namespace.

```yaml
# cluster-sync.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: voipms-sync
  namespace: flux-system
spec:
  interval: 10m0s
  path: ./flux # Path to this directory in your Git repo
  prune: true
  sourceRef:
    kind: GitRepository
    name: your-git-repo # The name of your Flux GitRepository source
  targetNamespace: "voip-sync-${CLUSTER_NAME}" # Example of interpolation
  vars:
    - name: CLUSTER_NAME
      value: "production"
```

In this example, Flux will replace `${CLUSTER_NAME}` with `"production"`, deploying the resources to the `voip-sync-production` namespace. This allows you to reuse the same manifests across different environments (e.g., staging, production).

## How the `CronJob` Works

The `CronJob` uses an **init container** to separate configuration from the application image.

1.  The `voipms-credentials` secret is mounted as environment variables into the init container.
2.  The init container runs a small shell script that writes a `config.ini` file to a shared `emptyDir` volume.
3.  The main application container starts and mounts this generated `config.ini` file, ready to use.

This pattern keeps the main Docker image generic and your secrets securely managed within the cluster.
