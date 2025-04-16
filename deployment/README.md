# Circle Core Deployment Templates

This directory contains deployment templates and configurations for deploying Circle Core in different environments.

## Deployment Options

Circle Core can be deployed in a variety of environments:

- **Docker**: Simple containerized deployment using Docker and Docker Compose
- **Kubernetes**: Scalable, orchestrated deployment using Kubernetes
- **Cloud Providers**: Native cloud deployments on major cloud platforms
  - AWS (Amazon Web Services)
  - Azure (Microsoft Azure)
  - GCP (Google Cloud Platform)
- **On-Premises**: Self-hosted deployment in your own data center

## Deployment Structure

```
deployment/
├── docker/                  # Docker deployment files
│   ├── Dockerfile           # Multi-stage, security-focused Docker image
│   ├── docker-compose.yml   # Docker Compose configuration for local deployment
│   └── docker-compose.prod.yml  # Production-ready Docker Compose configuration
├── kubernetes/              # Kubernetes deployment files
│   ├── deployment.yaml      # Core deployment configuration
│   ├── service.yaml         # Service definition
│   ├── configmap.yaml       # ConfigMap for configuration
│   ├── secret.yaml          # Secret template (do not store actual secrets)
│   ├── network-policy.yaml  # Network policy for security
│   ├── pvc.yaml             # Persistent Volume Claim
│   ├── ingress.yaml         # Ingress controller configuration
│   └── kustomize/           # Kustomize overlays for different environments
│       ├── base/            # Base configuration
│       ├── development/     # Development environment overlay
│       ├── staging/         # Staging environment overlay
│       └── production/      # Production environment overlay
├── cloud/                   # Cloud provider specific deployments
│   ├── aws/                 # AWS deployment templates
│   │   ├── cloudformation/  # CloudFormation templates
│   │   ├── terraform/       # Terraform configurations for AWS
│   │   └── eks/             # EKS-specific configurations
│   ├── azure/               # Azure deployment templates
│   │   ├── arm-templates/   # ARM templates
│   │   ├── terraform/       # Terraform configurations for Azure
│   │   └── aks/             # AKS-specific configurations
│   └── gcp/                 # GCP deployment templates
│       ├── terraform/       # Terraform configurations for GCP
│       └── gke/             # GKE-specific configurations
└── scripts/                 # Deployment automation scripts
    ├── deploy.sh            # Main deployment script
    ├── generate-config.py   # Configuration generator
    └── validate-deployment.py  # Deployment validation tool
```

## Security Considerations

All deployment templates follow these security principles:

1. **Least Privilege**: Services run with minimal permissions
2. **Network Segmentation**: Services are isolated with proper network policies
3. **Secret Management**: Secrets are handled securely and not stored in version control
4. **Container Hardening**: Containers run as non-root with minimal capabilities
5. **Resource Constraints**: Resource limits are defined to prevent DoS scenarios
6. **Security Scanning**: Images are scanned for vulnerabilities before deployment

## Quick Start

### Docker Deployment

```bash
# Clone the repository
git clone https://github.com/ol-s-cloud/circle-core.git
cd circle-core

# Start with Docker Compose
docker-compose -f deployment/docker/docker-compose.yml up -d
```

### Kubernetes Deployment

```bash
# Apply the Kubernetes configurations
kubectl apply -f deployment/kubernetes/

# Or use Kustomize for environment-specific deployment
kubectl apply -k deployment/kubernetes/kustomize/production/
```

### Cloud Provider Deployment

Each cloud provider directory contains detailed instructions for deployment.

## Configuration

Deployment configurations can be customized using environment variables or configuration files. See the [Configuration Documentation](../docs/configuration.md) for details.

## Monitoring and Observability

All deployment templates include configurations for monitoring and observability:

- Health checks for container orchestration
- Prometheus metrics endpoints
- Logging configurations for central log management
- Tracing support for distributed systems

## Updates and Rollbacks

The deployment templates include strategies for safe updates and rollbacks:

- Kubernetes: Rolling updates with health checks
- Docker Compose: Health check-based updates
- Cloud Providers: Infrastructure as Code for versioned deployments

## Support

For deployment issues or questions, please refer to the documentation or open an issue in the GitHub repository.
