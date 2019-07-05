import boto3
import botocore
import glob
import json
import pyAesCrypt
import sys
import awsutil
from multiprocessing import Process

from botocore.exceptions import ClientError

secrets_client = boto3.client('secretsmanager')
ec2_client = boto3.client('ec2')
cfn_client = boto3.client('cloudformation')
s3_client = boto3.client('s3')

# RDS information
rds_password_name = 'RdsPassword'
rds_user_name = 'RdsUserName'
rds_app_user = 'appuser'
rds_db_name = 'RdsDbName'
db_name = 'nrfc'
db_engine = 'mysql'
db_port = '3306'

default_ssh_key_pair_name = 'DefaultKey'
bastion_ssh_key_pair_name = 'BastionKey'


def _setup_secrets_and_keys():
    awsutil.generate_ssh_key_pair(default_ssh_key_pair_name)
    awsutil.generate_ssh_key_pair(bastion_ssh_key_pair_name)

    awsutil.save_secret(rds_user_name, rds_app_user)
    awsutil.save_secret(rds_db_name, db_name)

    for env in ['dev', 'test', 'prod']:
      app_db_password_secret_name = env + '/' + rds_password_name
      awsutil.create_password(app_db_password_secret_name)

def _setup_cfn_templates_bucket():
    awsutil.deploy_stack('cfn-templates-bucket', 'infrastructure/cfn-templates-bucket.yml', [])

def _setup_iam_roles_and_idp():
    parameters = [
            {
                'ParameterKey': 'MetadataDocument',
                'ParameterValue': awsutil.parse_file('infrastructure/aws_metadata.xml')
            },
            {
                'ParameterKey': 'SamlProviderName',
                'ParameterValue': 'MdasJumpCloud'
            },
        ]

    awsutil.deploy_stack('iam-roles-idp', 'infrastructure/iam-roles-idp.yml', parameters)

def _setup_cloud_trail():
    parameters = []
    awsutil.deploy_stack('cloudtrail', 'infrastructure/cloudtrail.yml', parameters)

def _setup_envs():
    cfn_templates_bucket = awsutil.get_cfn_template_output('cfn-templates-bucket', 'CfnTemplatesBucketName')
    s3 = boto3.resource('s3')
    # upload CloudFormation templates to template bucket
    for cfn_template in glob.glob('infrastructure/*.yml'):
        object_key = cfn_template.split('/')[1]
        s3.Bucket(cfn_templates_bucket).upload_file(cfn_template, object_key)

    # Create presigned URLs for access to CloudFormation templates in S3 template bucket
    vpc_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'vpc.yml'})
    vpc_peering_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'vpc-peering.yml'})
    bastion_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'bastion.yml'})
    rds_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'rds.yml'})
    # jenkins_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'jenkins.yml'})
    # etl_resources_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'etl-resources.yml'})
    # webapp_resources_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'webapp-static-hosting.yml'})
    # sam_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'serverless-application-model.yml'})
    # sagemaker_resources_template_url = s3_client.generate_presigned_url('get_object', ExpiresIn=0, Params={'Bucket': cfn_templates_bucket, 'Key': 'sagemaker-resources.yml'})

    parameters = [
            {
                'ParameterKey': 'VpcTemplateUrl',
                'ParameterValue': vpc_template_url
            },
            {
                'ParameterKey': 'VpcPeeringTemplateUrl',
                'ParameterValue': vpc_peering_template_url
            },
            {
                'ParameterKey': 'BastionTemplateUrl',
                'ParameterValue': bastion_template_url
            },
#            {
#                'ParameterKey': 'RdsTemplateUrl',
#                'ParameterValue': rds_template_url
#            },
            {
                'ParameterKey': 'BastionKeyName',
                'ParameterValue': bastion_ssh_key_pair_name
            },
#            {
#                'ParameterKey': 'DatabaseName',
#                'ParameterValue': db_name
#            },
#            {
#                'ParameterKey': 'DBMasterUsername',
#                'ParameterValue': rds_app_user
#            },
#            {
#                'ParameterKey': 'JenkinsTemplateUrl',
#                'ParameterValue': jenkins_template_url
#
#            },
            {
                'ParameterKey': 'DefaultSSHKey',
                'ParameterValue': default_ssh_key_pair_name

            },
#            {
#                'ParameterKey': 'GitBranch',
#                'ParameterValue': 'master'
#            },
#            {
#                'ParameterKey': 'GitRepo',
#                'ParameterValue': git_repo
#            },
#            {
#                'ParameterKey': 'EtlResourcesTemplateUrl',
#                'ParameterValue': etl_resources_template_url
#            },
#            {
#                'ParameterKey': 'WebAppResourcesTemplateUrl',
#                'ParameterValue': webapp_resources_template_url
#            },
#            {
#                'ParameterKey': 'SamTemplateUrl',
#                'ParameterValue': sam_template_url
#            },
#            {
#                'ParameterKey': 'SagemakerResourcesTemplateUrl',
#                'ParameterValue': sagemaker_resources_template_url
#            }
        ]

    awsutil.deploy_stack('envs-master', 'infrastructure/master.yml', parameters)


def main():
    _setup_secrets_and_keys()
    # check formatting of all CloudFormation templates in the infrastructure directory
    awsutil.validate_cfn_templates('infrastructure')
    _setup_cfn_templates_bucket()
    # _setup_iam_roles_and_idp()
    # _setup_cloud_trail()
    _setup_envs()

if __name__ == '__main__':
    main()
#    main(*sys.argv[1:])