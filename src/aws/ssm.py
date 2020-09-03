import boto3

def get_ssm_value(key, with_decryption=True):
    ssm = boto3.client('ssm')
    value = None
    error = ''
    try:
        param = ssm.get_parameter(Name=key, WithDecryption=with_decryption)
        value = param['Parameter']['Value']
        if not value:
            error = f'SSM key `{key}` is not defined \n'
    except Exception as ex:
        error = f'Cannot get ssm value for key: {key}'
    return error, value
def put_ssm_value(key, value, type='SecureString'):
    ssm = boto3.client('ssm')
    ssm.put_parameter(Name=key,Value=value,Type=type,Overwrite=True)