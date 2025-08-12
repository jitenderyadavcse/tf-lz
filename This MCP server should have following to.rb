This MCP server should have following tools
1. Tool Name - [ Check Lennar Module]
  If user asks following things
     - Create lambda module or any aws/azure module then It should check the lennar private repository modules and see whether that module exist or not, if modules exist then it would go to next tool

2. Tool Name - [ Get Terraform Module Details ]
  Once the module is verified in Lennar private registry, It should check two things
  -  Analyze all the inputs/outputs variables and main.tf all the .tf files including Readme files from Terraform cloud modules and github repository in modules-len org .
  - Once all the file structure input output and current version of the  module is analyzed by the module, move to next tool

 3. Tool Name - [ Populate Infra Config Repo with AWS/AZURE module call ]
  We will have to populate the calling repo of the module with below information
   - check for terraform directory in the root, if exist then populate main.tf with module call code

   for eg lambda:
     module "lambda" {
  source  = "app.terraform.io/Lennar/lambda/aws"
  version = "0.9.23"
  # insert required variables here
}
 and also pass all the input variable required for module call according to analysis done for module in step 2. In version field always use current_version of module in lennar terraform cloud registry.
 - All the variables.tf and other.tf files should be populated according to module input/output structure.
 - there is environment/dev/dev.auto.tfvars - for dev environment variables values should be added here
           environment/qa/qa.auto.tfvars - for qa environment variables values should be added here 
           environment/uat/uat.auto.tfvars  - for uat environment variables values should be added here
           environment/prod/prod.auto.tfvars - for prod environment variables values should be added here

 - Once all the above things are done for any aws/azure service input by user, then move to next tool

4. Tool Name - [ Repository Creation ]
 We will have to create repositories files as below
   - there is repositories folder in the root
   - create a file under that with service-name.tf for eg: if lambda name is "test-lambda" then test-lambda.tf file should be created with below content:

   module "github_repository" {
  source = "../github-repo-lz"

  providers = {
    vault.vault_prod = vault.vault_prod
    vault.vault_nonprod = vault.vault_nonprod
  }
  
  # App Metadata
  app_acronym     = ""  # Take input from user to provide project acronym name
  app_name        = "" # Take input from user to get project app name


  # GitHub Integration - using local variables for organization settings
  gh_org   = ""   # take input from user to give github organization name where github repo need to be created
  template_org = "" # take input from user to get template_organization name
  template_repo   = "" #take input from user to get template repo name to be used
  repo_name_suffix = "" # take input from user to create repo with suffix name


  vault_secrets = {}  # vault secrets map should be populated with below format
   "cloud-credentials" = ["aws_account_id", "azure_subscription_id"]
   these all need to be take input from user
   #Vault secret path = ["secret_key name", "secret_keyname"]

   
   Below environment config need to be populated according to AWS/Azure cloud
  # Per-environment1 Cloud Config
  environment_config = {
    dev = {
      cloud       = "azure" if aws thenit should be aws
      subscription_id = "" if aws then user need to add accound_id of aws
    }
    uat = {
     cloud       = "azure"
      subscription_id = ""
    }
    prod = {
      cloud       = "azure"
      subscription_id = ""
    }
    qa = {
      cloud       = "azure"
      subscription_id = ""
    }
  }

}
           

5.Tool Name - [ Verification ]
 Final tool will examine all the details as an expert of terraform AWS/Azure,
  to check all the variables and syntax errors


 6.  tool - [ Create Service infrastructure ]
 IF user give input as 
    - Create Lambda/ or any service of AWS/AZure  infra config
    or - Create lambda function or any s3 bucket Creation
     or - Create lambda module code for lennar
     
     then tool 1,2,3,4,5 should be called automatically one after the other

     Also, Terraform populate infra config should populate main.tf bu all the values should be added in environment/dev/dev.auto.tfvars for dev, qa ,uat prod respectively
     update other variables.tf accordingly

     If user types 
     - Create respository for ambda/apigateway or any-service
     or - create repo for any-service
     or - Create repo infrastructure for any-service 
     or -reposiotry config create for any-service 
     then a file under repositories folder should be created with apigatewayname.tf
     or lambdaname.tf 
     these file should contain the tool 4 configuration


     Also While getting the details of modules from github modules-len repo
     check the latest release tag created with which branch,
     if it is develop then get the module information from develop branch all .tf file and readme files
        otherwise if the latest relase tag created with main branch then get module details from main branch all .tf file and readme files


    I can see MCP server is adding extra attributes for the modules which are not even present in terraform cloud registry module or
    github latest release tag all .tf files. Kindly use only those attribute and variables which are defined in latest realease tag of github module repo or terraform cloud registry module latest version


    If Inputs are not available in Lennar terraform cloud registry module, then
    pick the exact numbers of parameters defined in variables.tf of github reposiotry latest realease tag
    all the variables accroding to their type should be passed to module block, no other extra resource block should be created in main.tf
    It is strictly matching the same number of variables defined in variables.tf and no extra variables should be passed to the module