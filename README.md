# Lennar MCP Server

A comprehensive Model Context Protocol (MCP) server for managing Terraform infrastructure modules within the Lennar organization. This server provides automated tools for discovering, analyzing, and deploying AWS and Azure infrastructure using Lennar's private Terraform Cloud registry.

## 🚀 Features

- **Module Discovery**: Check and verify Terraform modules in Lennar's private registry
- **Detailed Analysis**: Get comprehensive module information including inputs, outputs, and documentation
- **Infrastructure Generation**: Automatically generate Terraform configurations with professional naming conventions
- **Environment Management**: Create environment-specific configurations for dev, qa, uat, and prod
- **Orchestrated Deployment**: Single-command infrastructure setup with automatic tool chaining
- **GitHub Integration**: Fallback support for module discovery via GitHub repositories
- **Professional Standards**: Enterprise-grade naming conventions and best practices

## 📦 Installation & Setup

### Using Docker (Recommended)

The MCP server is available as a Docker image on Docker Hub:

```bash
# Pull the latest image
docker pull jitenderyadavofc/lennar-lz-mcp-server:latest

# Run the server
docker run --rm -i jitenderyadavofc/lennar-lz-mcp-server:latest
```

### MCP Configuration

Update your MCP client configuration (`.vscode/mcp.json` or Claude Desktop settings):

```json
{
    "servers": {
        "lennar-lz-mcp-server": {
            "command": "docker",
            "args": ["run", "--rm", "-i", "jitenderyadavofc/lennar-lz-mcp-server:latest"],
            "env": {}
        }
    }
}
```

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd final-mcp

# Install dependencies
uv sync

# Run the server
uv run python server.py
```

## 🛠 Available Tools

### 1. Check Lennar Module
Verify if a module exists in Lennar's private Terraform Cloud registry.

```
check_lennar_module(module_name: str, provider: str = "aws") -> str
```

**Example:**
```
check_lennar_module("lambda", "aws")
check_lennar_module("aks", "azu")
```

### 2. Get Terraform Module Details
Retrieve comprehensive module information including inputs, outputs, and documentation.

```
get_terraform_module_details(name: str, provider: str, version: str = "latest") -> str
```

**Example:**
```
get_terraform_module_details("lambda", "aws", "latest")
```

### 3. Get GitHub Module Files
Fallback method to retrieve module files directly from GitHub repositories.

```
get_github_module_files(module_name: str, provider: str = "aws") -> str
```

### 4. Populate Infrastructure Config Repository
Generate complete Terraform configuration files with professional naming conventions.

```
populate_infra_config_repo(module_name: str, provider: str, repo_path: str, module_details: str) -> str
```

### 5. Create Repository Configuration
Generate GitHub repository setup files and configurations.

```
create_repository_config(...) -> str
```

### 6. **Create Service Infrastructure (Orchestration Tool)**
The main orchestration tool that automatically executes all required steps in sequence.

```
create_service_infrastructure(
    service_request: str,
    repo_path: str,
    app_acronym: str = "",
    app_name: str = "",
    gh_org: str = "",
    template_org: str = "",
    template_repo: str = "",
    repo_name_suffix: str = "",
    vault_secrets: str = "{}",
    environment_configs: str = "{}"
) -> str
```

## 🏗 Generated Terraform Structure

When you use the orchestration tool, it creates a complete Terraform project structure:

```
your-repo/
├── terraform/
│   ├── main.tf              # Module calling configuration
│   ├── variables.tf         # Input variable definitions
│   ├── outputs.tf          # Output definitions
│   ├── backend.tf          # Terraform Cloud backend config
│   └── providers.tf        # Provider configurations (AWS only)
├── environment/
│   ├── dev/
│   │   └── dev.auto.tfvars     # Development environment values
│   ├── qa/
│   │   └── qa.auto.tfvars      # QA environment values
│   ├── uat/
│   │   └── uat.auto.tfvars     # UAT environment values
│   └── prod/
│       └── prod.auto.tfvars    # Production environment values
└── .github/
    └── repository-config.json  # GitHub repository configuration
```

### Example terraform/main.tf

```hcl
# Main Terraform configuration
# Generated automatically by Lennar MCP Server

module "lambda" {
  source  = "app.terraform.io/Lennar/lambda/aws"
  version = "1.0.0"

  function_name = var.function_name  # Lambda function name
  runtime = var.runtime  # Runtime environment
  handler = var.handler  # Function handler
  environment_variables = var.environment_variables  # Environment variables
  timeout = var.timeout  # Function timeout
  memory_size = var.memory_size  # Memory allocation
}
```

### Example environment/prod/prod.auto.tfvars

```hcl
# PROD Environment Variables
# Generated automatically by Lennar MCP Server
# Environment: prod

function_name = "lennar-prod-lambda-function"  # Lambda function name
runtime = "python3.11"  # Runtime environment
handler = "index.handler"  # Function handler
environment_variables = {
    Environment = "prod"
    Project     = "lennar-infrastructure"
    ManagedBy   = "terraform"
    Owner       = "platform-team"
}  # Environment variables
timeout = 600  # Function timeout
memory_size = 1024  # Memory allocation
```

## 🎯 Usage Examples

### Quick Start - Create Lambda Infrastructure

```
create_service_infrastructure(
    service_request="Create Lambda infra config",
    repo_path="/path/to/your/repo"
)
```

### Complete Setup with Repository Configuration

```
create_service_infrastructure(
    service_request="Create S3 bucket for production",
    repo_path="/path/to/your/repo",
    app_acronym="LNR",
    app_name="Lennar Platform",
    gh_org="lennar-tech",
    template_org="lennar-templates",
    template_repo="terraform-template",
    repo_name_suffix="infra"
)
```

### Azure Infrastructure

```
create_service_infrastructure(
    service_request="Create Azure AKS cluster",
    repo_path="/path/to/your/repo"
)
```

## 🔧 Professional Naming Conventions

The server follows enterprise-grade naming conventions:

### Resource Naming Pattern
```
lennar-{environment}-{service}-{type}
```

**Examples:**
- `lennar-prod-lambda-function`
- `lennar-dev-storage-bucket`
- `lennar-uat-vpc-security-group`

### Domain Naming
- **Production**: `api.lennar.com`
- **Other Environments**: `{environment}-api.lennar.com`

### Environment-Specific Scaling
- **Dev**: 1 instance, 128MB memory, us-east-1
- **QA**: 2 instances, 256MB memory, us-east-1
- **UAT**: 3 instances, 512MB memory, us-west-2
- **Prod**: 5 instances, 1024MB memory, us-west-2

## 🌐 Supported Services

### AWS Services
- Lambda Functions
- S3 Buckets
- VPC Networks
- RDS Databases
- EC2 Instances
- IAM Roles/Policies
- CloudFront Distributions
- API Gateway
- DynamoDB
- SQS/SNS

### Azure Services
- AKS Clusters
- Storage Accounts
- Virtual Networks
- Virtual Machines
- SQL Databases
- Cosmos DB
- Key Vault
- Azure Functions

## 🔄 Workflow

1. **Service Request Parsing**: Automatically detects service type and cloud provider
2. **Module Verification**: Checks Lennar's private Terraform Cloud registry
3. **Module Analysis**: Retrieves detailed module information with GitHub fallback
4. **Configuration Generation**: Creates all Terraform files with professional naming
5. **Environment Setup**: Generates environment-specific variable files
6. **Validation**: Performs syntax checking and best practice verification

## 📋 Environment Variables

The server uses the following configurations:

- **Terraform Cloud**: Lennar organization with private modules
- **GitHub Integration**: modules-len organization repositories
- **Naming Standards**: Enterprise-grade professional conventions

## 🚦 Getting Started

1. **Install the MCP server** using Docker or local setup
2. **Configure your MCP client** with the server details
3. **Use the orchestration tool** to create infrastructure:
   ```
   "Create Lambda function for development"
   ```
4. **Review generated files** in your repository
5. **Deploy with Terraform**:
   ```bash
   cd terraform
   terraform init
   terraform plan -var-file="../environment/dev/dev.auto.tfvars"
   terraform apply
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the MCP client
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Contact the platform team
- Check the Terraform Cloud registry for module documentation

---

**Lennar MCP Server** - Automating infrastructure deployment with enterprise-grade standards.