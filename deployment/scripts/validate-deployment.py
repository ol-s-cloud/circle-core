#!/usr/bin/env python3
"""
Circle Core Deployment Validator

This script validates a Circle Core deployment to ensure it's running correctly.
It supports different deployment targets (docker, kubernetes, aws, azure, gcp).
"""

import os
import sys
import time
import json
import argparse
import subprocess
import requests
from datetime import datetime

# Default validation endpoints and checks for different deployment targets
VALIDATION_CHECKS = {
    "docker": {
        "health_endpoint": "http://localhost:8000/health",
        "container_names": ["circle-core-api", "postgres", "redis"],
        "timeout_seconds": 30,
        "retry_attempts": 3,
        "retry_delay_seconds": 5
    },
    "kubernetes": {
        "health_endpoint": "http://localhost:8000/health",  # This will be overridden with ingress IP/hostname
        "deployment_names": ["circle-core"],
        "service_names": ["circle-core-service"],
        "namespace": "default",
        "timeout_seconds": 60,
        "retry_attempts": 5,
        "retry_delay_seconds": 10
    },
    "aws": {
        "health_endpoint": None,  # Will be determined from AWS outputs
        "timeout_seconds": 180,
        "retry_attempts": 6,
        "retry_delay_seconds": 30
    },
    "azure": {
        "health_endpoint": None,  # Will be determined from Azure outputs
        "timeout_seconds": 180,
        "retry_attempts": 6,
        "retry_delay_seconds": 30
    },
    "gcp": {
        "health_endpoint": None,  # Will be determined from GCP outputs
        "timeout_seconds": 180,
        "retry_attempts": 6,
        "retry_delay_seconds": 30
    }
}

def check_docker_deployment(config):
    """Validate a Docker deployment"""
    print("Validating Docker deployment...")
    failures = []
    
    # Check if containers are running
    for container in config["container_names"]:
        print(f"Checking container: {container}")
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if container not in result.stdout:
                failures.append(f"Container '{container}' is not running")
                print(f"❌ Container '{container}' is not running")
            else:
                print(f"✅ Container '{container}' is running")
                
                # Check container logs for errors
                log_result = subprocess.run(
                    ["docker", "logs", "--tail", "10", container],
                    capture_output=True,
                    text=True
                )
                
                if "error" in log_result.stdout.lower() or "exception" in log_result.stdout.lower():
                    failures.append(f"Container '{container}' logs contain errors")
                    print(f"⚠️ Container '{container}' logs contain errors")
        except subprocess.CalledProcessError as e:
            failures.append(f"Error checking container '{container}': {str(e)}")
            print(f"❌ Error checking container '{container}': {str(e)}")
    
    # Check health endpoint
    health_url = config["health_endpoint"]
    print(f"Checking health endpoint: {health_url}")
    
    for attempt in range(config["retry_attempts"]):
        try:
            response = requests.get(health_url, timeout=config["timeout_seconds"])
            
            if response.status_code == 200:
                print(f"✅ Health check successful (status code: {response.status_code})")
                try:
                    health_data = response.json()
                    print(f"Health data: {json.dumps(health_data, indent=2)}")
                except:
                    print("Health endpoint did not return valid JSON")
                break
            else:
                print(f"❌ Health check failed (status code: {response.status_code})")
                failures.append(f"Health check failed with status code {response.status_code}")
                
                if attempt < config["retry_attempts"] - 1:
                    print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                    time.sleep(config["retry_delay_seconds"])
        except requests.RequestException as e:
            print(f"❌ Error connecting to health endpoint: {str(e)}")
            failures.append(f"Error connecting to health endpoint: {str(e)}")
            
            if attempt < config["retry_attempts"] - 1:
                print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                time.sleep(config["retry_delay_seconds"])
    
    return failures

def check_kubernetes_deployment(config):
    """Validate a Kubernetes deployment"""
    print("Validating Kubernetes deployment...")
    failures = []
    namespace = config["namespace"]
    
    # Check deployments
    for deployment in config["deployment_names"]:
        print(f"Checking deployment: {deployment}")
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment, "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            deployment_data = json.loads(result.stdout)
            available_replicas = deployment_data.get("status", {}).get("availableReplicas", 0)
            replicas = deployment_data.get("status", {}).get("replicas", 0)
            
            if available_replicas < replicas:
                failures.append(f"Deployment '{deployment}' has {available_replicas}/{replicas} available replicas")
                print(f"❌ Deployment '{deployment}' has {available_replicas}/{replicas} available replicas")
            else:
                print(f"✅ Deployment '{deployment}' has {available_replicas}/{replicas} available replicas")
        except subprocess.CalledProcessError as e:
            failures.append(f"Error checking deployment '{deployment}': {str(e)}")
            print(f"❌ Error checking deployment '{deployment}': {str(e)}")
    
    # Check services
    for service in config["service_names"]:
        print(f"Checking service: {service}")
        try:
            result = subprocess.run(
                ["kubectl", "get", "service", service, "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            service_data = json.loads(result.stdout)
            service_type = service_data.get("spec", {}).get("type", "")
            
            print(f"✅ Service '{service}' exists (type: {service_type})")
            
            # Update health endpoint with service IP/hostname if it's LoadBalancer or NodePort
            if service_type in ["LoadBalancer", "NodePort"]:
                if service_type == "LoadBalancer" and "status" in service_data and "loadBalancer" in service_data["status"]:
                    ip = service_data["status"]["loadBalancer"].get("ingress", [{}])[0].get("ip", "")
                    hostname = service_data["status"]["loadBalancer"].get("ingress", [{}])[0].get("hostname", "")
                    
                    if ip:
                        config["health_endpoint"] = f"http://{ip}:8000/health"
                    elif hostname:
                        config["health_endpoint"] = f"http://{hostname}:8000/health"
                elif service_type == "NodePort":
                    # Get node IP
                    node_result = subprocess.run(
                        ["kubectl", "get", "nodes", "-o", "json"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    node_data = json.loads(node_result.stdout)
                    if node_data.get("items"):
                        node_ip = node_data["items"][0]["status"]["addresses"][0]["address"]
                        
                        # Get node port
                        node_port = service_data["spec"]["ports"][0]["nodePort"]
                        
                        config["health_endpoint"] = f"http://{node_ip}:{node_port}/health"
        except subprocess.CalledProcessError as e:
            failures.append(f"Error checking service '{service}': {str(e)}")
            print(f"❌ Error checking service '{service}': {str(e)}")
    
    # Check health endpoint if available
    if config["health_endpoint"]:
        print(f"Checking health endpoint: {config['health_endpoint']}")
        
        for attempt in range(config["retry_attempts"]):
            try:
                response = requests.get(config["health_endpoint"], timeout=config["timeout_seconds"])
                
                if response.status_code == 200:
                    print(f"✅ Health check successful (status code: {response.status_code})")
                    break
                else:
                    print(f"❌ Health check failed (status code: {response.status_code})")
                    failures.append(f"Health check failed with status code {response.status_code}")
                    
                    if attempt < config["retry_attempts"] - 1:
                        print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                        time.sleep(config["retry_delay_seconds"])
            except requests.RequestException as e:
                print(f"❌ Error connecting to health endpoint: {str(e)}")
                failures.append(f"Error connecting to health endpoint: {str(e)}")
                
                if attempt < config["retry_attempts"] - 1:
                    print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                    time.sleep(config["retry_delay_seconds"])
    else:
        print("⚠️ Health endpoint URL not available, skipping health check")
    
    return failures

def check_aws_deployment(config):
    """Validate an AWS deployment"""
    print("Validating AWS deployment...")
    failures = []
    
    # Get endpoint from Terraform outputs
    try:
        result = subprocess.run(
            ["terraform", "output", "-json", "endpoint"],
            capture_output=True,
            text=True,
            check=True
        )
        
        endpoint = json.loads(result.stdout).strip('"')
        config["health_endpoint"] = f"{endpoint}/health"
    except (subprocess.CalledProcessError, json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Error getting endpoint from Terraform outputs: {str(e)}")
        failures.append(f"Error getting endpoint from Terraform outputs: {str(e)}")
    
    # Check health endpoint if available
    if config.get("health_endpoint"):
        print(f"Checking health endpoint: {config['health_endpoint']}")
        
        for attempt in range(config["retry_attempts"]):
            try:
                response = requests.get(config["health_endpoint"], timeout=config["timeout_seconds"])
                
                if response.status_code == 200:
                    print(f"✅ Health check successful (status code: {response.status_code})")
                    break
                else:
                    print(f"❌ Health check failed (status code: {response.status_code})")
                    failures.append(f"Health check failed with status code {response.status_code}")
                    
                    if attempt < config["retry_attempts"] - 1:
                        print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                        time.sleep(config["retry_delay_seconds"])
            except requests.RequestException as e:
                print(f"❌ Error connecting to health endpoint: {str(e)}")
                failures.append(f"Error connecting to health endpoint: {str(e)}")
                
                if attempt < config["retry_attempts"] - 1:
                    print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                    time.sleep(config["retry_delay_seconds"])
    else:
        print("⚠️ Health endpoint URL not available, skipping health check")
    
    # Check AWS resources
    try:
        print("Checking AWS resources...")
        # Add specific AWS resource checks here (e.g., EC2 instances, RDS, etc.)
        # This would typically involve using boto3 to query AWS resources
        
        # Example: Check ECS service status (if using ECS)
        # Note: This is just an example and would need boto3 library
        """
        import boto3
        ecs = boto3.client('ecs')
        cluster_name = "circle-core-cluster"
        service_name = "circle-core-service"
        
        response = ecs.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        
        if len(response['services']) > 0:
            service = response['services'][0]
            if service['status'] == 'ACTIVE':
                print(f"✅ ECS service '{service_name}' is active")
            else:
                failures.append(f"ECS service '{service_name}' status is {service['status']}")
                print(f"❌ ECS service '{service_name}' status is {service['status']}")
        else:
            failures.append(f"ECS service '{service_name}' not found")
            print(f"❌ ECS service '{service_name}' not found")
        """
    except Exception as e:
        print(f"❌ Error checking AWS resources: {str(e)}")
        failures.append(f"Error checking AWS resources: {str(e)}")
    
    return failures

def check_azure_deployment(config):
    """Validate an Azure deployment"""
    print("Validating Azure deployment...")
    failures = []
    
    # Get endpoint from Terraform outputs
    try:
        result = subprocess.run(
            ["terraform", "output", "-json", "endpoint"],
            capture_output=True,
            text=True,
            check=True
        )
        
        endpoint = json.loads(result.stdout).strip('"')
        config["health_endpoint"] = f"{endpoint}/health"
    except (subprocess.CalledProcessError, json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Error getting endpoint from Terraform outputs: {str(e)}")
        failures.append(f"Error getting endpoint from Terraform outputs: {str(e)}")
    
    # Check health endpoint if available
    if config.get("health_endpoint"):
        print(f"Checking health endpoint: {config['health_endpoint']}")
        
        for attempt in range(config["retry_attempts"]):
            try:
                response = requests.get(config["health_endpoint"], timeout=config["timeout_seconds"])
                
                if response.status_code == 200:
                    print(f"✅ Health check successful (status code: {response.status_code})")
                    break
                else:
                    print(f"❌ Health check failed (status code: {response.status_code})")
                    failures.append(f"Health check failed with status code {response.status_code}")
                    
                    if attempt < config["retry_attempts"] - 1:
                        print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                        time.sleep(config["retry_delay_seconds"])
            except requests.RequestException as e:
                print(f"❌ Error connecting to health endpoint: {str(e)}")
                failures.append(f"Error connecting to health endpoint: {str(e)}")
                
                if attempt < config["retry_attempts"] - 1:
                    print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                    time.sleep(config["retry_delay_seconds"])
    else:
        print("⚠️ Health endpoint URL not available, skipping health check")
    
    # Check Azure resources
    try:
        print("Checking Azure resources...")
        # Add specific Azure resource checks here
        # This would typically involve using azure-sdk-for-python
        
        # Example: Check App Service status (if using Azure App Service)
        # Note: This is just an example and would need azure-mgmt-web library
        """
        from azure.mgmt.web import WebSiteManagementClient
        from azure.identity import DefaultAzureCredential
        
        credential = DefaultAzureCredential()
        web_client = WebSiteManagementClient(credential, subscription_id)
        
        resource_group = "circle-core-rg"
        app_service_name = "circle-core-app"
        
        app_service = web_client.web_apps.get(resource_group, app_service_name)
        
        if app_service.state == "Running":
            print(f"✅ App Service '{app_service_name}' is running")
        else:
            failures.append(f"App Service '{app_service_name}' state is {app_service.state}")
            print(f"❌ App Service '{app_service_name}' state is {app_service.state}")
        """
    except Exception as e:
        print(f"❌ Error checking Azure resources: {str(e)}")
        failures.append(f"Error checking Azure resources: {str(e)}")
    
    return failures

def check_gcp_deployment(config):
    """Validate a GCP deployment"""
    print("Validating GCP deployment...")
    failures = []
    
    # Get endpoint from Terraform outputs
    try:
        result = subprocess.run(
            ["terraform", "output", "-json", "endpoint"],
            capture_output=True,
            text=True,
            check=True
        )
        
        endpoint = json.loads(result.stdout).strip('"')
        config["health_endpoint"] = f"{endpoint}/health"
    except (subprocess.CalledProcessError, json.JSONDecodeError, AttributeError) as e:
        print(f"❌ Error getting endpoint from Terraform outputs: {str(e)}")
        failures.append(f"Error getting endpoint from Terraform outputs: {str(e)}")
    
    # Check health endpoint if available
    if config.get("health_endpoint"):
        print(f"Checking health endpoint: {config['health_endpoint']}")
        
        for attempt in range(config["retry_attempts"]):
            try:
                response = requests.get(config["health_endpoint"], timeout=config["timeout_seconds"])
                
                if response.status_code == 200:
                    print(f"✅ Health check successful (status code: {response.status_code})")
                    break
                else:
                    print(f"❌ Health check failed (status code: {response.status_code})")
                    failures.append(f"Health check failed with status code {response.status_code}")
                    
                    if attempt < config["retry_attempts"] - 1:
                        print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                        time.sleep(config["retry_delay_seconds"])
            except requests.RequestException as e:
                print(f"❌ Error connecting to health endpoint: {str(e)}")
                failures.append(f"Error connecting to health endpoint: {str(e)}")
                
                if attempt < config["retry_attempts"] - 1:
                    print(f"Retrying in {config['retry_delay_seconds']} seconds... (attempt {attempt + 1}/{config['retry_attempts']})")
                    time.sleep(config["retry_delay_seconds"])
    else:
        print("⚠️ Health endpoint URL not available, skipping health check")
    
    # Check GCP resources
    try:
        print("Checking GCP resources...")
        # Add specific GCP resource checks here
        # This would typically involve using google-cloud-python libraries
        
        # Example: Check GKE cluster status (if using GKE)
        # Note: This is just an example and would need google-cloud-container library
        """
        from google.cloud import container_v1
        
        client = container_v1.ClusterManagerClient()
        project_id = "circle-core-project"
        zone = "us-central1-a"
        cluster_id = "circle-core-cluster"
        
        name = f"projects/{project_id}/locations/{zone}/clusters/{cluster_id}"
        
        response = client.get_cluster(name=name)
        
        if response.status == container_v1.Cluster.Status.RUNNING:
            print(f"✅ GKE cluster '{cluster_id}' is running")
        else:
            failures.append(f"GKE cluster '{cluster_id}' status is {response.status}")
            print(f"❌ GKE cluster '{cluster_id}' status is {response.status}")
        """
    except Exception as e:
        print(f"❌ Error checking GCP resources: {str(e)}")
        failures.append(f"Error checking GCP resources: {str(e)}")
    
    return failures

def validate_deployment(environment, target):
    """Validate a Circle Core deployment"""
    print(f"Starting validation for {environment} environment on {target} target...")
    
    # Get validation config
    if target not in VALIDATION_CHECKS:
        print(f"Error: Unsupported target '{target}'")
        sys.exit(1)
    
    config = VALIDATION_CHECKS[target].copy()
    
    # Validate based on target
    failures = []
    
    if target == "docker":
        failures = check_docker_deployment(config)
    elif target == "kubernetes":
        failures = check_kubernetes_deployment(config)
    elif target == "aws":
        failures = check_aws_deployment(config)
    elif target == "azure":
        failures = check_azure_deployment(config)
    elif target == "gcp":
        failures = check_gcp_deployment(config)
    
    # Print validation results
    print("\n======================================")
    print(f"Validation Results - {environment} on {target}")
    print("======================================")
    
    if not failures:
        print("✅ All checks passed!")
        return 0
    else:
        print(f"❌ {len(failures)} failures detected:")
        for i, failure in enumerate(failures, 1):
            print(f"  {i}. {failure}")
        return 1

def main():
    """Main function to parse arguments and validate deployment"""
    parser = argparse.ArgumentParser(description='Validate Circle Core deployment')
    parser.add_argument('-e', '--environment', required=True,
                        choices=['development', 'staging', 'production'],
                        help='Deployment environment')
    parser.add_argument('-t', '--target', required=True,
                        choices=['docker', 'kubernetes', 'aws', 'azure', 'gcp'],
                        help='Deployment target')
    
    args = parser.parse_args()
    
    return validate_deployment(args.environment, args.target)

if __name__ == '__main__':
    sys.exit(main())
