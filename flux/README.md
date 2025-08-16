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

### 1. Configure Image Automation (Optional)

The `cronjob.yaml` manifest is already configured for Flux Image Update Automation. When a new version of the application image is pushed to the container registry, Flux can automatically update the `image` tag and commit the change back to your repository.

To enable this, you will need to create `ImageRepository` and `ImagePolicy` resources in your cluster. See the [Flux Image Update Automation documentation](https://fluxcd.io/flux/guides/image-update/) for a detailed guide.

The image line in `cronjob.yaml` that Flux will update is:
```yaml
# flux/cronjob.yaml
...
containers:
  - name: voipms-sync-container
    image: your-repo/voipms-sync:latest # {"$imagepolicy": "voip-sync:voipms-sync"}
...
```
You will need to create an `ImagePolicy` named `voipms-sync` in the `voip-sync` namespace for this to work.

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

## Deployment with Flux (from OCI)

The CI pipeline for this repository publishes the Kustomize configuration in this directory as an OCI artifact. You should configure your Flux deployment to pull from this OCI artifact instead of directly from the Git repository.

This approach decouples the deployment from the source code, leading to more reliable and secure deployments.

First, you need to create an `OCIRepository` source in your cluster to tell Flux where to find the manifests.

```yaml
# oci-source.yaml
apiVersion: source.toolkit.fluxcd.io/v1beta2
kind: OCIRepository
metadata:
  name: voipms-sync-manifests
  namespace: flux-system
spec:
  interval: 10m
  url: oci://ghcr.io/your-org/flux-manifests # <-- CHANGE THIS
  ref:
    semver: ">=0.1.0"
```

Next, create a `Kustomization` that points to this `OCIRepository` source.

```yaml
# kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: voipms-sync
  namespace: flux-system
spec:
  interval: 10m
  prune: true
  sourceRef:
    kind: OCIRepository
    name: voipms-sync-manifests # Must match the name of the OCIRepository above
  targetNamespace: voip-sync
```

## How the `CronJob` Works

The `CronJob` uses an **init container** to separate configuration from the application image.

1.  The `voipms-credentials` secret is mounted as environment variables into the init container.
2.  The init container runs a small shell script that writes a `config.ini` file to a shared `emptyDir` volume.
3.  The main application container starts and mounts this generated `config.ini` file, ready to use.

This pattern keeps the main Docker image generic and your secrets securely managed within the cluster.
