import boto3
import botocore
import glob
import json
import pyAesCrypt
import sys
from datetime import datetime
from github import Github
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

# git_deploy_priv_key_encrypted = 'git_ssh_key.priv.encrypted'
# git_deploy_pub_key_encrypted = 'git_ssh_key.pub.encrypted'
# git_deploy_priv_key_decrypted = 'GitDeployKey.priv'
# git_deploy_pub_key_decrypted = 'GitDeployKey.pub'

git_ssh_priv_key = 'GitSSHPrivateKey'
git_ssh_pub_key =  'GitSSHPublicKey'
git_ssh_key_name = 'babycheetah'

secrets_client = boto3.client('secretsmanager')
ec2_client = boto3.client('ec2')
cfn_client = boto3.client('cloudformation')
s3_client = boto3.client('s3')

def _secret_exists(secret_name):
    response = secrets_client.list_secrets()
    secret_found = False
    while response and not secret_found:
        for secret in response['SecretList']:
            if secret['Name'] == secret_name:
                secret_found = True
                break
        response = secrets_client.list_secrets(NextToken=response['NextToken']) if 'NextToken' in response else None
    return secret_found

def get_cfn_template_output(stack_name, output_key):
    desc = cfn_client.describe_stacks(StackName=stack_name)
    for output in desc['Stacks'][0]['Outputs']:
        if output['OutputKey'] == output_key:
            return output['OutputValue']
    raise Exception('No output {} found'.format(output_key))

def create_password(password_name):
    if not _secret_exists(password_name):
        password_dict = secrets_client.get_random_password(
            PasswordLength=20,
            ExcludeCharacters='"^&(),.?+=@/$\'\\`|~'
        )
        secrets_client.create_secret(
            Name = password_name,
            Description = password_name,
            SecretString = password_dict['RandomPassword']
        )

def save_secret(key_name, value):
    if not _secret_exists(key_name):
        secrets_client.create_secret(
            Name = key_name,
            Description = '{} SSH Key'.format(key_name),
            SecretString = value
            )
    else:
        secrets_client.update_secret(
            SecretId = key_name,
            Description = '{} SSH Key'.format(key_name),
            SecretString = value
            )

def save_rds_connectivity_secret(key_name, value):
    if not _secret_exists(key_name):
        secrets_client.create_secret(
            Name = key_name,
            SecretString = value
            )
    else:
        secrets_client.update_secret(
            SecretId = key_name,
            SecretString = value
            )

def generate_ssh_key_pair(key_name):
    try:
        response = ec2_client.describe_key_pairs(
            KeyNames=[key_name]
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            key_pair = ec2_client.create_key_pair(
                        KeyName = key_name
                       )
            if not _secret_exists(key_name):
                secrets_client.create_secret(
                    Name = key_name,
                    Description = '{} SSH Key'.format(key_name),
                    SecretString = key_pair['KeyMaterial']
                    )
            else:
                secrets_client.update_secret(
                    SecretId = key_name,
                    Description = '{} SSH Key'.format(key_name),
                    SecretString = key_pair['KeyMaterial']
                    )
        else:
            raise e

def generate_git_ssh_key_pair(api_token):
    if not _secret_exists(git_ssh_priv_key) or not _secret_exists(git_ssh_pub_key):
        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )
        private_key = key.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption()).decode('utf-8').strip()
        public_key = key.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH).decode('utf-8').strip()

        if not _secret_exists(git_ssh_priv_key):
            secrets_client.create_secret(
                Name = git_ssh_priv_key,
                Description = 'Git ssh private key',
                SecretString = private_key
            )
        else:
            secrets_client.update_secret(
                SecretId = git_ssh_priv_key,
                Description = 'Git ssh private key',
                SecretString = private_key
            )

        if not _secret_exists(git_ssh_pub_key):
            secrets_client.create_secret(
                Name = git_ssh_pub_key,
                Description = 'Git ssh public key',
                SecretString = public_key
            )
        else:
            secrets_client.update_secret(
                SecretId = git_ssh_pub_key,
                Description = 'Git ssh public key',
                SecretString = public_key
            )

        g = Github(api_token)
        user = g.get_user()
        key_exists = False
        existing_key = ''
        for userkey in user.get_keys():
            if userkey.key == public_key:
                key_exists = True
                existing_key = userkey

        if not key_exists:
            dateTimeObj = datetime.now()
            timestampStr = dateTimeObj.strftime("%Y%m%d%H%M%S%f")
            user.create_key('babycheetah-{}'.format(timestampStr), public_key)


# def decrypt_git_ssh_key(decryption_password):
#     pyAesCrypt.decryptFile(git_deploy_priv_key_encrypted, git_deploy_priv_key_decrypted, decryption_password, 64 * 1024)
#     decrypted_content = parse_file(git_deploy_priv_key_decrypted);
#     if not _secret_exists(git_deploy_priv_key_decrypted):
#         secrets_client.create_secret(
#             Name = git_deploy_priv_key_decrypted,
#             Description = 'Git deploy ssh private key',
#             SecretString = decrypted_content
#         )
#     else:
#         secrets_client.update_secret(
#             SecretId = git_deploy_priv_key_decrypted,
#             Description = 'Git deploy ssh private key',
#             SecretString = decrypted_content
#         )
#
#     pyAesCrypt.decryptFile(git_deploy_pub_key_encrypted, git_deploy_pub_key_decrypted, decryption_password, 64 * 1024)
#     decrypted_content = parse_file(git_deploy_pub_key_decrypted);
#     if not _secret_exists(git_deploy_pub_key_decrypted):
#         secrets_client.create_secret(
#             Name = git_deploy_pub_key_decrypted,
#             Description = 'Git deploy ssh public key',
#             SecretString = decrypted_content
#         )
#     else:
#         secrets_client.update_secret(
#             SecretId = git_deploy_pub_key_decrypted,
#             Description = 'Git deploy ssh public key',
#             SecretString = decrypted_content
#         )

def validate_cfn_templates(path):
    for cfn_template in glob.glob('{}/*.yml'.format(path)):
        print ('Validation cfn template {}'.format(cfn_template))
        parse_template(cfn_template)

def stack_exists(stack_name):
    paginator = cfn_client.get_paginator('list_stacks')
    response_iterator = paginator.paginate()
    for page in response_iterator:
        stacks = page['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName']:
                return True
    return False

def get_secret_string(secret_id):
    return secrets_client.get_secret_value(SecretId = secret_id)['SecretString']

def parse_template(template):
    template_data = parse_file(template)
    cfn_client.validate_template(TemplateBody=template_data)
    return template_data

def parse_file(file):
    with open(file) as fileobj:
        content = fileobj.read()
    return content.strip()

def deploy_stack(stack_name, template, parameters):

    template_data = parse_template(template)
    #parameter_data = json.dumps(parameters)

    params = {
        'StackName': stack_name,
        'TemplateBody': template_data,
        'Parameters': parameters,
        'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
    }

    try:
        if stack_exists(stack_name):
            print('Updating {}'.format(stack_name))
            stack_result = cfn_client.update_stack(**params)
            waiter = cfn_client.get_waiter('stack_update_complete')
        else:
            print('Creating {}'.format(stack_name))
            stack_result = cfn_client.create_stack(**params)
            waiter = cfn_client.get_waiter('stack_create_complete')
        print('...waiting for stack to be ready...')
        waiter.wait(StackName=stack_name)
    except botocore.exceptions.ClientError as ex:
        error_message = ex.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print('No changes')
        else:
            raise ex
    return cfn_client.describe_stacks(StackName=stack_name)
