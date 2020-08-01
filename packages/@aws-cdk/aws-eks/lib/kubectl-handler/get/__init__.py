import json
import logging
import os
import subprocess
import urllib3
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()

# these are coming from the kubectl layer
os.environ['PATH'] = '/opt/kubectl:/opt/awscli:' + os.environ['PATH']

outdir = os.environ.get('TEST_OUTDIR', '/tmp')
kubeconfig = os.path.join(outdir, 'kubeconfig')

def get_handler(event, context):
    logger.info(json.dumps(event))

    request_type = event['RequestType']
    props = event['ResourceProperties']

    # resource properties (all required)
    cluster_name  = props['ClusterName']
    role_arn      = props['RoleArn']

    # "log in" to the cluster
    subprocess.check_call([ 'aws', 'eks', 'update-kubeconfig',
        '--role-arn', role_arn,
        '--name', cluster_name,
        '--kubeconfig', kubeconfig
    ])

    resource_type   = props['ResourceType']
    resource_name   = props['ResourceName']
    json_path       = props['JsonPath']
    timeout_seconds = props['TimeoutSeconds']

    # json path should be surrouded with '{}'
    path = '{{{0}}}'.format(json_path)
    if request_type == 'Create' or request_type == 'Update':
        output = waitForOutput(
          ['get', resource_type, resource_name, "-o=jsonpath='{{{0}}}'".format(json_path)],
          int(timeout_seconds))
        return {'Data': {'Value': output}}
    elif request_type == 'Delete':
        pass
    else:
        raise Exception("invalid request type %s" % request_type)

def waitForOutput(args, timeout_seconds):

  end_time = time.time() + timeout_seconds

  while time.time() < end_time:
    # the output is surrounded with '', so we unquote
    logger.info(f'Running kubectl command to fetch value: {args}')
    output = kubectl(args).decode('utf-8')[1:-1]
    logger.info(f'Value is: {output} ')
    if output:
      return output
    time.sleep(10)

  raise RuntimeError(f'Timeout waiting for output from kubectl command: {args}')

def kubectl(args):
    retry = 3
    while retry > 0:
        try:
            cmd = [ 'kubectl', '--kubeconfig', kubeconfig ] + args
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            output = exc.output
            if b'i/o timeout' in output and retry > 0:
                logger.info("kubectl timed out, retries left: %s" % retry)
                retry = retry - 1
            else:
                raise Exception(output)
        else:
            logger.info(output)
            return output
