#!make
env_path=.env
include $(env_path)
export $(shell sed 's/=.*//' $(env_path))

.PHONY: run build setup deploy update_ssm clean

run: build_with_docker deploy

build:
		@sam build
build_with_docker:
		@sam build --use-container
deploy:
		@aws --region $(Region) s3 mb s3://$(S3Bucket)
		@sam deploy --stack-name $(StackName) \
					--s3-bucket $(S3Bucket) \
					--s3-prefix $(StackName) \
					--capabilities 'CAPABILITY_IAM' \
					--region $(Region) \
					--confirm-changeset \
					--parameter-overrides 'ParameterKey=Stage,ParameterValue=$(Stage) ParameterKey=S3SnowBucketName,ParameterValue=$(S3SnowBucketName) ParameterKey=S3JSDBucketName,ParameterValue=$(S3JSDBucketName)'

update_ssm:
		@set -x
		@echo "Updating SSM parameters"
		@aws configure set cli_follow_urlparam false
		# Jira Parameters
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraHost --value "$(JiraHost)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraUserId --value "$(JiraUserId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraAppPassword --value "$(JiraAppPassword)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraCustomerRefNoFieldId --value "$(JiraCustomerRefNoFieldId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraActualResultFieldId --value "$(JiraActualResultFieldId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraExpectedResultFieldId --value "$(JiraExpectedResultFieldId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraEnvironmentFieldId --value "$(JiraEnvironmentFieldId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraServiceDeskId --value "$(JiraServiceDeskId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/JiraRequestTypeId --value "$(JiraRequestTypeId)" --type SecureString --overwrite
		# Snow Parameters
		aws ssm put-parameter --region $(Region) --name /$(Stage)/SnowHost --value "$(SnowHost)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/SnowClientId --value "$(SnowClientId)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/BasicAuth --value "$(BasicAuth)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/SnowAuthUserName --value "$(SnowAuthUserName)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/SnowAuthPassword --value "$(SnowAuthPassword)" --type SecureString --overwrite
		aws ssm put-parameter --region $(Region) --name /$(Stage)/SnowAuthUrl --value "$(SnowAuthUrl)" --type SecureString --overwrite
		# S3 Parameters
		aws ssm put-parameter --region $(Region) --name /$(Stage)/S3PresignUrlTtl --value "$(S3PresignUrlTtl)" --type SecureString --overwrite
clean:
		@aws cloudformation delete-stack --stack-name $(StackName)
