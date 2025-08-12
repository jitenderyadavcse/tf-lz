# Import necessary modules
from mcp.server import FastMCP
import requests
import json
import os
import re
import argparse
import uvicorn
import sys
import datetime
import math
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configuration extracted from Flask code
API_BASE_URL = "https://app.terraform.io/api/v2"
TFC_API_TOKEN = "pGSP98eUfrIyzA.atlasv1.jYve4Bz95m2JfWcdn2pl4flRYDomtC561qYP8WtrO4KCttbbqARAOpkOw9NILGAF1K8"
ORGANIZATION = "Lennar"
GITHUB_TOKEN = "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"  # Token for private GitHub repositories

# Initialize the FastMCP server
mcp = FastMCP("lennar-aws-infrastructure")

# Helper functions - defined first to avoid import order issues
def generate_providers_tf_content(provider: str = "aws") -> str:
    """Generate providers.tf content based on the provider"""
    if provider == "azu" or provider == "azure":
        return '''# Provider configurations for Azure
# Generated automatically by Lennar MCP Server

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  
  subscription_id = var.subscription_id
  
  default_tags {
    tags = var.common_tags
  }
}'''
    else:
        return '''# Provider configurations
# Generated automatically by Lennar MCP Server

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.common_tags
  }
}'''

def generate_backend_tf_content(project_name: str) -> str:
    """Generate backend.tf content"""
    return f'''# Backend configuration
# Generated automatically by Lennar MCP Server

terraform {{
  backend "remote" {{
    organization = "Lennar"

    workspaces {{
      prefix = "{project_name}-"
    }}
  }}
}}'''


@mcp.tool()
def get_terraform_module_details(name: str, provider: str, version: str = "latest") -> str:
    """Get comprehensive details about a Terraform module from Lennar's private Terraform Cloud registry
    
    Args:
        name: The name of the module (e.g., 'vpc', 'lambda', 'aks')
        provider: The provider for the module (e.g., 'aws', 'azu' for Azure)
        version: The version of the module (default: 'latest')
    
    Returns:
        JSON string containing complete module details including inputs, outputs, main.tf content, and usage examples
    """
    try:
        # Map 'azu' to 'azure' for display purposes but keep 'azu' for API calls
        display_provider = 'azure' if provider == 'azu' else provider
        
        headers = {
            "Authorization": f"Bearer {TFC_API_TOKEN}",
            "Content-Type": "application/vnd.api+json"
        }
        
        # Get module information from Lennar's private registry using the exact provider format
        module_url = f"{API_BASE_URL}/organizations/{ORGANIZATION}/registry-modules/private/{ORGANIZATION}/{name}/{provider}"
        
        response = requests.get(module_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            return json.dumps({"error": f"Module {ORGANIZATION}/{name}/{provider} not found in Lennar's private registry"})
        
        if response.status_code == 401:
            return json.dumps({"error": "Unauthorized - check TFC API token"})
        
        response.raise_for_status()
        module_data = response.json()
        
        # Get versions list
        versions_url = f"{API_BASE_URL}/organizations/{ORGANIZATION}/registry-modules/private/{ORGANIZATION}/{name}/{provider}/versions"
        versions_response = requests.get(versions_url, headers=headers, timeout=30)
        versions_data = versions_response.json() if versions_response.status_code == 200 else {}
        
        # Extract module information
        module_info = module_data.get("data", {})
        attributes = module_info.get("attributes", {})
        
        # Determine the version to get detailed info for
        target_version = version
        if version == "latest" and attributes.get("version-statuses"):
            target_version = attributes.get("version-statuses", [{}])[0].get("version", "")
        
        # Get detailed version information including inputs, outputs, and files
        version_detail_url = f"{versions_url}/{target_version}"
        version_response = requests.get(version_detail_url, headers=headers, timeout=30)
        
        if version_response.status_code == 200:
            version_data = version_response.json()
            version_attributes = version_data.get("data", {}).get("attributes", {})
            
            # Get configuration version details for inputs/outputs
            config_version_url = f"{version_detail_url}/configuration-version"
            config_response = requests.get(config_version_url, headers=headers, timeout=30)
            config_data = config_response.json() if config_response.status_code == 200 else {}
            
            # Get module files (main.tf, variables.tf, outputs.tf, etc.)
            files_url = f"{config_version_url}/configuration-version-files"
            files_response = requests.get(files_url, headers=headers, timeout=30)
            files_data = files_response.json() if files_response.status_code == 200 else {}
            
        else:
            version_attributes = {}
            config_data = {}
            files_data = {}
        
        # Extract input variables
        inputs = []
        if "inputs" in version_attributes:
            for input_var in version_attributes.get("inputs", []):
                inputs.append({
                    "name": input_var.get("name", ""),
                    "type": input_var.get("type", ""),
                    "description": input_var.get("description", ""),
                    "default": input_var.get("default"),
                    "required": input_var.get("required", True),
                    "sensitive": input_var.get("sensitive", False)
                })
        
        # Extract output variables
        outputs = []
        if "outputs" in version_attributes:
            for output_var in version_attributes.get("outputs", []):
                outputs.append({
                    "name": output_var.get("name", ""),
                    "description": output_var.get("description", ""),
                    "sensitive": output_var.get("sensitive", False)
                })
        
        # Extract file contents
        module_files = {}
        if files_data and "data" in files_data:
            for file_info in files_data["data"]:
                file_attrs = file_info.get("attributes", {})
                filename = file_attrs.get("filename", "")
                content = file_attrs.get("content", "")
                
                if filename in ["main.tf", "variables.tf", "outputs.tf", "versions.tf", "README.md"]:
                    module_files[filename] = content
        
        # Generate usage example with correct provider display
        usage_example = generate_module_usage_example(name, provider, inputs, ORGANIZATION)
        
        # Format the comprehensive response
        result = {
            "organization": ORGANIZATION,
            "module": f"{ORGANIZATION}/{name}/{provider}",
            "name": attributes.get("name", name),
            "provider": display_provider,  # Show 'azure' instead of 'azu' in results
            "provider_code": provider,      # Keep original 'azu' for reference
            "description": version_attributes.get("description", "No description available"),
            "source": version_attributes.get("source", ""),
            "status": attributes.get("status", ""),
            "version_requested": version,
            "current_version": target_version,
            "available_versions": [v.get("attributes", {}).get("version", "") for v in versions_data.get("data", [])][:10],
            "created_at": attributes.get("created-at", ""),
            "updated_at": attributes.get("updated-at", ""),
            "vcs_repo": attributes.get("vcs-repo", {}),
            "input_variables": inputs,
            "output_variables": outputs,
            "module_files": module_files,
            "usage_example": usage_example,
            "terraform_version": version_attributes.get("terraform-version", ""),
            "providers": version_attributes.get("providers", []),
            "dependencies": version_attributes.get("dependencies", []),
            "readme": version_attributes.get("readme", module_files.get("README.md", "No README available"))[:2000] + "..." if len(version_attributes.get("readme", module_files.get("README.md", ""))) > 2000 else version_attributes.get("readme", module_files.get("README.md", "No README available"))
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to fetch module details from Lennar registry: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

def generate_module_usage_example(name: str, provider: str, inputs: list, organization: str) -> str:
    """Generate a usage configuration for the module based on ONLY its actual input variables"""
    
    config = f'''# Configuration for {organization}/{name}/{provider} module
module "{name}" {{
  source = "app.terraform.io/{organization}/{name}/{provider}"
  
'''
    
    # Only add variables that actually exist in the module
    if not inputs:
        config += '  # No input variables found in module\n'
    else:
        for input_var in inputs:
            var_name = input_var.get("name", "")
            var_type = input_var.get("type", "string")
            default_val = input_var.get("default")
            description = input_var.get("description", "")
            required = input_var.get("required", True)
            
            # Only include required variables or variables without defaults
            if required and default_val is None:
                # Use placeholder values that indicate they need to be filled
                config += f'  {var_name} = var.{var_name}  # {description}\n'
            elif not required and default_val is not None:
                # Show optional variables as comments
                config += f'  # {var_name} = {json.dumps(default_val)}  # Optional: {description}\n'
    
    config += "}\n"
    return config

def generate_professional_value(var_name: str, module_name: str) -> str:
    """Generate professional values based on variable name patterns"""
    var_name_lower = var_name.lower()
    
    # Common patterns for professional naming
    if "bucket" in var_name_lower:
        return f"lennar-{module_name}-bucket"
    elif "function" in var_name_lower or "lambda" in var_name_lower:
        return f"lennar-{module_name}-function"
    elif "role" in var_name_lower:
        return f"lennar-{module_name}-role"
    elif "policy" in var_name_lower:
        return f"lennar-{module_name}-policy"
    elif "key" in var_name_lower and "kms" in var_name_lower:
        return f"lennar-{module_name}-key"
    elif "vpc" in var_name_lower:
        return f"lennar-{module_name}-vpc"
    elif "subnet" in var_name_lower:
        return f"lennar-{module_name}-subnet"
    elif "sg" in var_name_lower or "security" in var_name_lower:
        return f"lennar-{module_name}-sg"
    elif "db" in var_name_lower or "database" in var_name_lower:
        return f"lennar-{module_name}-db"
    elif "cluster" in var_name_lower:
        return f"lennar-{module_name}-cluster"
    elif "workspace" in var_name_lower:
        return f"lennar-{module_name}-workspace"
    elif "repository" in var_name_lower or "repo" in var_name_lower:
        return f"lennar-{module_name}-repo"
    elif "domain" in var_name_lower:
        return f"{module_name}.lennar.com"
    elif "prefix" in var_name_lower:
        return f"lennar-{module_name}"
    elif "suffix" in var_name_lower:
        return f"{module_name}-lennar"
    else:
        return f"lennar-{module_name}-resource"

def generate_number_value(var_name: str) -> int:
    """Generate appropriate number values based on variable name"""
    var_name_lower = var_name.lower()
    
    if "port" in var_name_lower:
        if "http" in var_name_lower:
            return 80
        elif "https" in var_name_lower:
            return 443
        elif "ssh" in var_name_lower:
            return 22
        else:
            return 8080
    elif "count" in var_name_lower or "size" in var_name_lower:
        if "min" in var_name_lower:
            return 1
        elif "max" in var_name_lower:
            return 10
        else:
            return 3
    elif "timeout" in var_name_lower:
        return 300
    elif "memory" in var_name_lower:
        return 128
    elif "cpu" in var_name_lower:
        return 256
    else:
        return 1

def generate_list_value(var_name: str, module_name: str) -> str:
    """Generate appropriate list values based on variable name"""
    var_name_lower = var_name.lower()
    
    if "subnet" in var_name_lower:
        return '["subnet-12345", "subnet-67890"]'
    elif "sg" in var_name_lower or "security" in var_name_lower:
        return f'["lennar-{module_name}-sg"]'
    elif "az" in var_name_lower or "availability" in var_name_lower:
        return '["us-east-1a", "us-east-1b"]'
    elif "cidr" in var_name_lower:
        return '["10.0.1.0/24", "10.0.2.0/24"]'
    elif "domain" in var_name_lower:
        return f'["{module_name}.lennar.com"]'
    elif "tag" in var_name_lower:
        return '["production", "managed"]'
    else:
        return f'["lennar-{module_name}-item"]'

# Define a resource (data the AI can access)
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}! Welcome to the MCP Lennar"

@mcp.tool()
def check_lennar_module(module_name: str, provider: str = "aws") -> str:
    """Check if a specified AWS or Azure module exists in the Lennar private repository
    
    Args:
        module_name: The name of the module (e.g., 'lambda', 'vpc', 's3', 'aks')
        provider: The provider for the module (default: 'aws', can be 'azu' for Azure)
    
    Returns:
        JSON string indicating if module exists and basic info, or error message
    """
    try:
        # Map 'azure' to 'azu' for API calls if needed
        api_provider = 'azu' if provider == 'azure' else provider
        display_provider = 'azure' if api_provider == 'azu' else api_provider
        
        headers = {
            "Authorization": f"Bearer {TFC_API_TOKEN}",
            "Content-Type": "application/vnd.api+json"
        }
        
        # Check if module exists in Lennar's private registry using correct provider code
        module_url = f"{API_BASE_URL}/organizations/{ORGANIZATION}/registry-modules/private/{ORGANIZATION}/{module_name}/{api_provider}"
        
        response = requests.get(module_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            return json.dumps({
                "success": False,
                "error": f"Module {ORGANIZATION}/{module_name}/{api_provider} not found in Lennar's private registry",
                "module_exists": False
            })
        
        if response.status_code == 401:
            return json.dumps({
                "success": False,
                "error": "Unauthorized - check TFC API token",
                "module_exists": False
            })
        
        response.raise_for_status()
        module_data = response.json()
        
        # Extract basic module information
        module_info = module_data.get("data", {})
        attributes = module_info.get("attributes", {})
        
        result = {
            "success": True,
            "module_exists": True,
            "module_name": module_name,
            "provider": display_provider,
            "provider_code": api_provider,
            "organization": ORGANIZATION,
            "status": attributes.get("status", ""),
            "current_version": attributes.get("version-statuses", [{}])[0].get("version", "") if attributes.get("version-statuses") else "",
            "created_at": attributes.get("created-at", ""),
            "repository_url": attributes.get("vcs-repo", {}).get("repository-http-url", ""),
            "message": f"Module {ORGANIZATION}/{module_name}/{api_provider} found and verified"
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to check module in Lennar registry: {str(e)}",
            "module_exists": False
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}",
            "module_exists": False
        })

@mcp.tool()
def get_github_module_files(module_name: str, provider: str = "aws") -> str:
    """Get module files directly from the appropriate branch of GitHub repository in modules-len organization
    
    This tool checks the latest release tag to determine which branch to use:
    - If latest release is from 'develop' branch, fetch from develop
    - If latest release is from 'main' branch, fetch from main
    - Defaults to main if no releases found
    
    Args:
        module_name: The name of the module
        provider: The provider for the module (e.g., 'aws', 'azu' for Azure)
    
    Returns:
        JSON string containing file contents from the appropriate GitHub repository branch
    """
    try:
        # For GitHub repository naming, use 'azu' for Azure modules
        github_provider = provider  # Keep original provider code for GitHub repo naming
        display_provider = 'azure' if provider == 'azu' else provider
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        repo_name = f"terraform-{github_provider}-{module_name}"
        
        # Step 1: Get the latest release to determine which branch to use
        releases_url = f"https://api.github.com/repos/modules-len/{repo_name}/releases/latest"
        release_response = requests.get(releases_url, headers=headers, timeout=30)
        
        target_branch = "main"  # Default to main branch
        release_info = {}
        
        if release_response.status_code == 200:
            release_data = release_response.json()
            release_info = {
                "tag_name": release_data.get("tag_name", ""),
                "name": release_data.get("name", ""),
                "published_at": release_data.get("published_at", ""),
                "target_commitish": release_data.get("target_commitish", "main")
            }
            
            # Determine target branch from release
            target_commitish = release_data.get("target_commitish", "main")
            if target_commitish in ["develop", "development", "dev"]:
                target_branch = "develop"
            elif target_commitish == "main":
                target_branch = "main"
            else:
                # If it's a specific commit hash or other branch, default to main
                target_branch = "main"
                
            print(f"Latest release '{release_info['tag_name']}' found, using branch: {target_branch}")
        else:
            print(f"No releases found for {repo_name}, defaulting to main branch")
            release_info = {"message": "No releases found, using main branch"}
        
        # Step 2: Fetch repository contents from the determined branch
        base_url = f"https://api.github.com/repos/modules-len/{repo_name}/contents"
        
        # Get repository file list from target branch
        response = requests.get(f"{base_url}?ref={target_branch}", headers=headers, timeout=30)
        
        if response.status_code == 404:
            return json.dumps({"error": f"Repository modules-len/{repo_name} not found or branch {target_branch} does not exist"})
        
        response.raise_for_status()
        files_list = response.json()
        
        # Get all .tf files and README files from target branch
        terraform_files = {}
        file_metadata = {}
        target_extensions = [".tf", ".md", ".txt"]
        
        # Function to recursively fetch files from directories
        def fetch_files_recursively(items, current_path=""):
            files_found = {}
            metadata_found = {}
            
            for item in items:
                item_name = item.get("name", "")
                item_type = item.get("type", "")
                item_path = f"{current_path}/{item_name}" if current_path else item_name
                
                # Check if it's a file with target extension
                if item_type == "file" and any(item_name.lower().endswith(ext) for ext in target_extensions):
                    try:
                        # Fetch file content from target branch using contents API
                        file_content_url = f"https://api.github.com/repos/modules-len/{repo_name}/contents/{item_path}?ref={target_branch}"
                        file_response = requests.get(file_content_url, headers=headers, timeout=30)
                        
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            
                            # Decode base64 content
                            import base64
                            if file_data.get("encoding") == "base64":
                                content = base64.b64decode(file_data.get("content", "")).decode('utf-8')
                                files_found[item_path] = content
                                
                                # Store metadata
                                metadata_found[item_path] = {
                                    "size": file_data.get("size", 0),
                                    "sha": file_data.get("sha", ""),
                                    "download_url": file_data.get("download_url", ""),
                                    "html_url": file_data.get("html_url", ""),
                                    "last_modified": file_data.get("git_url", "").split("/")[-1] if file_data.get("git_url") else ""
                                }
                    except Exception as e:
                        print(f"Error fetching {item_path}: {str(e)}")
                        continue
                
                # If it's a directory, fetch its contents recursively
                elif item_type == "dir":
                    try:
                        dir_url = f"https://api.github.com/repos/modules-len/{repo_name}/contents/{item_path}?ref={target_branch}"
                        dir_response = requests.get(dir_url, headers=headers, timeout=30)
                        
                        if dir_response.status_code == 200:
                            dir_items = dir_response.json()
                            sub_files, sub_metadata = fetch_files_recursively(dir_items, item_path)
                            files_found.update(sub_files)
                            metadata_found.update(sub_metadata)
                    except Exception as e:
                        print(f"Error fetching directory {item_path}: {str(e)}")
                        continue
            
            return files_found, metadata_found
        
        # Fetch all files recursively
        terraform_files, file_metadata = fetch_files_recursively(files_list)
        
        # Parse variables.tf for input variables
        input_variables = []
        variables_files = [k for k in terraform_files.keys() if k.endswith("variables.tf")]
        for var_file in variables_files:
            parsed_vars = parse_terraform_variables(terraform_files[var_file])
            input_variables.extend(parsed_vars)
        
        # Parse outputs.tf for output variables
        output_variables = []
        output_files = [k for k in terraform_files.keys() if k.endswith("outputs.tf")]
        for out_file in output_files:
            parsed_outputs = parse_terraform_outputs(terraform_files[out_file])
            output_variables.extend(parsed_outputs)
        
        # Get repository information
        repo_info_url = f"https://api.github.com/repos/modules-len/{repo_name}"
        repo_info_response = requests.get(repo_info_url, headers=headers, timeout=30)
        repo_info = repo_info_response.json() if repo_info_response.status_code == 200 else {}
        
        # Get latest commit information from target branch
        commits_url = f"https://api.github.com/repos/modules-len/{repo_name}/commits/{target_branch}"
        commits_response = requests.get(commits_url, headers=headers, timeout=30)
        latest_commit = commits_response.json() if commits_response.status_code == 200 else {}
        
        # Organize files by type
        organized_files = {
            "terraform_files": {k: v for k in terraform_files.keys() if k.endswith('.tf')},
            "documentation_files": {k: v for k in terraform_files.keys() if k.endswith(('.md', '.txt'))},
            "all_files": terraform_files
        }
        
        # Extract README content
        readme_content = ""
        readme_files = [k for k in terraform_files.keys() if 'readme' in k.lower()]
        if readme_files:
            readme_content = terraform_files[readme_files[0]]
        
        result = {
            "success": True,
            "repository": f"modules-len/{repo_name}",
            "provider": display_provider,
            "provider_code": provider,
            "branch_used": target_branch,
            "release_info": release_info,
            "files": organized_files,
            "file_metadata": file_metadata,
            "input_variables": input_variables,
            "output_variables": output_variables,
            "file_count": len(terraform_files),
            "terraform_file_count": len(organized_files["terraform_files"]),
            "documentation_file_count": len(organized_files["documentation_files"]),
            "readme_content": readme_content[:2000] + "..." if len(readme_content) > 2000 else readme_content,
            "repository_info": {
                "description": repo_info.get("description", ""),
                "created_at": repo_info.get("created_at", ""),
                "updated_at": repo_info.get("updated_at", ""),
                "pushed_at": repo_info.get("pushed_at", ""),
                "default_branch": repo_info.get("default_branch", "main"),
                "size": repo_info.get("size", 0),
                "language": repo_info.get("language", ""),
                "topics": repo_info.get("topics", [])
            },
            "latest_commit": {
                "sha": latest_commit.get("sha", "")[:8] if latest_commit.get("sha") else "",
                "message": latest_commit.get("commit", {}).get("message", ""),
                "author": latest_commit.get("commit", {}).get("author", {}).get("name", ""),
                "date": latest_commit.get("commit", {}).get("author", {}).get("date", ""),
                "branch": target_branch
            }
        }
        
        return json.dumps(result, indent=2)
        
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to fetch files from GitHub: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})

def parse_terraform_variables(variables_content: str) -> List[Dict]:
    """Enhanced parsing of variables.tf content to extract variable definitions more accurately"""
    variables = []
    
    # More comprehensive regex pattern to match variable blocks including multiline content
    variable_pattern = r'variable\s+"([^"]+)"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    matches = re.findall(variable_pattern, variables_content, re.DOTALL)
    
    for var_name, var_block in matches:
        var_info = {"name": var_name}
        
        # Extract description with better handling of multiline descriptions
        desc_patterns = [
            r'description\s*=\s*"([^"]*)"',  # Single line
            r'description\s*=\s*<<-?EOT\s*\n(.*?)\n\s*EOT',  # Heredoc
            r'description\s*=\s*<<([A-Z]+)\s*\n(.*?)\n\s*\1',  # Custom heredoc
        ]
        
        description = ""
        for pattern in desc_patterns:
            desc_match = re.search(pattern, var_block, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
                break
        
        var_info["description"] = description
        
        # Extract type with better parsing
        type_match = re.search(r'type\s*=\s*([^\n\r]+)', var_block)
        if type_match:
            var_type = type_match.group(1).strip()
            # Clean up the type (remove comments, extra spaces)
            var_type = re.sub(r'#.*$', '', var_type, flags=re.MULTILINE).strip()
            var_info["type"] = var_type
        else:
            var_info["type"] = "string"  # Default type
        
        # Extract default value with better handling of complex defaults
        default_patterns = [
            r'default\s*=\s*"([^"]*)"',  # String default
            r'default\s*=\s*(true|false)',  # Boolean default
            r'default\s*=\s*(\d+(?:\.\d+)?)',  # Number default
            r'default\s*=\s*\[(.*?)\]',  # List default (simplified)
            r'default\s*=\s*\{([^}]*)\}',  # Map/object default (simplified)
            r'default\s*=\s*([^\n\r#]+)',  # Any other default
        ]
        
        default_value = None
        for pattern in default_patterns:
            default_match = re.search(pattern, var_block, re.DOTALL)
            if default_match:
                default_str = default_match.group(1).strip()
                # Try to parse the default value appropriately
                if pattern == default_patterns[1]:  # Boolean
                    default_value = default_str == "true"
                elif pattern == default_patterns[2]:  # Number
                    default_value = float(default_str) if '.' in default_str else int(default_str)
                elif pattern == default_patterns[3]:  # List
                    default_value = f"[{default_str}]"
                elif pattern == default_patterns[4]:  # Map/object
                    default_value = f"{{{default_str}}}"
                else:
                    default_value = default_str
                break
        
        if default_value is not None:
            var_info["default"] = default_value
            var_info["required"] = False
        else:
            var_info["required"] = True
        
        # Check for validation blocks
        if "validation" in var_block:
            var_info["has_validation"] = True
            
        # Check for sensitive flag
        if re.search(r'sensitive\s*=\s*true', var_block):
            var_info["sensitive"] = True
        else:
            var_info["sensitive"] = False
        
        variables.append(var_info)
    
    return variables

def parse_terraform_outputs(outputs_content: str) -> List[Dict]:
    """Enhanced parsing of outputs.tf content to extract output definitions more accurately"""
    outputs = []
    
    # More comprehensive regex pattern to match output blocks
    output_pattern = r'output\s+"([^"]+)"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    matches = re.findall(output_pattern, outputs_content, re.DOTALL)
    
    for output_name, output_block in matches:
        output_info = {"name": output_name}
        
        # Extract description with better handling
        desc_patterns = [
            r'description\s*=\s*"([^"]*)"',
            r'description\s*=\s*<<-?EOT\s*\n(.*?)\n\s*EOT',
            r'description\s*=\s*<<([A-Z]+)\s*\n(.*?)\n\s*\1',
        ]
        
        description = ""
        for pattern in desc_patterns:
            desc_match = re.search(pattern, output_block, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
                break
        
        output_info["description"] = description
        
        # Extract value reference
        value_match = re.search(r'value\s*=\s*([^\n\r#]+)', output_block)
        if value_match:
            output_info["value_reference"] = value_match.group(1).strip()
        
        # Check if sensitive
        if re.search(r'sensitive\s*=\s*true', output_block):
            output_info["sensitive"] = True
        else:
            output_info["sensitive"] = False
        
        outputs.append(output_info)
    
    return outputs

@mcp.tool()
def populate_infra_config_repo(module_name: str, provider: str, repo_path: str, module_details: str) -> str:
    """Populate the calling repository with Terraform module call configurations
    
    Args:
        module_name: Name of the module (e.g., 'lambda')
        provider: Provider (e.g., 'aws', 'azure')
        repo_path: Path to the repository root
        module_details: JSON string containing module analysis from previous tools
    
    Returns:
        JSON string with success/error status and created files
    """
    try:
        # Parse module details
        details = json.loads(module_details) if isinstance(module_details, str) else module_details
        
        repo_path = Path(repo_path)
        terraform_dir = repo_path / "terraform"
        
        # Create terraform directory if it doesn't exist
        terraform_dir.mkdir(exist_ok=True)
        
        # Get current version from module details
        current_version = details.get("current_version", "latest")
        input_variables = details.get("input_variables", [])
        output_variables = details.get("output_variables", [])
        
        created_files = []
        
        # 1. Create main.tf with module call
        main_tf_content = generate_main_tf_content(module_name, provider, current_version, input_variables)
        main_tf_path = terraform_dir / "main.tf"
        with open(main_tf_path, "w") as f:
            f.write(main_tf_content)
        created_files.append(str(main_tf_path))
        
        # 2. Create variables.tf
        variables_tf_content = generate_variables_tf_content(input_variables)
        variables_tf_path = terraform_dir / "variables.tf"
        with open(variables_tf_path, "w") as f:
            f.write(variables_tf_content)
        created_files.append(str(variables_tf_path))
        
        # 3. Create outputs.tf
        outputs_tf_content = generate_outputs_tf_content(module_name, output_variables)
        outputs_tf_path = terraform_dir / "outputs.tf"
        with open(outputs_tf_path, "w") as f:
            f.write(outputs_tf_content)
        created_files.append(str(outputs_tf_path))
        
        # 4. Create environment-specific tfvars files
        environments = ["dev", "qa", "uat", "prod"]
        for env in environments:
            env_dir = repo_path / "environment" / env
            env_dir.mkdir(parents=True, exist_ok=True)
            
            tfvars_content = generate_tfvars_content(input_variables, env)
            tfvars_path = env_dir / f"{env}.auto.tfvars"
            with open(tfvars_path, "w") as f:
                f.write(tfvars_content)
            created_files.append(str(tfvars_path))
        
        # 5. Create backend.tf and optionally providers.tf (not needed for Azure)
        backend_tf_path = terraform_dir / "backend.tf"
        with open(backend_tf_path, "w") as f:
            f.write(generate_backend_tf_content(module_name))
        created_files.append(str(backend_tf_path))
        
        # Only create providers.tf for non-Azure modules
        if provider != "azu":
            providers_tf_path = terraform_dir / "providers.tf"
            with open(providers_tf_path, "w") as f:
                f.write(generate_providers_tf_content(provider))
            created_files.append(str(providers_tf_path))
        
        result = {
            "success": True,
            "module": f"{ORGANIZATION}/{module_name}/{provider}",
            "version": current_version,
            "created_files": created_files,
            "terraform_directory": str(terraform_dir),
            "environments_configured": environments,
            "message": "Infrastructure configuration repository populated successfully"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to populate infra config repo: {str(e)}"
        })

def generate_main_tf_content(module_name: str, provider: str, version: str, input_variables: List[Dict]) -> str:
    """Generate main.tf content with module call"""
    content = f'''# Main Terraform configuration
# Generated automatically by Lennar MCP Server

module "{module_name}" {{
  source  = "app.terraform.io/{ORGANIZATION}/{module_name}/{provider}"
  version = "{version}"

'''
    
    # Add required variables
    for var in input_variables:
        var_name = var.get("name", "")
        description = var.get("description", "")
        required = var.get("required", True)
        
        if required:
            content += f'  {var_name} = var.{var_name}  # {description}\n'
    
    content += "}\n"
    return content

def generate_variables_tf_content(input_variables: List[Dict]) -> str:
    """Generate variables.tf content ONLY from actual module input variables"""
    content = '''# Variables for Terraform configuration
# Generated automatically by Lennar MCP Server
# These variables match the actual module requirements

'''
    
    if not input_variables:
        content += '# No input variables found in the module\n'
        return content
    
    for var in input_variables:
        var_name = var.get("name", "")
        description = var.get("description", "No description available")
        var_type = var.get("type", "string")
        default = var.get("default")
        sensitive = var.get("sensitive", False)
        
        content += f'variable "{var_name}" {{\n'
        content += f'  description = "{description}"\n'
        content += f'  type        = {var_type}\n'
        
        if default is not None:
            # Format the default value properly
            if isinstance(default, str):
                content += f'  default     = "{default}"\n'
            elif isinstance(default, bool):
                content += f'  default     = {str(default).lower()}\n'
            elif isinstance(default, (int, float)):
                content += f'  default     = {default}\n'
            else:
                content += f'  default     = {default}\n'
        
        if sensitive:
            content += '  sensitive   = true\n'
        
        content += "}\n\n"
    
    return content

def generate_outputs_tf_content(module_name: str, output_variables: List[Dict]) -> str:
    """Generate outputs.tf content"""
    content = f'''# Outputs for {module_name} module
# Generated automatically by Lennar MCP Server

'''
    
    for output in output_variables:
        output_name = output.get("name", "")
        description = output.get("description", "No description")
        sensitive = output.get("sensitive", False)
        
        content += f'output "{output_name}" {{\n'
        content += f'  description = "{description}"\n'
        content += f'  value       = module.{module_name}.{output_name}\n'
        
        if sensitive:
            content += '  sensitive   = true\n'
        
        content += "}\n\n"
    
    return content

def generate_tfvars_content(input_variables: List[Dict], environment: str) -> str:
    """Generate environment-specific tfvars content ONLY for actual module variables"""
    content = f'''# {environment.upper()} Environment Variables
# Generated automatically by Lennar MCP Server
# Environment: {environment}
# Only includes variables that exist in the actual module

'''
    
    if not input_variables:
        content += '# No input variables found in the module\n'
        return content
    
    for var in input_variables:
        var_name = var.get("name", "")
        var_type = var.get("type", "string")
        description = var.get("description", "")
        required = var.get("required", True)
        default = var.get("default")
        
        # Only generate values for required variables (no defaults)
        if required and default is None:
            # Generate appropriate values based on the actual variable type and name
            if "string" in var_type.lower():
                value = generate_env_string_value(var_name, environment)
            elif "bool" in var_type.lower():
                value = generate_env_bool_value(var_name, environment)
            elif "number" in var_type.lower():
                value = generate_env_number_value(var_name, environment)
            elif "list" in var_type.lower():
                value = generate_env_list_value(var_name, environment)
            elif "map" in var_type.lower() or "object" in var_type.lower():
                value = generate_env_object_value(var_name, environment)
            else:
                # For unknown types, use string with placeholder
                value = f'"UPDATE_THIS_VALUE_FOR_{var_name.upper()}"'
            
            content += f'{var_name} = {value}  # {description}\n'
        elif not required and default is not None:
            # Show optional variables as comments with their defaults
            content += f'# {var_name} = {json.dumps(default)}  # Optional: {description}\n'
    
    return content

def generate_env_string_value(var_name: str, environment: str) -> str:
    """Generate environment-specific string values based on actual variable names"""
    var_name_lower = var_name.lower()
    env_prefix = f"lennar-{environment}"
    
    # Generate values based on actual variable name patterns
    if "name" in var_name_lower:
        return f'"{env_prefix}-{var_name.replace("_name", "").replace("_", "-")}"'
    elif "region" in var_name_lower:
        # Environment-specific regions
        region_map = {
            "dev": "us-east-1",
            "qa": "us-east-1", 
            "uat": "us-west-2",
            "prod": "us-west-2"
        }
        return f'"{region_map.get(environment, "us-east-1")}"'
    elif "environment" in var_name_lower or var_name_lower == "env":
        return f'"{environment}"'
    elif "bucket" in var_name_lower:
        return f'"{env_prefix}-storage-bucket"'
    elif "role" in var_name_lower:
        return f'"{env_prefix}-execution-role"'
    elif "policy" in var_name_lower:
        return f'"{env_prefix}-access-policy"'
    elif "key" in var_name_lower:
        return f'"{env_prefix}-encryption-key"'
    elif "domain" in var_name_lower:
        if environment == "prod":
            return '"api.lennar.com"'
        else:
            return f'"{environment}-api.lennar.com"'
    elif "prefix" in var_name_lower:
        return f'"{env_prefix}"'
    elif "suffix" in var_name_lower:
        return f'"{environment}-lennar"'
    else:
        # Use placeholder that clearly indicates this needs to be updated
        return f'"PLEASE_UPDATE_{var_name.upper()}_FOR_{environment.upper()}"'

def generate_env_bool_value(var_name: str, environment: str) -> str:
    """Generate environment-specific boolean values based on actual variable names"""
    var_name_lower = var_name.lower()
    
    if "enable" in var_name_lower or "enabled" in var_name_lower:
        # Enable monitoring and logging in prod/uat, optional in dev/qa
        if "monitor" in var_name_lower or "log" in var_name_lower:
            return "true" if environment in ["prod", "uat"] else "false"
        # Enable encryption by default
        elif "encrypt" in var_name_lower:
            return "true"
        else:
            return "true"
    elif "public" in var_name_lower:
        # No public access in prod
        return "false" if environment == "prod" else "true"
    elif "delete" in var_name_lower or "destroy" in var_name_lower:
        # Allow deletion in dev/qa only
        return "true" if environment in ["dev", "qa"] else "false"
    else:
        return "true"

def generate_env_number_value(var_name: str, environment: str) -> str:
    """Generate environment-specific number values based on actual variable names"""
    var_name_lower = var_name.lower()
    
    if "count" in var_name_lower or "size" in var_name_lower:
        # Scale based on environment
        scale_map = {"dev": 1, "qa": 2, "uat": 3, "prod": 5}
        base_value = scale_map.get(environment, 1)
        
        if "min" in var_name_lower:
            return str(base_value)
        elif "max" in var_name_lower:
            return str(base_value * 3)
        else:
            return str(base_value)
    elif "memory" in var_name_lower:
        # Memory allocation based on environment
        memory_map = {"dev": 128, "qa": 256, "uat": 512, "prod": 1024}
        return str(memory_map.get(environment, 128))
    elif "cpu" in var_name_lower:
        # CPU allocation based on environment  
        cpu_map = {"dev": 256, "qa": 512, "uat": 1024, "prod": 2048}
        return str(cpu_map.get(environment, 256))
    elif "timeout" in var_name_lower:
        # Timeout values based on environment
        timeout_map = {"dev": 60, "qa": 120, "uat": 300, "prod": 600}
        return str(timeout_map.get(environment, 300))
    elif "port" in var_name_lower:
        return str(generate_number_value(var_name))
    else:
        return "1"

def generate_env_list_value(var_name: str, environment: str) -> str:
    """Generate environment-specific list values based on actual variable names"""
    var_name_lower = var_name.lower()
    env_prefix = f"lennar-{environment}"
    
    if "subnet" in var_name_lower:
        if environment == "prod":
            return f'["{env_prefix}-private-subnet-1", "{env_prefix}-private-subnet-2", "{env_prefix}-private-subnet-3"]'
        else:
            return f'["{env_prefix}-subnet-1", "{env_prefix}-subnet-2"]'
    elif "sg" in var_name_lower or "security" in var_name_lower:
        return f'["{env_prefix}-security-group"]'
    elif "az" in var_name_lower or "availability" in var_name_lower:
        region_az_map = {
            "us-east-1": ["us-east-1a", "us-east-1b", "us-east-1c"],
            "us-west-2": ["us-west-2a", "us-west-2b", "us-west-2c"]
        }
        region = "us-west-2" if environment in ["uat", "prod"] else "us-east-1"
        azs = region_az_map[region]
        return f'["{azs[0]}", "{azs[1]}"]'
    elif "cidr" in var_name_lower:
        cidr_map = {
            "dev": ["10.0.1.0/24", "10.0.2.0/24"],
            "qa": ["10.1.1.0/24", "10.1.2.0/24"], 
            "uat": ["10.2.1.0/24", "10.2.2.0/24"],
            "prod": ["10.3.1.0/24", "10.3.2.0/24"]
        }
        cidrs = cidr_map.get(environment, ["10.0.1.0/24", "10.0.2.0/24"])
        return f'["{cidrs[0]}", "{cidrs[1]}"]'
    elif "tag" in var_name_lower:
        return f'["{environment}", "managed", "terraform"]'
    else:
        # Use placeholder that clearly indicates this needs to be updated
        return f'["UPDATE_{var_name.upper()}_LIST_FOR_{environment.upper()}"]'

def generate_env_object_value(var_name: str, environment: str) -> str:
    """Generate environment-specific object/map values based on actual variable names"""
    var_name_lower = var_name.lower()
    
    if "tag" in var_name_lower:
        return f'''{{
    Environment = "{environment}"
    Project     = "lennar-infrastructure"
    ManagedBy   = "terraform"
    Owner       = "platform-team"
  }}'''
    elif "config" in var_name_lower:
        return f'''{{
    environment = "{environment}"
    region      = "{get_env_region(environment)}"
  }}'''
    else:
        # Use placeholder that clearly indicates this needs to be updated
        return f'''{{
    # UPDATE_THIS_OBJECT_FOR_{var_name.upper()}
    environment = "{environment}"
  }}'''

def get_env_region(environment: str) -> str:
    """Get the appropriate AWS region for an environment"""
    region_map = {
        "dev": "us-east-1",
        "qa": "us-east-1", 
        "uat": "us-west-2",
        "prod": "us-west-2"
    }
    return region_map.get(environment, "us-east-1")

# Server startup code
if __name__ == "__main__":
    print("Starting Lennar MCP Server...")
    print("Available tools:")
    print("- check_lennar_module: Check if module exists in Lennar registry")
    print("- get_terraform_module_details: Get detailed module information")
    print("- get_github_module_files: Get module files from GitHub (with branch detection)")
    print("- populate_infra_config_repo: Create terraform configuration files")
    print("- create_repository_infrastructure: Create repository-specific .tf files")
    print("- verify_terraform_configuration: Verify generated configurations")
    print("- create_service_infrastructure: Orchestrate complete infrastructure creation")
    print()
    
    # Run the MCP server using stdin/stdout protocol
    mcp.run()