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

def main():
    _setup_secrets_and_keys()


if __name__ == '__main__':
    main()
#    main(*sys.argv[1:])