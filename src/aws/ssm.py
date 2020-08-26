import boto3

def get_ssm_value(key, with_decryption=False):
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