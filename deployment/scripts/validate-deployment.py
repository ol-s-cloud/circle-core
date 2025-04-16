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
        
        # Check ECS service if using ECS
        try:
            ecs_result = subprocess.run(
                ["aws", "ecs", "describe-services", "--cluster", "circle-core", "--services", "circle-core"],
                capture_output=True,
                text=True,
                check=True
            )
            
            ecs_data = json.loads(ecs_result.stdout)
            if ecs_data.get("services"):
                service = ecs_data["services"][0]
                desired_count = service.get("desiredCount", 0)
                running_count = service.get("runningCount", 0)
                
                if running_count < desired_count:
                    failures.append(f"ECS service has {running_count}/{desired_count} running tasks")
                    print(f"❌ ECS service has {running_count}/{desired_count} running tasks")
                else:
                    print(f"✅ ECS service has {running_count}/{desired_count} running tasks")
        except subprocess.CalledProcessError:
            # ECS might not be used, so this is not a critical failure
            print("⚠️ ECS service check skipped (ECS might not be used)")
        
        # Check Lambda function if using Lambda
        try:
            lambda_result = subprocess.run(
                ["aws", "lambda", "get-function", "--function-name", "circle-core"],
                capture_output=True,
                text=True,
                check=True
            )
            
            lambda_data = json.loads(lambda_result.stdout)
            if lambda_data.get("Configuration"):
                state = lambda_data["Configuration"].get("State")
                last_update = lambda_data["Configuration"].get("LastUpdateStatus")
                
                if state != "Active" or last_update != "Successful":
                    failures.append(f"Lambda function state: {state}, last update: {last_update}")
                    print(f"❌ Lambda function state: {state}, last update: {last_update}")
                else:
                    print(f"✅ Lambda function is active and updated successfully")
        except subprocess.CalledProcessError:
            # Lambda might not be used, so this is not a critical failure
            print("⚠️ Lambda function check skipped (Lambda might not be used)")
        
    except Exception as e:
        failures.append(f"Error checking AWS resources: {str(e)}")
        print(f"❌ Error checking AWS resources: {str(e)}")
    
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
    
    # Check health endpoint
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
        # Check App Service if using App Service
        try:
            appservice_result = subprocess.run(
                ["az", "webapp", "show", "--name", "circle-core", "--resource-group", "circle-core"],
                capture_output=True,
                text=True,
                check=True
            )
            
            appservice_data = json.loads(appservice_result.stdout)
            state = appservice_data.get("state", "")
            
            if state != "Running":
                failures.append(f"App Service state: {state}")
                print(f"❌ App Service state: {state}")
            else:
                print(f"✅ App Service is running")
        except subprocess.CalledProcessError:
            # App Service might not be used, so this is not a critical failure
            print("⚠️ App Service check skipped (App Service might not be used)")
        
        # Check AKS cluster if using AKS
        try:
            aks_result = subprocess.run(
                ["az", "aks", "show", "--name", "circle-core", "--resource-group", "circle-core"],
                capture_output=True,
                text=True,
                check=True
            )
            
            aks_data = json.loads(aks_result.stdout)
            provisioning_state = aks_data.get("provisioningState", "")
            
            if provisioning_state != "Succeeded":
                failures.append(f"AKS cluster provisioning state: {provisioning_state}")
                print(f"❌ AKS cluster provisioning state: {provisioning_state}")
            else:
                print(f"✅ AKS cluster is provisioned successfully")
        except subprocess.CalledProcessError:
            # AKS might not be used, so this is not a critical failure
            print("⚠️ AKS cluster check skipped (AKS might not be used)")
        
    except Exception as e:
        failures.append(f"Error checking Azure resources: {str(e)}")
        print(f"❌ Error checking Azure resources: {str(e)}")
    
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
    
    # Check health endpoint
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
        # Check GKE cluster if using GKE
        try:
            gke_result = subprocess.run(
                ["gcloud", "container", "clusters", "describe", "circle-core", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            gke_data = json.loads(gke_result.stdout)
            status = gke_data.get("status", "")
            
            if status != "RUNNING":
                failures.append(f"GKE cluster status: {status}")
                print(f"❌ GKE cluster status: {status}")
            else:
                print(f"✅ GKE cluster is running")
        except subprocess.CalledProcessError:
            # GKE might not be used, so this is not a critical failure
            print("⚠️ GKE cluster check skipped (GKE might not be used)")
        
        # Check Cloud Run service if using Cloud Run
        try:
            cloudrun_result = subprocess.run(
                ["gcloud", "run", "services", "describe", "circle-core", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            cloudrun_data = json.loads(cloudrun_result.stdout)
            conditions = cloudrun_data.get("status", {}).get("conditions", [])
            ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
            
            if not ready:
                failures.append("Cloud Run service is not ready")
                print("❌ Cloud Run service is not ready")
            else:
                print("✅ Cloud Run service is ready")
        except subprocess.CalledProcessError:
            # Cloud Run might not be used, so this is not a critical failure
            print("⚠️ Cloud Run service check skipped (Cloud Run might not be used)")
        
    except Exception as e:
        failures.append(f"Error checking GCP resources: {str(e)}")
        print(f"❌ Error checking GCP resources: {str(e)}")
    
    return failures

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Validate Circle Core deployment')
    parser.add_argument('-e', '--environment', required=True,
                        choices=['development', 'staging', 'production'],
                        help='Deployment environment')
    parser.add_argument('-t', '--target', required=True,
                        choices=['docker', 'kubernetes', 'aws', 'azure', 'gcp'],
                        help='Deployment target')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    print(f"Validating {args.environment} deployment on {args.target}...")
    
    # Get the validation configuration for the target
    if args.target not in VALIDATION_CHECKS:
        print(f"Error: Unknown target '{args.target}'")
        sys.exit(1)
    
    config = VALIDATION_CHECKS[args.target].copy()
    
    # Adjust configuration based on environment
    if args.environment == "production":
        config["retry_attempts"] = config["retry_attempts"] + 2
    
    # Perform validation based on target
    failures = []
    if args.target == "docker":
        failures = check_docker_deployment(config)
    elif args.target == "kubernetes":
        failures = check_kubernetes_deployment(config)
    elif args.target == "aws":
        failures = check_aws_deployment(config)
    elif args.target == "azure":
        failures = check_azure_deployment(config)
    elif args.target == "gcp":
        failures = check_gcp_deployment(config)
    
    # Print validation results
    print("\n======================================")
    print("Validation Results")
    print("======================================")
    
    if failures:
        print(f"❌ Validation failed with {len(failures)} issues:")
        for i, failure in enumerate(failures, 1):
            print(f"  {i}. {failure}")
        sys.exit(1)
    else:
        print("✅ Validation successful! No issues found.")
        sys.exit(0)

if __name__ == '__main__':
    main()
