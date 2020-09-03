# sw_api

This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- src - Code for the application's Lambda function.
- events - Invocation events that you can use to invoke the function.
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions and an API Gateway API. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Deploy the application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To set variables environment, create a ``.env`` file in the root directory with the same variables as the ``.env_sample`` file.

- SAM configuration:

```commandline
    Region=us-east-1
    StackName=swapiv10
    S3Bucket=aws-sam-cli-v10
```
* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **S3Bucket**: The name of the Amazon S3 bucket where this command uploads your AWS CloudFormation template.

- Template Parameters:

```commandline
    # Template parameters
    Stage=dev
    S3SnowBucketName=snow-attachments-v10
    S3JSDBucketName=jsd-attachments-v10
```

- SSM Parameters:

```commandline
    # SSM parameters
    # Jira
    JiraHost=NOT_CONFIGURED
    JiraUserId=NOT_CONFIGURED
    JiraAppPassword=NOT_CONFIGURED
    ...
```

To build and deploy your application run the following in your shell:

Build
```bash
make build
```

Or build with docker if you have troubles with Python environment
```bash
make build_with_docker
```

Deploy
```bash
make deploy
```

You can find your API Gateway Endpoint URL in the output values displayed after deployment.
To get the api token, run the command below with the value from the output

```bash
aws apigateway get-api-key --api-key <ApiKeyId> --include-value
```
Then you can pass api token as `x-api-key` HTTP Header Parameter to access the api

Update SSM parameters with value from `.env` file
```bash
make update_ssm
```

## Cleanup

To delete the application that you created, use the command below:

```bash
make clean
```
## Change ENV path

By default the `make` command targets on `.env` file, you can change it with `env_path` argument

```bash
make env_path=<ENV_PATH> build
make env_path=<ENV_PATH> build_with_docker
make env_path=<ENV_PATH> deploy
make env_path=<ENV_PATH> make update_ssm
make env_path=<ENV_PATH> clean
```