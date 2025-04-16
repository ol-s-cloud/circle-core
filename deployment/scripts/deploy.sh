#!/bin/bash
# Circle Core Deployment Script
# This script automates the deployment of Circle Core in various environments

set -e

# Default values
ENVIRONMENT="development"
TARGET="docker"
VERSION="latest"
CONFIG_FILE=""
VERBOSE=0

# Help message
show_help() {
    echo "Circle Core Deployment Script"
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV   Set deployment environment (development, staging, production)"
    echo "  -t, --target TARGET     Set deployment target (docker, kubernetes, aws, azure, gcp)"
    echo "  -v, --version VERSION   Set version to deploy (default: latest)"
    echo "  -c, --config FILE       Specify a configuration file"
    echo "  --verbose               Enable verbose output"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment production --target docker"
    echo "  $0 -e staging -t kubernetes"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -e|--environment)
            ENVIRONMENT="$2"
            shift
            shift
            ;;
        -t|--target)
            TARGET="$2"
            shift
            shift
            ;;
        -v|--version)
            VERSION="$2"
            shift
            shift
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo "Error: Invalid environment. Must be development, staging, or production."
    exit 1
fi

# Validate target
if [[ ! "$TARGET" =~ ^(docker|kubernetes|aws|azure|gcp)$ ]]; then
    echo "Error: Invalid target. Must be docker, kubernetes, aws, azure, or gcp."
    exit 1
fi

# Log settings if verbose
if [ $VERBOSE -eq 1 ]; then
    echo "Deployment settings:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Target: $TARGET"
    echo "  Version: $VERSION"
    echo "  Config: $CONFIG_FILE"
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Circle Core Deployment"
echo "Environment: $ENVIRONMENT"
echo "Target: $TARGET"
echo "========================================"

# Generate configuration if needed
if [ -n "$CONFIG_FILE" ]; then
    echo "Using configuration file: $CONFIG_FILE"
    # Copy or process the configuration file
    if [ $VERBOSE -eq 1 ]; then
        echo "Processing configuration file..."
    fi
else
    echo "Generating configuration for $ENVIRONMENT environment..."
    # Generate default configuration for the environment
    python "$SCRIPT_DIR/generate-config.py" -e "$ENVIRONMENT" -o "$REPO_ROOT/config/$ENVIRONMENT.json"
    CONFIG_FILE="$REPO_ROOT/config/$ENVIRONMENT.json"
    echo "Configuration generated: $CONFIG_FILE"
fi

# Deploy based on target
case $TARGET in
    docker)
        echo "Deploying with Docker..."
        
        # Set environment variables
        export CIRCLE_VERSION=$VERSION
        export CIRCLE_ENV=$ENVIRONMENT
        
        # Choose the appropriate docker-compose file
        if [ "$ENVIRONMENT" == "production" ]; then
            COMPOSE_FILE="$REPO_ROOT/deployment/docker/docker-compose.prod.yml"
        else
            COMPOSE_FILE="$REPO_ROOT/deployment/docker/docker-compose.yml"
        fi
        
        # Create .env file
        echo "Creating .env file for Docker Compose..."
        ENV_FILE="$REPO_ROOT/deployment/docker/.env.$ENVIRONMENT"
        touch "$ENV_FILE"
        
        # Generate secure passwords if not already set
        if ! grep -q "POSTGRES_PASSWORD" "$ENV_FILE"; then
            echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)" >> "$ENV_FILE"
        fi
        
        if ! grep -q "REDIS_PASSWORD" "$ENV_FILE"; then
            echo "REDIS_PASSWORD=$(openssl rand -base64 24)" >> "$ENV_FILE"
        fi
        
        if ! grep -q "GRAFANA_PASSWORD" "$ENV_FILE" && [ "$ENVIRONMENT" == "production" ]; then
            echo "GRAFANA_PASSWORD=$(openssl rand -base64 24)" >> "$ENV_FILE"
        fi
        
        # Ensure encryption key is set
        if ! grep -q "CIRCLE_ENCRYPTION_KEY" "$ENV_FILE"; then
            echo "CIRCLE_ENCRYPTION_KEY=$(openssl rand -base64 32)" >> "$ENV_FILE"
        fi
        
        # Copy configuration file
        mkdir -p "$REPO_ROOT/deployment/docker/config"
        cp "$CONFIG_FILE" "$REPO_ROOT/deployment/docker/config/config.json"
        
        # Deploy with Docker Compose
        cd "$REPO_ROOT"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
        
        echo "Docker deployment completed!"
        ;;
        
    kubernetes)
        echo "Deploying to Kubernetes..."
        
        # Choose the appropriate Kustomize overlay
        KUSTOMIZE_DIR="$REPO_ROOT/deployment/kubernetes/kustomize/$ENVIRONMENT"
        
        if [ ! -d "$KUSTOMIZE_DIR" ]; then
            echo "Error: Kustomize overlay for $ENVIRONMENT not found."
            exit 1
        fi
        
        # Apply Kubernetes resources
        echo "Applying Kubernetes resources..."
        kubectl apply -k "$KUSTOMIZE_DIR"
        
        echo "Kubernetes deployment completed!"
        ;;
        
    aws)
        echo "Deploying to AWS..."
        
        # Deploy to AWS using CloudFormation or Terraform
        if [ -d "$REPO_ROOT/deployment/cloud/aws/terraform" ]; then
            cd "$REPO_ROOT/deployment/cloud/aws/terraform"
            
            # Initialize Terraform
            echo "Initializing Terraform..."
            terraform init -backend-config="environment=$ENVIRONMENT"
            
            # Create variables file
            echo "Creating Terraform variables file..."
            cat > terraform.tfvars <<EOF
environment = "$ENVIRONMENT"
circle_version = "$VERSION"
EOF
            
            # Apply Terraform configuration
            echo "Applying Terraform configuration..."
            terraform apply -auto-approve -var-file=terraform.tfvars
            
            echo "AWS deployment completed!"
        else
            echo "Error: AWS Terraform configuration not found."
            exit 1
        fi
        ;;
        
    azure)
        echo "Deploying to Azure..."
        
        # Deploy to Azure using ARM Templates or Terraform
        if [ -d "$REPO_ROOT/deployment/cloud/azure/terraform" ]; then
            cd "$REPO_ROOT/deployment/cloud/azure/terraform"
            
            # Initialize Terraform
            echo "Initializing Terraform..."
            terraform init -backend-config="environment=$ENVIRONMENT"
            
            # Create variables file
            echo "Creating Terraform variables file..."
            cat > terraform.tfvars <<EOF
environment = "$ENVIRONMENT"
circle_version = "$VERSION"
EOF
            
            # Apply Terraform configuration
            echo "Applying Terraform configuration..."
            terraform apply -auto-approve -var-file=terraform.tfvars
            
            echo "Azure deployment completed!"
        else
            echo "Error: Azure Terraform configuration not found."
            exit 1
        fi
        ;;
        
    gcp)
        echo "Deploying to GCP..."
        
        # Deploy to GCP using Terraform
        if [ -d "$REPO_ROOT/deployment/cloud/gcp/terraform" ]; then
            cd "$REPO_ROOT/deployment/cloud/gcp/terraform"
            
            # Initialize Terraform
            echo "Initializing Terraform..."
            terraform init -backend-config="environment=$ENVIRONMENT"
            
            # Create variables file
            echo "Creating Terraform variables file..."
            cat > terraform.tfvars <<EOF
environment = "$ENVIRONMENT"
circle_version = "$VERSION"
EOF
            
            # Apply Terraform configuration
            echo "Applying Terraform configuration..."
            terraform apply -auto-approve -var-file=terraform.tfvars
            
            echo "GCP deployment completed!"
        else
            echo "Error: GCP Terraform configuration not found."
            exit 1
        fi
        ;;
esac

# Validate deployment
if [ $VERBOSE -eq 1 ]; then
    echo "Validating deployment..."
    python "$SCRIPT_DIR/validate-deployment.py" -e "$ENVIRONMENT" -t "$TARGET"
fi

echo "Deployment process finished successfully!"
