'''This script performs below tasks:
    1. Deploys instance from GCP gcp_controller.tar.gz
    2. Upload gcp_controller.tar.gz to GCP Bucket account if  gcp_controller.tar.gz is not present
    3. Delete previous controller if present
'''
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery as GCP_discovery
credentials = GoogleCredentials.get_application_default()
gcp = GCP_discovery.build('compute', 'v1', credentials=credentials)
from googleapiclient import errors as gerrors
import argparse
import requests
import logging
import yaml
import json
import traceback
import uuid
import datetime
import time

# [START storage_upload_file]
from google.cloud import storage


log = logging.getLogger('setup_env_gcp')
GCP_KEYFILE='/home/user/.ssh/google_compute_engine'



def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Setup environment')
    parser.add_argument(
        '--testbed-name',
        help='GCP testbed path', default=None)
    parser.add_argument(
        '--bucket_name',
        help='GCP bucket name', default=None)
    parser.add_argument(
        '--verbose',
        help='', default=None)
    parser.add_argument(
        '--project',
        help='project to create controller', default=None)
    parser.add_argument(
        '--zone',
        help='zone to create controller vm', default=None)
    parser.add_argument(
        '--subnetwork',
        help='subnetwork in which controller is getting created', default=None)
    parser.add_argument(
        '--source_file_name',
        help='GCP source file compressed tar.gz ', default=None)
    parser.add_argument(
        '--destination_blob_name',
        help='GCP destination file ', default=None)
    parser.add_argument(
        '--build-dir',
        help='Build dir path', default=None)
    parser.add_argument(
        '--machine-type',
        help='GCP Controller VM machine flavor', default="n1-standard-4")
    parser.add_argument(
        '--instance-name',
        help='GCP instances VM machine name', default="test-instance"
    )
    return parser.parse_args()


def execute(cmd):
        max_count = 10
        for count in range(max_count):
            try:
                return cmd.execute()
            except gerrors.HttpError as e:
                content = json.loads(e.content)
                error = content.get('error')
                message = error.get('message', "")
                code = error.get('code')
                reason = error.get('errors')[0].get('reason')
                if reason and (reason == 'rateLimitExceeded' or
                               reason == 'userRateLimitExceeded' or
                               reason == 'resourceNotReady'):
                    # retry the command
                    if count != max_count - 1:
                        time.sleep(30)
                        continue
            except Exception as e:
                log.error(e)


def instance_exist(project, zone, args):
    try:
        ins =  gcp.instances().get(project=args.project, zone=args.zone, instance=args.instance-name)
        result =  execute(ins)
        if result == None:
            return None
        result_ip = result['networkInterfaces'][0]['networkIP']
    except gerrors.HttpError as e:
        if e.code == 404:
            log.info("Instance doesn't exist")
    return result_ip



def delete_old_controller(project, zone, args):
    req = gcp.instances().delete(project=args.project, zone=args.zone, instance=args.instance-name)
    return execute(req)

def create_bucket(bucket_name, args):
    """Creates a new bucket."""
    storage_client = storage.Client(project = args.project)
    try:
        bucket = storage_client.create_bucket(args.bucket_name)
    except gerrors.HttpError as e:
        if e.code == 409:
            log.info("bucket already exist")
    log.info('Bucket {} created'.format(bucket.name))
    return args.bucket_name


def upload_blob(bucket_name, source_file_name, destination_blob_name, args):
    """Uploads a file to the bucket."""
    storage_client = storage.Client(project = args.project)
    bucket = storage_client.get_bucket(args.bucket_name)
    blob = bucket.blob(args.destination_blob_name)
    blob.upload_from_filename(args.source_file_name)
    log.info('File {} uploaded to {}.'.format(
        args.source_file_name,
        args.destination_blob_name))


def get_raw_url(args):
    raw_name = 'controller'
    image_url = "https://storage.googleapis.com/%s/%s" % (args.bucket_name, args.destination_blob_name)
    return image_url, raw_name


def image_creation(project,raw_name,image_url):
    image_body = {
        "name": raw_name,
        "rawDisk": {
            "source": image_url,
            }
        }

    request =  gcp.images().insert(project=args.project, body=image_body)
    return execute(request)


def image_exist(project, raw_name):
    try:
        request = gcp.images().get(project=args.project, image=raw_name)
        result =  execute(request)
        if result == None:
            return None
    except Exception as e:
        if  e.code == 404:
            log.info("Image doesn't exist")
    return result


def controller_create(project, zone, args):
    controller_name = args.instance-name
    image_url, raw_name = get_raw_url(args)
    instance_body = {
      "machineType": "projects/%s/zones/%s/machineTypes/%s" %(args.project, args.zone, args.machine_type),
      "name": "%s" % controller_name,
      "canIpForward": "true",
      "disks": [
        {
          "autoDelete": "true",
          "boot": "true",
          "initializeParams": {
        "sourceImage": "global/images/%s" %raw_name,
        "diskSizeGb": 80
          }
        }
      ],
      "networkInterfaces": [
        {
          "network": "projects/%s/global/networks/yournetworkname" %args.project,
          "subnetwork": "projects/astral-chassis-136417/regions/us-central1/subnetworks/%s" %args.subnetwork,
        }
      ],
      "serviceAccounts": [
          {
            "email": "xyz-compute@developer.gserviceaccount.com",
            "scopes": [
            "https://www.googleapis.com/auth/logging.write",
            "https://www.googleapis.com/auth/servicecontrol",
            "https://www.googleapis.com/auth/service.management.readonly",
            "https://www.googleapis.com/auth/trace.append",
            "https://www.googleapis.com/auth/devstorage.read_only",
            "https://www.googleapis.com/auth/monitoring.write",
            "https://www.googleapis.com/auth/compute"
            ]
        }
        ],
      "tags": {
          "items": [
              "http-server",
              "https-server"
              ]
          },
      }
    request = gcp.instances().insert(project=args.project, zone=args.zone, body=instance_body)
    return  execute(request)


def delete_blob(bucket_name, destination_blob_name, args):
    """Deletes a blob from the bucket."""
    try:
        storage_client = storage.Client(project = args.project)
        bucket = storage_client.get_bucket(args.bucket_name)
        blob = bucket.blob(args.destination_blob_name)
        blob.delete()
        log.info('Blob {} deleted.'.format(args.destination_blob_name))
    except Exception as e:
        pass



def delete_bucket(bucket_name, args):
    """Deletes a bucket. The bucket must be empty."""
    try:
        storage_client = storage.Client(args.project)
        bucket = storage_client.get_bucket(args.bucket_name)
        bucket.delete()
        log.info('Bucket {} deleted'.format(bucket.name))
    except Exception as e:
        pass
 

def main(args):
    log.info(args)
    image_url, raw_name = get_raw_url(args)
    controller_name = args.instance-name
    if instance_exist(args.project, args.zone, args):
        delete_old_controller(args.project, args.zone, args)

    if not image_exist(args.project, raw_name):
        create_bucket(args.bucket_name, args)
        upload_blob(args.bucket_name, args.source_file_name, args.destination_blob_name, args)
        image_creation(args.project,raw_name,image_url)
        time.sleep(90)
    results = {}
    results[controller_name] = controller_create(args.project, args.zone, args)
    time.sleep(160)
    controller_ip = instance_exist(args.project, args.zone, args)
    log.info("controller ip is %s" %controller_ip)
    delete_blob(args.bucket_name, args.destination_blob_name, args)
    delete_bucket(args.bucket_name, args)
    log.info('Controller %s has been configured.'%controller_name)

   
if __name__ == '__main__':
    args = parse_arguments()
    lvl = logging.DEBUG if args.verbose else logging.INFO
    log.setLevel(lvl)
    ch = logging.StreamHandler()
    ch.setLevel(lvl)
    formatter = logging.Formatter(
        '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    main(args)
