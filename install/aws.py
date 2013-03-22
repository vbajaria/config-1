import boto, os, time
from fabric.api import run, env
from fabric.api import local, settings, abort
from fabric.context_managers import hide, cd
from fabric.contrib.console import confirm
from boto.exception import BotoServerError
from boto.ec2.elb import HealthCheck
from boto.s3.bucket import Bucket

HOME = os.getenv('HOME')

# remote linux user
env.user = 'ubuntu'

env.key_filename = [
    '%s/.ssh/Ntropy1.pem' %HOME
]

AWS_ACCOUNT_ID = '242358675102'
AWS_ACCESS_KEY_ID = 'AKIAJZX3DTK5VLHPLE3Q'
AWS_SECRET_ACCESS_KEY = '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'

ec2_conn = None
elb_conn = None

#################################################################################
# CONNECTIONS
#################################################################################
def get_ec2_conn():
    if not ec2_conn:
        globals()['ec2_conn'] = boto.connect_ec2(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    return ec2_conn

def get_elb_conn():
    if not elb_conn:
        globals()['elb_conn'] = boto.connect_elb(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    return elb_conn

#################################################################################
# LOADBALANCER COMMON
#################################################################################
def get_loadbalancer_name(service_type, org='ntropy'):
    return '%s-%s' %(org, service_type)

def get_loadbalancer(service_type, org='ntropy'):
    lb_name = get_loadbalancer_name(service_type=service_type, org=org)
    return get_elb_conn().get_all_load_balancers(load_balancer_names=[lb_name])[0]

def get_or_create_loadbalancer(service_type, org='ntropy'):
    try:
        return get_loadbalancer(service_type=service_type)
    except BotoServerError:
        if service_type == 'beacon-web':
            return create_beacon_web_loadbalancer()
        elif service_type == 'kafka':
            return create_kafka_loadbalancer()
        else:
            return None

def add_instances_to_loadbalancer(service_type, instances=None, org='ntropy'):
    lb = get_or_create_loadbalancer(service_type=service_type, org=org)
    if lb:
        if not instances:
            instances = get_instances(service_type=service_type, org=org, state='running')
        print 'Adding %d instance(s) to the load balancer' %len(instances)
        lb.register_instances([x.id for x in instances])

def remove_instances_from_loadbalancer(service_type, instances, org='ntropy'):
    lb = get_or_create_loadbalancer(service_type=service_type, org=org)
    if lb:
        lb.deregister_instances([x.id for x in instances])

#################################################################################
# SERVERS COMMON
#################################################################################
def get_instances(org='ntropy', service_type=None, state=None, master=False, slave=False):
    filters = {}
    if service_type:
        filters = {'tag:Name': '%s-%s' %(org, service_type)}

        if master and slave:
            raise Exception("Cannot set both master and slave")

        if master:
            filters['tag:Name2'] = '%s-%s-master' %(org, service_type)
        elif slave:
            filters['tag:Name2'] = '%s-%s-slave' %(org, service_type)

    instances = []
    for r in get_ec2_conn().get_all_instances(filters=filters):
        for instance in r.instances:
            if state and instance.state == state:
                instances.append(instance)
            elif not state:
                instances.append(instance)
    return instances

def get_service_ami(service_type, org='ntropy'):
    filters = {'tag:Name': service_type}
    return get_ec2_conn().get_all_images(filters=filters)[0]

def get_security_groups(service_type):
    return ec2_conn.get_all_security_groups(groupnames=service_type)

def create_new_instances(service_type, instance_type, org='ntropy', num_instances=1):
    conn = get_ec2_conn()
    total_running_instances = len(get_instances(service_type=service_type, org=org, state='running'))

    if total_running_instances > 0:
        if service_type in ['mysql', 'storm', 'hbase']:
            print 'Adding %d %s server(s) to an already running cluster of %d (1 master and %d slave(s))' %(
                num_instances, service_type, total_running_instances, total_running_instances-1)
        else:
            print 'Adding %d %s server(s) to an already running cluster of %d' %(
                num_instances, service_type, total_running_instances)
    else:
        print 'Creating a new cluster by adding %d %s server(s)' %(num_instances, service_type)

    ami = get_service_ami(service_type=service_type)
    reservation = conn.run_instances(ami.id, max_count=num_instances, instance_type=instance_type,
        key_name='Ntropy1', security_groups=get_security_groups(service_type=service_type),
        placement='us-east-1a')

    try:
        conn.create_tags([x.id for x in reservation.instances], tags={'Name':'%s-%s' %(org, service_type)})
    except boto.exception.EC2ResponseError:
        time.sleep(30)
        conn.terminate_instances([x.id for x in reservation.instances])
        raise Exception, "Could not start instances. Please try again."

    for index, instance in enumerate(reservation.instances):
        if service_type in ['mysql', 'storm', 'hbase']:
            if index == 0 and total_running_instances == 0:
                conn.create_tags(instance.id, tags={'Name2':'%s-%s-master' %(org, service_type)})
            else:
                conn.create_tags(instance.id, tags={'Name2':'%s-%s-slave' %(org, service_type)})

#################################################################################
# BEACON SERVERS LOADBALANCER
#################################################################################
def create_beacon_web_loadbalancer(org='ntropy'):
    regions = ['us-east-1a']
    ports = [(80, 80, 'http')]
    lb_name = get_loadbalancer_name(service_type='beacon-web', org=org)
    lb = elb_conn.create_load_balancer(lb_name, regions, ports)
    hc = HealthCheck(interval=30, timeout=5, healthy_threshold=4, unhealthy_threshold=2, target='HTTP:80/healthcheck')
    lb.configure_health_check(hc)
    print 'Created a load balancer for the beacon service'
    return lb

def create_kafka_loadbalancer(org='ntropy'):
    regions = ['us-east-1a']
    ports = [(9092, 9092, 'tcp')]
    lb_name = get_loadbalancer_name(service_type='kafka', org=org)
    lb = elb_conn.create_load_balancer(lb_name, regions, ports)
    hc = HealthCheck(interval=30, timeout=5, healthy_threshold=4, unhealthy_threshold=2, target='TCP:9092')
    lb.configure_health_check(hc)
    print 'Created a load balancer for kafka'
    return lb

#################################################################################
# ELASTIC IPS
#################################################################################
def get_all_ips():
    return get_ec2_conn().get_all_addresses()

#################################################################################
# S3
#################################################################################
def generate_url(bucket, key):
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(bucket)
    key = bucket.get_key(key)
    return key.generate_url(expires_in=60)

