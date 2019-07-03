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

jenkins_password_name = 'JenkinsPassword'
rds_password_name = 'RdsPassword'
rds_user_name = 'RdsUserName'
rds_app_user = 'appuser'
rds_db_name = 'RdsDbName'
db_name = 'nrfc'
db_engine = 'mysql'
db_port = '3306'
default_ssh_key_pair_name = 'DefaultKey'
bastion_ssh_key_pair_name = 'BastionKey'
git_api_token_name = 'GitApiToken'
# git_repo = 'git@github.com:enjaygee/python-cloudformation.git'
# git_user_name = 'babycheetah-svc'


def _setup_secrets_and_keys(api_token):
    awsutil.save_secret(git_api_token_name, api_token)
    awsutil.generate_ssh_key_pair(default_ssh_key_pair_name)
    awsutil.generate_ssh_key_pair(bastion_ssh_key_pair_name)
    awsutil.create_password(jenkins_password_name)

    awsutil.generate_git_ssh_key_pair(api_token)

    awsutil.save_secret(rds_user_name, rds_app_user)
    awsutil.save_secret(rds_db_name, db_name)

    for env in ['dev', 'test', 'prod']:
      app_db_password_secret_name = env + '/' + rds_password_name
      awsutil.create_password(app_db_password_secret_name)