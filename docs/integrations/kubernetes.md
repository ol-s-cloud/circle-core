# Kubernetes Integration

## Overview

The Kubernetes integration provides a comprehensive deployment solution for Circle Core components across multiple environments. This integration leverages Kubernetes' orchestration capabilities to provide scalable, secure, and repeatable deployments with proper resource management, secret handling, and network security.

## Status

| Aspect | Details |
|--------|---------|
| **Status** | ✅ Complete |
| **Version Added** | v0.2.0 |
| **Last Updated** | April 16, 2025 |
| **Category** | DevOps & CI/CD |
| **Priority** | High |
| **Maintainer** | Infrastructure Team |

## Integration Details

### Capabilities

* Multi-environment deployment (development, staging, production)
* Configuration management with ConfigMaps
* Secure credential handling with Secrets
* Persistent storage management with PVCs
* External access configuration with Ingress
* Network security with NetworkPolicies
* Deployment validation and verification
* Kustomize-based environment customization

### Prerequisites

* Kubernetes cluster v1.24+ (tested with v1.25-1.27)
* kubectl CLI tool
* Basic knowledge of Kubernetes concepts
* Appropriate RBAC permissions in the target cluster

### Configuration Options

```yaml
# Example kustomization.yaml for a production environment
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namePrefix: circle-core-prod-

commonLabels:
  environment: production
  app: circle-core

patchesStrategicMerge:
  - deployment-patch.yaml
  - config-patch.yaml

images:
  - name: circle-core
    newName: your-registry/circle-core
    newTag: 0.2.0
```

### Deployment Structure

The Kubernetes integration uses the following structure:

```
deployment/kubernetes/
├── configmap.yaml        # Application configuration
├── deployment.yaml       # Core component deployment
├── ingress.yaml          # External access configuration
├── kustomize/            # Kustomize configurations
│   ├── base/             # Base configuration
│   └── overlays/         # Environment-specific overlays
│       ├── development/
│       ├── staging/
│       └── production/
├── network-policy.yaml   # Network security rules
├── pvc.yaml              # Persistent storage claims
├── secret.yaml           # Credential template
└── service.yaml          # Internal service definition
```

## Usage Examples

### Basic Deployment

```bash
# Deploy to development environment
./deployment/scripts/deploy.sh --environment development --target kubernetes

# Deploy to production environment
./deployment/scripts/deploy.sh --environment production --target kubernetes
```

### Validation

```bash
# Validate a deployment
./deployment/scripts/validate-deployment.py --environment production --target kubernetes
```

### Custom Configuration

```bash
# Generate custom configuration
./deployment/scripts/generate-config.py --environment production --output-dir ./config

# Apply custom configuration
kubectl apply -k ./config
```

## Security Considerations

* **Pod Security**: Non-root user execution, read-only filesystem where possible
* **Network Security**: Default-deny policy with specific allows
* **Secret Management**: Kubernetes secrets with proper RBAC
* **Resource Limits**: CPU and memory limits on all containers
* **RBAC**: Role-based access control for all components
* **TLS**: Ingress with TLS configuration
* **Image Security**: Verified container images

## Performance Considerations

* **Resource Allocation**: Appropriate CPU/memory requests and limits
* **Scaling**: Horizontal Pod Autoscaler support
* **Storage**: Performance considerations for persistent volumes
* **Node Affinity**: Optional node placement for optimized performance

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment fails | Check Kubernetes events: `kubectl describe pod <pod-name>` |
| Configuration issues | Verify ConfigMap contents and environment variables |
| Storage problems | Check PVC status and underlying storage provider |
| Network connectivity | Validate NetworkPolicy rules and service DNS resolution |
| Validation errors | Review validation script output for specific issues |

## Implementation Details

### Architecture Decisions

This integration implements the architecture described in [ADR-0001](architecture/decisions/0001-kubernetes-deployment-architecture.md), which provides detailed rationale for the design choices.

### Validation Framework

The validation framework performs these checks:
* Resource existence and correct configuration
* Health endpoint availability
* Container status and readiness
* Log analysis for errors
* Security compliance with best practices

### Custom Resource Handling

The integration can be extended with custom resources like:
* Prometheus ServiceMonitors for monitoring
* Istio VirtualServices for advanced routing
* Cert-Manager certificates for TLS automation

## Roadmap

* Multi-cluster deployment support (v0.3.0)
* Helm chart alternative (v0.4.0)
* Operator-based deployment (v0.5.0)
* Enhanced observability integration (v0.3.0)

## References

* [Kubernetes Documentation](https://kubernetes.io/docs/home/)
* [Kustomize Documentation](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)
* [Circle Core Deployment Guide](../guides/kubernetes-deployment.md)
* [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes/)

## Change History

| Version | Date | Changes |
|---------|------|---------|
| v0.2.0 | 2025-04-16 | Initial Kubernetes integration |
| v0.1.0 | 2025-04-14 | Preliminary Kubernetes design |
