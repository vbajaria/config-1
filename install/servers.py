import boto, os, aws, time, re, socket
from fabric.api import *
from fabric.context_managers import *

HOME = os.getenv('HOME')
env.user = 'ubuntu'
env.key_filename = ['%s/.ssh/Ntropy1.pem' %HOME]

#################################################################################
# ENV.HOSTS
#################################################################################
def get_hosts(org='ntropy', service_type=None, state=None, master=False, slave=False, remote=True):
    if remote:
        return [x.public_dns_name for x in aws.get_instances(
            service_type=service_type, org=org, state=state, master=master, slave=slave)]
    else:
        return ['localhost']

def set_hosts(org='ntropy', service_type=None, state='running', master=False, slave=False, remote=True):
    env.hosts = get_hosts(org=org, service_type=service_type, state=state, master=master, slave=slave, remote=remote)
    print env.hosts

#################################################################################
# PUSH DATA
#################################################################################
def install_push_script():
    put('/home/premal/push_test_data.py', '/home/ubuntu/')

def run_push_script(endpoint, token, t=None):
    if t:
        run('nohup sh -c "python push_test_data.py %s %s %s &"' %(endpoint, token, t))
    else:
        run('nohup sh -c "python push_test_data.py %s %s &"' %(endpoint, token))

def kill_push_script():
    sudo('pkill -f push_test_data.py')

#################################################################################
# APT-GET
#################################################################################
def apt_get_update():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        print 'Updating apt repo'
        run('sudo apt-get update')

def install_apt_sources():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        print 'Installing required apt-get sources'
        sudo('wget https://raw.github.com/premal/config/master/apt/mkpasswd.sources.list -O /etc/apt/sources.list.d/mkpasswd.sources.list')

def install_basic_software():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        install_apt_sources()
        apt_get_update()

        print 'Installing htop iotop sysstat git mkpasswd ntp locate liblzo2-dev'
        run('sudo apt-get -y install htop iotop sysstat git mkpasswd ntp locate liblzo2-dev')

        print 'Installing monit'
        install_monit()

        install_ganglia_slave()

        print 'Installing ssh config'
        install_ssh_config()

        print 'Installing /etc/hosts'
        install_etc_hosts()

#################################################################################
# ETC HOSTS
#################################################################################
def install_etc_hosts(org='ntropy'):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l etc_hosts')

    if result.failed:
        with settings(hide('warnings', 'running', 'stdout', 'stderr')):
            run('wget https://raw.github.com/premal/config/master/etc_hosts -O etc_hosts')
            print 'Downloaded hosts file'

    etc_hosts = []
    for instance in aws.get_instances(org=org, state='running'):
        etc_hosts.append(('%s\t%s %s' %(instance.private_ip_address, instance.public_dns_name, instance.private_dns_name)))

    code_lines = ["f = open('etc_hosts').read()" ,
                  "out = f.replace('REPLACE_WITH_HOSTS', '''%s''')" %'\n'.join(etc_hosts),
                  "f = open('/etc/hosts', 'w')",
                  "f.write(out)",
                  "f.close()"]

    with settings(hide('warnings', 'running', 'stdout', 'stderr')):
        sudo('python -c "%s"' %'; '.join(code_lines))
        print 'Updated hosts file'

#################################################################################
# SERVICE CONFIG
#################################################################################
def install_service_config():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /etc/init.d/service_config.sh')

    if result.failed:
        with settings(hide('warnings', 'running', 'stdout', 'stderr')):
            sudo('wget https://raw.github.com/premal/config/master/service_config.sh -O /etc/init.d/service_config.sh')

    install_daemon_dirs()

def install_daemon_dirs():
    with settings(hide('warnings', 'running', 'stdout', 'stderr')):
        sudo('mkdir -p /var/log/service')
        sudo('chmod 777 -R /var/log/service/')

        sudo('mkdir -p /var/service/pids')
        sudo('chmod 777 -R /var/service/pids/')

#################################################################################
# INIT.D
#################################################################################
def install_initd(service):
    with settings(hide('warnings', 'running', 'stdout', 'stderr')):
        sudo('wget https://github.com/premal/config/raw/master/%s/init.d -O /etc/init.d/%s' %(service, service))
        sudo('chmod a+x /etc/init.d/%s' %service)
        print 'Installed startup script'

#################################################################################
# USER
#################################################################################
def install_user(username, password):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run(' grep "^%s:" /etc/passwd' %username)

    if result.failed:
        with settings(hide('warnings', 'running', 'stdout', 'stderr')):
            run('sudo addgroup %s' %username)
            run('sudo useradd %s -g %s -m -s /bin/bash -p `mkpasswd %s`' %(username, username, password))
            print 'Created user: (%s) in group: (%s)' %(username, username)

#################################################################################
# MONIT
#################################################################################
def install_monit():
    with settings(hide('warnings', 'running', 'stdout', 'stderr')):
        run('sudo apt-get install -y monit')
        print 'Installed monit'

#################################################################################
# UPDATE CONFIG
#################################################################################
def install_update_config():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l update_config.py')

    if result.failed:
        run('wget https://github.com/premal/config/raw/master/update_config.py -O update_config.py')

#################################################################################
# BASHRC
#################################################################################
def install_bashrc(service_type):
    install_update_config()

    run('wget https://raw.github.com/premal/config/master/%s/.%src -O /home/ubuntu/.%src' %(service_type, service_type, service_type))

    code = ["if [ -f .%src ]; then" %service_type,
            "    . ~/.%src" %service_type,
            "fi\n"]

    run('python update_config.py .bashrc "%s"' %'\n'.join(code))        
    run('source /home/ubuntu/.bashrc')

#################################################################################
# SECURITY LIMITS
#################################################################################
def install_security_limits(user, org='ntropy'):
    install_update_config()

    security_map = dict(
        storm = dict(
            nproc_soft = dict(
                value = 1024,
            ),
            nproc_hard = dict(
                value = 1024,
            ),
            nofile = dict(
                type = '-',
                value = 65535,
            ),
        ),
        hadoop = dict(
            nproc_soft = dict(
                value = 1024,
            ),
            nproc_hard = dict(
                value = 1024,
            ),
            nofile = dict(
                type = '-',
                value = 65535,
            ),
        ),
        hbase = dict(
            nproc = dict(
                type = '-',
                value = 1024,
            ),
            nofile = dict(
                type = '-',
                value = 65535,
            ),
        )
    )

    for key, value in security_map.get(user).iteritems():
        config = [user]
        if value.has_key('type'):
            config.append(value.get('type'))
            config.append(key)
        else:
            config.append(key.split('_')[1])
            config.append(key.split('_')[0])
        config.append(str(value.get('value')))
        config_line = '\t'.join(config)
        sudo('python update_config.py /etc/security/limits.conf "%s"' %config_line)

#################################################################################
# GIT
#################################################################################
def checkout_branch(branch):
    with cd('/var/ntropy'):
        run('git checkout %s' %branch)
        run('git pull origin %s' %branch)

def install_code():
    install_git_access()

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /var/ntropy')

    if result.failed:
        with cd('/var'):
            sudo('mkdir -p ntropy')
            sudo('chown ubuntu:ubuntu ntropy')
            run('git clone git@github.com:vbajaria/ntropy.git')

    remove_git_access()

def install_git_access():
    run('wget "%s" -O ~/.ssh/id_rsa' %aws.generate_url('bootstrap-keys', 'id_rsa'))
    sudo('chmod 600 /home/%s/.ssh/id_rsa' %env.user)
    run('wget "%s" -O ~/.ssh/id_rsa.pub' %aws.generate_url('bootstrap-keys', 'id_rsa'))
    sudo('chmod 644 /home/%s/.ssh/id_rsa.pub' %env.user)

def remove_git_access():
    sudo('rm ~/.ssh/id_rsa*')

#################################################################################
# SSH
#################################################################################
def install_ssh_config():
    put('/home/premal/ssh_config', '/etc/ssh/ssh_config', use_sudo=True)
    run('sudo service ssh restart')

#################################################################################
# KEY MANAGEMENT
#################################################################################
def install_key():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('wget "%s" -O Ntropy1.pem' %aws.generate_url('bootstrap-software', 'Ntropy1.pem'))
        run('chmod 400 Ntropy1.pem')

def delete_key():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('rm Ntropy1.pem')
    
#################################################################################
# MONITORING
#################################################################################
def install_monit_config():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('wget https://github.com/premal/config/raw/master/monit/monitrc -O /etc/monit/monitrc')

def install_monitoring_config(service, sub_service=None):
    filename = service
    if sub_service:
        filename = '%s-%s' %(service, sub_service)

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('wget https://github.com/premal/config/raw/master/%s/%s.monit -O /etc/monit/conf.d/%s.monit' %(service, filename, filename))
        sudo('/etc/init.d/monit restart')

#################################################################################
# JAVA
#################################################################################
def install_java():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/jvm/sun-java6')

    if result.failed:
        print 'Downloading and installing Java'
        with settings(hide('running', 'stdout', 'warnings')):
            run('wget https://s3.amazonaws.com/bootstrap-software/jdk-6u38-linux-x64.bin -O jdk-6u38-linux-x64.bin')
            run('sudo chmod +x jdk-6u38-linux-x64.bin')
            run('echo -ne \'\n\' |./jdk-6u38-linux-x64.bin')
            run('sudo mkdir -p /usr/lib/jvm')
            run('sudo mv jdk1.6.0_38 /usr/lib/jvm/sun-java6')
            run('sudo update-alternatives --install /usr/bin/javac javac /usr/lib/jvm/sun-java6/bin/javac 1')
            run('sudo update-alternatives --install /usr/bin/java java /usr/lib/jvm/sun-java6/bin/java 1')
            run('sudo update-alternatives --install /usr/bin/javaws javaws /usr/lib/jvm/sun-java6/bin/javaws 1')
            run('sudo update-alternatives --set javac /usr/lib/jvm/sun-java6/bin/javac')
            run('sudo update-alternatives --set java /usr/lib/jvm/sun-java6/bin/java')
            run('sudo update-alternatives --set javaws /usr/lib/jvm/sun-java6/bin/javaws')
            run('rm jdk-6u38-linux-x64.bin')
            run('export JAVA_HOME=/usr/lib/jvm/sun-java6/')
    else:
        print 'Java is already installed'

#################################################################################
# MYSQL SERVER SOFTWARE SETUP
#################################################################################
def setup_mysql_server(org='ntropy'):
    install_basic_software()
    install_mysql()
    setup_ntropy_database()

def get_mysql_root_pass():
    return 'ntropydb'

def get_mysql_ntropy_pass():
    return '2bc869f70e28759f57561b5303f4883c'

def install_mysql():
    # TODO change this to installing from a binary
    run('sudo apt-get -y install mysql-server')

def setup_ntropy_database():
    # TODO change mysql remote host access, not allow %
    command =  'CREATE DATABASE ntropy;'
    command += 'CREATE USER ntropy IDENTIFIED BY \'%s\';' %get_mysql_ntropy_pass()
    command += 'GRANT ALL ON ntropy.* TO ntropy@\'%%\' IDENTIFIED BY \'%s\';' %get_mysql_ntropy_pass()
    command += 'FLUSH PRIVILEGES;'
    run('mysql -u root -p%s -e "%s"' %(get_mysql_root_pass(), command))

def install_mysql_config(org='ntropy', branch='master', checkout=True):
    install_code()
    checkout_branch(branch)
    run('sudo cp /var/ntropy/conf/mysql/mysql-master.my.cnf /etc/mysql/my.cnf')

#################################################################################
# MYSQL SERVERS SERVICES
#################################################################################
def start_mysql():
    run('sudo /etc/init.d/mysql start')

def restart_mysql():
    run('sudo /etc/init.d/mysql restart')

#################################################################################
# BEACON SERVERS SOFTWARE SETUP
#################################################################################
def setup_beacon_server(org='ntropy'):
    install_basic_software()
    install_java()

#################################################################################
# BEACON SERVERS CODE AND CONFIG SETUP
#################################################################################
def install_beacon_code_config(org='ntropy'):
    install_beacon_jar()
    install_beacon_config()

    if org in ['ntropy', 'grepdata']:
        install_beacon_https_cert()

    install_service_config()
    install_initd(service='beacon')
    install_monitoring_config(service='beacon')
    install_etc_hosts(org=org)

def install_beacon_jar():
    install_key()

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('scp -i Ntropy1.pem kickstart.grepdata.com:/var/ntropy/dataapi/target/dataapi-0.1.jar .')
        sudo('mkdir -p /usr/lib/beacon')
        sudo('cp dataapi-0.1.jar /usr/lib/beacon/dataapi-0.1.jar')
        print 'Installed JAR'

    delete_key()

def install_beacon_config():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('mkdir -p /usr/lib/beacon')
        sudo('wget https://github.com/premal/config/raw/master/beacon/beacon-dev-config.yml -O /usr/lib/beacon/beacon-dev-config.yml')
        sudo('wget https://github.com/premal/config/raw/master/beacon/beacon-prod-config.yml -O /usr/lib/beacon/beacon-prod-config.yml')
        sudo('wget https://github.com/premal/config/raw/master/beacon/beacon-prod-https-config.yml -O /usr/lib/beacon/beacon-prod-https-config.yml')
        print 'Downloaded Configs'

def install_beacon_https_cert():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('wget "%s" -O ~/.ssh/beacon.keystore' %aws.generate_url('bootstrap-keys', 'beacon.keystore'))
        sudo('chmod 400 ~/.ssh/beacon.keystore')
    
#################################################################################
# BEACON SERVERS SERVICES
#################################################################################
def _validate_service_type(service_type):
    if service_type not in ['beacon-dev', 'beacon-prod', 'beacon-prod-https']:
        raise ValueError, "Valid values are beacon-dev, beacon-prod and beacon-prod-https"

def start_beacon_server(service_type):
    _validate_service_type(service_type)
    sudo('nohup sh -c "/etc/init.d/beacon %s start &"' %(service_type))

def stop_beacon_server(service_type):
    _validate_service_type(service_type)
    sudo('/etc/init.d/beacon %s stop' %(service_type))

def restart_beacon_server(service_type):
    _validate_service_type(service_type)
    stop_beacon_server(service_type)
    start_beacon_server(service_type)

#################################################################################
# API SERVER SOFTWARE
#################################################################################
def setup_api_server(org='ntropy'):
    install_basic_software()
    install_java()

#################################################################################
# API SERVERS CODE AND CONFIG SETUP
#################################################################################
def install_api_code_config(org='ntropy'):
    install_api_jar()
    install_api_config()

    if org in ['ntropy', 'grepdata']:
        install_api_https_cert()

    install_service_config()
    install_initd(service='api')
    install_monitoring_config(service='api')
    install_etc_hosts(org=org)

def install_api_jar():
    install_key()

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('scp -i Ntropy1.pem kickstart.grepdata.com:/var/ntropy/dataapi/target/dataapi-0.1.jar .')
        sudo('mkdir -p /usr/lib/api')
        sudo('cp dataapi-0.1.jar /usr/lib/api/dataapi-0.1.jar')
        print 'Installed JAR'

    delete_key()

def install_api_config(org='ntropy'):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('mkdir -p /usr/lib/api')
        sudo('wget https://github.com/premal/config/raw/master/api/api-dev-config.yml -O /usr/lib/api/api-dev-config.yml')

        instances = aws.get_instances(service_type='zookeeper', org=org, state='running')
        zkServers = '\n            - '.join(['\\\\"%s\\\\"' %x.public_dns_name for x in instances])

        if not instances:
            # default to localhost
            zkServers = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

        for config_file in ['api-prod-config.yml', 'api-prod-https-config.yml']:
            sudo('wget https://github.com/premal/config/raw/master/api/%s -O %s' %(config_file, config_file))
            code_lines = ["f = open('%s').read()" %config_file,
                          "out = f.replace('REPLACE_WITH_ZOOKEEPER_SERVERS', '''%s''')" %zkServers,
                          "f = open('/usr/lib/api/%s', 'w')" %config_file,
                          "f.write(out)",
                          "f.close()"]    
            sudo('python -c "%s"' %'; '.join(code_lines))
        print 'Downloaded Configs'

def install_api_https_cert():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('wget "%s" -O ~/.ssh/api.keystore' %aws.generate_url('bootstrap-keys', 'api.keystore'))
        sudo('chmod 400 ~/.ssh/api.keystore')
    
#################################################################################
# API SERVER SERVICES
#################################################################################
def _validate_service_type(service_type):
    if service_type not in ['api-dev', 'api-prod-https']:
        raise ValueError, "Valid values are api-dev and api-prod-https"

def start_api_server(service_type):
    _validate_service_type(service_type)
    sudo('nohup sh -c "/etc/init.d/api %s start &"' %(service_type))

def stop_api_server(service_type):
    _validate_service_type(service_type)
    sudo('/etc/init.d/api %s stop' %(service_type))

def restart_api_server(service_type):
    _validate_service_type(service_type)
    stop_api_server(service_type)
    start_api_server(service_type)

#################################################################################
# FRONTEND SERVER SOFTWARE SETUP
#################################################################################
def setup_frontend_server(org='ntropy'):
    install_nginx()
    install_django()
    install_tastypie()
    install_python_mysqldb()

def install_nginx():
    sudo('apt-get -y install nginx')
    sudo('apt-get -y install python-flup')

def install_django():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('python -c "import django;"')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/Django-1.4.3.tar.gz -O Django-1.4.3.tar.gz')
        run('tar xzf Django-1.4.3.tar.gz')
        with cd('Django-1.4.3'):
            run('sudo python setup.py install')
        run('rm Django-1.4.3.tar.gz')
        run('sudo rm -rf Django-1.4.3')
    else:
        print 'Django is already installed'

def install_tastypie():
    sudo('apt-get -y install python-pip')
    sudo('pip install django-tastypie')

def install_python_mysqldb():
    run('sudo apt-get -y install python-mysqldb')

#################################################################################
# FRONTEND CONFIG
#################################################################################
def install_frontend_config():
    install_nginx_config()
    install_sitecustomize()
    install_django_config()
    install_django_settings()

def install_nginx_config():
    run('wget https://github.com/premal/config/raw/master/frontend/nginx.conf -O nginx.conf')

    code_lines = ["f = open('nginx.conf').read()" ,
                  "out = f.replace('REPLACE_WITH_WORKER_PROCESSES', '4')",
                  "out = out.replace('REPLACE_WITH_NUM_WORKER_CONNECTIONS', '1024')",
                  "f = open('/etc/nginx/nginx.conf', 'w')",
                  "f.write(out)",
                  "f.close()"]
    run('sudo python -c "%s"' %'; '.join(code_lines))

def install_sitecustomize():
    sudo('mkdir -p /var/log/ntropy')
    sudo('chmod 777 /var/log/ntropy/')
    run('touch /var/log/ntropy/error.log')
    sudo('wget https://github.com/premal/config/raw/master/frontend/sitecustomize.py -O /etc/python2.7/sitecustomize.py')

def install_django_config():
    run('wget https://github.com/premal/config/raw/master/frontend/start_django -O start_django')

    code_lines = ["f = open('start_django').read()", 
                  "out = f.replace('MAX_CHILDREN', '4')",
                  "out = out.replace('MAX_SPARE', '4')",
                  "out = out.replace('MIN_SPARE', '4')",
                  "f = open('/etc/django/start_django', 'w')",
                  "f.write(out)",
                  "f.close()"]
    sudo('mkdir -p /etc/django')
    sudo('python -c "%s"' %'; '.join(code_lines))
    sudo('chmod +x /etc/django/start_django')

def install_django_settings(org='ntropy'):
    run('wget https://github.com/premal/config/raw/master/frontend/django_settings.py -O django_settings.py')

    mysql_master_ip = aws.get_instances(service_type='mysql', org=org, state='running')[0].private_ip_address
    code_lines = ["f = open('django_settings.py').read()" ,
                  "out = f.replace('REPLACE_MYSQL_IP', '%s')" %mysql_master_ip,
                  "f = open('/var/ntropy/ui/web/server/settings.py', 'w')",
                  "f.write(out)",
                  "f.close()"]
    run('python -c "%s"' %'; '.join(code_lines))

def update_frontend_code(branch='develop'):
    pass
    
#################################################################################
# FRONTEND SERVICES
#################################################################################
def frontend_start():
    sudo('/etc/init.d/nginx restart; sleep 5')
    sudo('/etc/django/start_django')

#################################################################################
# ZOOKEEPER SOFTWARE SETUP
#################################################################################
def setup_zookeeper_server(org='ntropy'):
    install_basic_software()
    install_java()
    install_user('zookeeper', 'zookeeper')
    install_zookeeper()

def install_zookeeper():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/zookeeper')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/zookeeper-3.4.5.tar.gz -O zookeeper-3.4.5.tar.gz')
        sudo('mv zookeeper-3.4.5.tar.gz /usr/lib/')

        with cd('/usr/lib/'):
            sudo('tar xzf zookeeper-3.4.5.tar.gz')
            sudo('ln -s zookeeper-3.4.5 zookeeper')
            sudo('rm zookeeper-3.4.5.tar.gz')
            sudo('chown -R zookeeper:zookeeper /usr/lib/zookeeper/')
            sudo('chown -R zookeeper:zookeeper /usr/lib/zookeeper')
        
        print 'Installed Zookeeper'
    else:
        print 'Zookeeper is already installed'

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('mkdir -p /grepdata/zookeeper')
        sudo('chown -R zookeeper:zookeeper /grepdata/zookeeper')

#################################################################################
# ZOOKEEPER CODE AND CONFIG SETUP
#################################################################################
def install_zookeeper_config(org='ntropy'):
    install_zoo_data_dir()
    install_zoo_log_dir()
    install_zkEnv()
    install_zoo_cfg(org=org)
    install_bashrc(service_type='zookeeper')
    install_monitoring_config(service='zookeeper')
    install_etc_hosts(org=org)

def install_zoo_data_dir():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('mkdir -p /grepdata/zookeeper')
        sudo('chown -R zookeeper:zookeeper /grepdata/zookeeper')

def install_zoo_log_dir():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('mkdir -p /var/log/zookeeper')
        sudo('chown -R zookeeper:zookeeper /var/log/zookeeper')
        
def install_zkEnv():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('wget https://github.com/premal/config/raw/master/zookeeper/zkEnv.sh -O /usr/lib/zookeeper/bin/zkEnv.sh')
        sudo('chown zookeeper:zookeeper /usr/lib/zookeeper/bin/zkEnv.sh')

def install_zoo_cfg(org='ntropy1'):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('wget https://github.com/premal/config/raw/master/zookeeper/zoo.cfg -O zoo.cfg')

        zkInstances = aws.get_instances(service_type='zookeeper', org=org, state='running')
        zkServers = '\n'.join(['server.%s=%s:2888:3888' %(''.join(re.findall(r'\d+', x.ip_address)), x.public_dns_name) for x in zkInstances])

        # defaults to localhost
        if not zkServers:
            zkServers = 'server.1=%s:2888:3888' %run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

        code_lines = ["f = open('zoo.cfg').read()" ,
                      "out = f.replace('REPLACE_WITH_ZOOKEEPER_SERVERS', '''%s''')" %zkServers,
                      "f = open('/usr/lib/zookeeper/conf/zoo.cfg', 'w')",
                      "f.write(out)",
                      "f.close()"]
        sudo('python -c "%s"' %'; '.join(code_lines), user='zookeeper')

        for instance in zkInstances:
            print ''.join(re.findall(r'\d+', instance.private_ip_address))
            if (''.join(re.findall(r'\d+', instance.private_ip_address)) ==
                run('python -c "import socket, re; print \'\'.join(re.findall(r\'\d+\', socket.gethostbyname(socket.gethostname())))"')):
                code_lines = ["f = open('/grepdata/zookeeper/myid', 'w')" ,
                              "f.write('%s')" %int(''.join(re.findall(r'\d+', instance.ip_address))),
                              "f.close()"]
                sudo('python -c "%s"' %'; '.join(code_lines), user='zookeeper')

#################################################################################
# ZOOKEEPER SERVICES
#################################################################################
def start_zookeeper():
    with cd('/usr/lib/zookeeper'):
        run('sudo -u zookeeper bin/zkServer.sh start')

def stop_zookeeper():
    with cd('/usr/lib/zookeeper'):
        run('sudo -u zookeeper bin/zkServer.sh stop')

def restart_zookeeper():
    with cd('/usr/lib/zookeeper'):
        run('sudo -u zookeeper bin/zkServer.sh restart')

#################################################################################
# KAFKA SOFTWARE SETUP
#################################################################################
def setup_kafka_server():
    install_basic_software()
    install_java()
    install_user('kafka', 'kafka')
    install_kafka()

def install_kafka():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/kafka')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/kafka-0.7.2-incubating-src.tgz -O kafka-0.7.2.tgz')
        sudo('mv kafka-0.7.2.tgz /usr/lib/')

        with cd('/usr/lib/'):
            sudo('tar xzf kafka-0.7.2.tgz')
            sudo('rm kafka-0.7.2.tgz')
            sudo('ln -s kafka-0.7.2-incubating-src kafka')
            sudo('chown -R kafka:kafka /usr/lib/kafka/')
            sudo('chown -R kafka:kafka /usr/lib/kafka')

        with cd('/usr/lib/kafka'):
            sudo('./sbt update')
            sudo('./sbt package')

        print 'Installed Kafka'
    else:
        print 'Kafka is already installed'

    sudo('mkdir -p /grepdata/kafka')
    sudo('chown -R kafka:kafka /grepdata/kafka')

    sudo('mkdir -p /var/log/kafka')
    sudo('chown -R kafka:kafka /var/log/kafka')

#################################################################################
# KAFKA CODE AND CONFIG SETUP
#################################################################################
def install_kafka_config(org='ntropy'):
    install_kafka_properties(org=org)
    install_service_config()
    install_kafka_daemon()
    install_bashrc(service_type='kafka')
    install_monitoring_config(service='kafka')
    install_etc_hosts(org=org)

def install_kafka_properties(org='ntropy'):
    public_ip = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')
    instance_id = 1

    kInstances = aws.get_instances(service_type='kafka', org=org, state='running')
    for instance in kInstances:
        if (''.join(re.findall(r'\d+', instance.private_ip_address)) ==
            run('python -c "import socket, re; print \'\'.join(re.findall(r\'\d+\', socket.gethostbyname(socket.gethostname())))"')):
            public_ip = instance.public_dns_name
            instance_id = int(''.join(re.findall(r'\d+', instance.id)))

    instances = aws.get_instances(service_type='zookeeper', org=org, state='running')
    zkServers = ','.join(['%s:2181' %x.public_dns_name for x in instances])

    # defaults to localhost
    if not zkServers:
        zkServers = '%s:2181' %public_ip

    zk_code_lines = ["f = open('server.properties').read()",
                     "out = f.replace('REPLACE_WITH_ZOOKEEPER_SERVERS','%s')" %zkServers,
                     "out = out.replace('REPLACE_WITH_EXTERNAL_IP','%s')" %public_ip,
                     "f = open('/usr/lib/kafka/config/server.properties', 'w')",
                     "f.write(out)",
                     "f.close()"]

    bk_code_lines = ["f = open('/usr/lib/kafka/config/server.properties').read()",
                     "out = f.replace('REPLACE_WITH_BROKER_ID','%s')" %instance_id,
                     "f = open('/usr/lib/kafka/config/server.properties', 'w')",
                     "f.write(out)",
                     "f.close()"]

    sudo('wget https://github.com/premal/config/raw/master/kafka/server.properties -O server.properties')
    sudo('python -c "%s"' %'; '.join(zk_code_lines))
    sudo('python -c "%s"' %'; '.join(bk_code_lines))
    sudo('chown kafka:kafka /usr/lib/kafka/config/server.properties')

def install_kafka_daemon():
    sudo('wget https://github.com/premal/config/raw/master/kafka/init.d -O /etc/init.d/kafka')
    sudo('chmod +x /etc/init.d/kafka')

    #sudo('cp /var/ntropy/conf/kafka/kafka-server-stop.sh /usr/lib/kafka/bin/kafka-server-stop.sh')
    #sudo('cp /var/ntropy/conf/kafka/rc.local /etc/init.d/rc.local')

#################################################################################
# KAFKA SERVICES
#################################################################################
# TODO figure out start kafka in background mode
def start_kafka():
    run('nohup sh -c "sudo -u kafka /etc/init.d/kafka start &"')

def stop_kafka():
    run('sudo /etc/init.d/kafka stop')

def restart_kafka():
    stop_kafka()
    start_kafka()

#################################################################################
# STORM SOFTWARE SETUP
#################################################################################
def setup_storm_server(org='ntropy'):
    install_basic_software()
    install_storm_essentials()
    install_java()
    install_zeromq()
    install_jzmq()
    install_user('storm', 'storm')
    install_storm()

def install_storm_essentials():
    sudo('apt-get update')
    sudo('apt-get install -y git unzip build-essential pkg-config libtool autoconf uuid-dev')

def install_zeromq():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/zeromq')

    if result.failed:
        run('wget http://download.zeromq.org/zeromq-2.1.7.tar.gz')
        sudo('mv zeromq-2.1.7.tar.gz /usr/lib/')
        with cd('/usr/lib'):
            sudo('tar xzf zeromq-2.1.7.tar.gz')
            sudo('rm zeromq-2.1.7.tar.gz')
            sudo('ln -s zeromq-2.1.7 zeromq')
        with cd('/usr/lib/zeromq'):
            sudo('./configure')
            sudo('make')
            sudo('make install')
    else:
        print 'ZeroMQ is already installed'

def install_jzmq():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l jzmq/done.log')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/jzmq.tar.gz -O jzmq.tar.gz')
        run('tar xzf jzmq.tar.gz')
        with cd ('jzmq/src'):
            sudo('touch classdist_noinst.stamp')
            sudo('CLASSPATH=.:./.:$CLASSPATH javac -d . org/zeromq/ZMQ.java org/zeromq/ZMQException.java org/zeromq/ZMQQueue.java org/zeromq/ZMQForwarder.java org/zeromq/ZMQStreamer.java')
        with cd ('jzmq'):
            put('/home/premal/dev/ntropy/conf/storm/environment', '/etc/environment', use_sudo=True)
            sudo('./autogen.sh')
            sudo('./configure')
            sudo('make')
            sudo('make install')
            run('touch done.log')
    else:
        print 'JZMQ is already installed'

def install_storm():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/storm')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/storm-0.9.0-wip16.zip -O storm-0.9.0-wip16.zip')
        sudo('mv storm-0.9.0-wip16.zip /usr/lib/')
        with cd('/usr/lib'):
            sudo('unzip storm-0.9.0-wip16.zip')
            sudo('rm storm-0.9.0-wip16.zip')
            sudo('ln -s storm-0.9.0-wip15 storm')
            sudo('chown -R storm:storm /usr/lib/storm/')
            sudo('chown -R storm:storm /usr/lib/storm')
    else:
        print 'Storm is already installed'

    sudo('mkdir -p /grepdata/storm')
    sudo('chown -R storm:storm /grepdata/storm')

#################################################################################
# STORM CODE AND CONFIG SETUP
#################################################################################
def install_storm_code_config(org='ntropy'):
    install_storm_config(org=org)
    install_storm_daemon(org=org)
    install_service_config()
    install_bashrc(service_type='storm')
    install_storm_symlinks()
    install_monitoring_config('storm', 'nimbus')
    install_monitoring_config('storm', 'ui')
    install_monitoring_config('storm', 'supervisor')
    install_etc_hosts(org=org)

def install_storm_config(org='ntropy'):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('wget https://github.com/premal/config/raw/master/storm/storm.yaml -O storm.yaml')

    instances = aws.get_instances(service_type='zookeeper', org=org, state='running')
    zkServers = '\n     - '.join(['\\\\"%s\\\\"' %x.public_dns_name for x in instances])

    # default to localhost
    if not instances:
        zkServers = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    try:
        public_dns_name = aws.get_instances(service_type='storm', org=org, state='running', master=True)[0].public_dns_name
    except IndexError:
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('storm.yaml').read()",
                  "out = f.replace('REPLACE_WITH_ZOOKEEPER_SERVERS', '''%s''')" %zkServers,
                  "out = out.replace('REPLACE_WITH_NIMBUS_SERVER', '%s')" %public_dns_name,
                  "f = open('/usr/lib/storm/conf/storm.yaml', 'w')",
                  "f.write(out)",
                  "f.close()"]
    
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('python -c "%s"' %'; '.join(code_lines), user='storm')

def install_storm_daemon(org='ntropy'):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('wget https://github.com/premal/config/raw/master/storm/init.d -O /etc/init.d/storm')
        sudo('chmod +x /etc/init.d/storm')

def install_storm_symlinks():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('ln -s /usr/lib/storm/logs/ /var/log/storm')
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('ln -s /usr/lib/storm/conf /etc/storm-conf')

#################################################################################
# STORM SERVICES
#################################################################################
def start_storm_master():
    start_storm_nimbus()
    start_storm_ui()

def stop_storm_master():
    stop_storm_nimbus()
    stop_storm_ui()

def restart_storm_master():
    stop_storm_master()
    start_storm_master()

def start_storm_nimbus():
    run('nohup sh -c "sudo -u storm /etc/init.d/storm nimbus start &"')

def stop_storm_nimbus():
    run('sudo -u storm /etc/init.d/storm nimbus stop')

def restart_storm_nimbus():
    stop_storm_nimbus()
    start_storm_nimbus()

def start_storm_ui():
    run('nohup sh -c "sudo -u storm /etc/init.d/storm ui start &"')

def stop_storm_ui():
    run('sudo -u storm /etc/init.d/storm ui stop')

def restart_storm_ui():
    stop_storm_ui()
    start_storm_ui()

def start_storm_supervisor():
    run('nohup sh -c "sudo -u storm /etc/init.d/storm supervisor start &"')

def stop_storm_supervisor():
    run('sudo -u storm /etc/init.d/storm supervisor stop')

def restart_storm_supervisor():
    stop_storm_supervisor()
    start_storm_supervisor()

#################################################################################
# STORM LOGS
#################################################################################
def delete_storm_logs():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        sudo('rm /usr/lib/storm/logs/*.log.?')

#################################################################################
# HBASE SOFTWARE SETUP
#################################################################################
def setup_hbase_server(org='ntropy'):
    install_basic_software()
    install_java()
    install_user('hbase', 'hbase')
    install_passwordless_ssh('hbase')
    install_hbase()
    install_hbase_symlinks()
    install_lzo()

def install_passwordless_ssh(username):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = sudo('ls -l /home/%s/.ssh/id_rsa' %username)

    if result.failed:
        run('sudo -u %s ssh-keygen -t rsa -P "" -f /home/%s/.ssh/id_rsa' %(username, username))
        run('sudo -u %s cp /home/%s/.ssh/id_rsa.pub /home/%s/.ssh/authorized_keys' %(
            username, username, username))

def install_hbase():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hbase')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/hbase-0.94.4.tar.gz -O hbase-0.94.4.tar.gz')
        sudo('mv hbase-0.94.4.tar.gz /usr/lib/')
        with cd('/usr/lib'):
            sudo('tar xzf hbase-0.94.4.tar.gz')
            sudo('rm hbase-0.94.4.tar.gz')
            sudo('ln -s hbase-0.94.4 hbase')
            sudo('chown -R hbase:hbase hbase/')
            sudo('chown -R hbase:hbase hbase')
    else:
        print 'HBase is already installed'

    sudo('mkdir -p /grepdata/hbase')
    sudo('mkdir -p /grepdata/hbase/tmp')
    sudo('mkdir -p /grepdata/hbase/local')
    sudo('chown -R hbase:hbase /grepdata/hbase')

def install_hbase_symlinks():
    sudo('ln -s /usr/lib/hbase/logs /var/log/hbase')

def install_lzo():
    sudo('apt-get -y install liblzo2-dev')

    with cd('/usr/lib/hadoop/lib/native/Linux-amd64-64'):
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.a -O libgplcompression.a', user='hadoop')
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.la -O libgplcompression.la', user='hadoop')
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.so.0.0.0 -O libgplcompression.so.0.0.0', user='hadoop')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hadoop/lib/native/Linux-amd64-64/libgplcompression.so')
    if result.failed:
        with cd('/usr/lib/hadoop/lib/native/Linux-amd64-64'):
            sudo('ln -s libgplcompression.so.0.0.0 libgplcompression.so')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hadoop/lib/native/Linux-amd64-64/libgplcompression.so.0')
    if result.failed:
        with cd('/usr/lib/hadoop/lib/native/Linux-amd64-64'):
            sudo('ln -s libgplcompression.so.0.0.0 libgplcompression.so.0', user='hadoop')

    with cd('/usr/lib/hadoop/lib/'):
        sudo('wget https://s3.amazonaws.com/bootstrap-software/hadoop-lzo-0.4.15.jar -O hadoop-lzo-0.4.15.jar', user='hadoop')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hbase/lib/native/Linux-amd64-64')
    if result.failed:
        sudo('mkdir /usr/lib/hbase/lib/native/Linux-amd64-64', user='hbase')

    with cd('/usr/lib/hbase/lib/native/Linux-amd64-64/'):
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.a -O libgplcompression.a', user='hbase')
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.la -O libgplcompression.la', user='hbase')
        sudo('wget https://s3.amazonaws.com/bootstrap-software/libgplcompression.so.0.0.0 -O libgplcompression.so.0.0.0', user='hbase')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hbase/lib/native/Linux-amd64-64/libgplcompression.so')
    if result.failed:
        with cd('/usr/lib/hbase/lib/native/Linux-amd64-64/'):
            sudo('ln -s libgplcompression.so.0.0.0 libgplcompression.so', user='hbase')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hbase/lib/native/Linux-amd64-64/libgplcompression.so.0')
    if result.failed:
        with cd('/usr/lib/hbase/lib/native/Linux-amd64-64/'):
            sudo('ln -s libgplcompression.so.0.0.0 libgplcompression.so.0', user='hbase')

    with cd('/usr/lib/hbase/lib/'):
        sudo('wget https://s3.amazonaws.com/bootstrap-software/hadoop-lzo-0.4.15.jar -O hadoop-lzo-0.4.15.jar', user='hbase')

#################################################################################
# HADOOP SOFTWARE SETUP
#################################################################################
def setup_hadoop_server(org='ntropy'):
    install_basic_software()
    install_java()
    install_user('hadoop', 'hadoop')
    install_passwordless_ssh('hadoop')
    install_hadoop()
    install_hdfs_dirs()

def install_hadoop():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('ls -l /usr/lib/hadoop')

    if result.failed:
        run('wget https://s3.amazonaws.com/bootstrap-software/hadoop-1.0.4-bin.tar.gz -O hadoop-1.0.4-bin.tar.gz')
        sudo('mv hadoop-1.0.4-bin.tar.gz /usr/lib/')
        with cd('/usr/lib'):
            sudo('tar xzf hadoop-1.0.4-bin.tar.gz')
            sudo('rm hadoop-1.0.4-bin.tar.gz')
            sudo('ln -s hadoop-1.0.4 hadoop')
            sudo('chown -R hadoop:hadoop hadoop/')
            sudo('chown -R hadoop:hadoop hadoop')
    else:
        print 'Hadoop is already installed'
        
def install_hdfs_dirs():
    sudo('mkdir -p /grepdata/hadoop/name')
    sudo('chown -R hadoop:hadoop /grepdata/hadoop/')

    sudo('mkdir -p /hdfs/volume1')
    sudo('mkdir -p /hdfs/volume1/data')
    sudo('mkdir -p /hdfs/volume1/name')
    sudo('chown -R hadoop:hadoop /hdfs/')

#################################################################################
# HBASE CODE AND CONFIG SETUP
#################################################################################
def install_hbase_config(org='ntropy'):
    install_hdfs_dirs()
    install_hbase_env(org=org)
    install_hbase_site(org=org)
    install_hbase_regionservers(org=org)
    install_security_limits('hbase', org=org)
    install_bashrc(service_type='hbase')
    install_etc_hosts(org=org)
    install_hbase_daemon()
    install_monitoring_config('hbase', 'master')
    install_monitoring_config('hbase', 'regionserver')

def install_hbase_env(org='ntropy'):
    sudo('wget https://github.com/premal/config/raw/master/hbase/hbase-env.sh -O /usr/lib/hbase/conf/hbase-env.sh')

def install_hbase_site(org='ntropy'):
    run('wget https://github.com/premal/config/raw/master/hbase/hbase-site.xml -O hbase-site.xml')

    try:
        public_dns_name = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0].public_dns_name
        instances = aws.get_instances(service_type='zookeeper', org=org, state='running')
        zkServers = ','.join(["%s" %x.public_dns_name for x in instances])
    except IndexError:
        # defaults to localhost
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')
        zkServers = public_dns_name

    code_lines = ["f = open('hbase-site.xml').read()",
                  "out = f.replace('REPLACE_WITH_NAMENODE', '%s')" %public_dns_name,
                  "out = out.replace('REPLACE_WITH_ZOOKEEPER_SERVERS', '%s')" %zkServers,
                  "f = open('/usr/lib/hbase/conf/hbase-site.xml', 'w')",
                  "f.write(out)",
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hbase')

def install_hbase_regionservers(org='ntropy'):
    instances = aws.get_instances(service_type='hbase', org=org, state='running', slave=True)
    regionservers = '\n'.join([x.public_dns_name for x in instances])

    if not regionservers:
        # default to localhost
        regionservers = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')
    
    code_lines = ["f = open('/usr/lib/hbase/conf/regionservers', 'w')",
                  "f.write('''%s''')" %regionservers,
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hbase')

def install_hbase_metrics(org='ntropy'):
    run('wget https://github.com/premal/config/raw/master/hbase/hadoop-metrics.properties -O hadoop-metrics.properties')

    try:
        public_dns_name = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0].public_dns_name
    except IndexError:
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('hadoop-metrics.properties').read()",
                  "out = f.replace('REPLACE_WITH_GANGLIA_MASTER', '%s')" %public_dns_name,
                  "f = open('/usr/lib/hbase/conf/hadoop-metrics.properties', 'w')",
                  "f.write(out)",
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hbase')

def install_hbase_daemon():
    sudo('wget https://github.com/premal/config/raw/master/hbase/hbase-daemon.sh -O /usr/lib/hbase/bin/hbase-daemon.sh', user='hbase')

########################## HDFS ##########################
def install_hadoop_config(org='ntropy'):
    install_hadoop_env(org=org)
    install_hdfs_site(org=org)
    install_core_site(org=org)
    install_hdfs_master(org=org)
    install_hdfs_slaves(org=org)
    install_hadoop_metrics(org=org)
    install_hadoop_daemon()
    install_hadoop_symlinks()
    install_monitoring_config('hadoop', 'namenode')
    install_monitoring_config('hadoop', 'datanode')

def install_hadoop_env(org='ntropy'):
    sudo('wget https://github.com/premal/config/raw/master/hadoop/hadoop-env.sh -O /usr/lib/hadoop/conf/hadoop-env.sh', user='hadoop')

def install_hdfs_site(org='ntropy'):
    sudo('wget https://github.com/premal/config/raw/master/hadoop/hdfs-site.xml -O /usr/lib/hadoop/conf/hdfs-site.xml', user='hadoop')

def install_core_site(org='ntropy'):
    run('wget https://github.com/premal/config/raw/master/hadoop/core-site.xml -O core-site.xml')

    try:
        public_dns_name = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0].public_dns_name
    except IndexError:
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('core-site.xml').read()",
                  "out = f.replace('REPLACE_WITH_NAMENODE', '%s')" %public_dns_name,
                  "f = open('/usr/lib/hadoop/conf/core-site.xml', 'w')",
                  "f.write(out)",
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hadoop')

def install_hdfs_master(org='ntropy'):
    try:
        public_dns_name = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0].public_dns_name
    except IndexError:
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('/usr/lib/hadoop/conf/master', 'w')",
                  "f.write('%s')" %public_dns_name,
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hadoop')

def install_hdfs_slaves(org='ntropy'):
    instances = aws.get_instances(service_type='hbase', org=org, state='running', slave=True)
    datanodes = '\n'.join([x.public_dns_name for x in instances])

    if not datanodes:
        datanodes = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('/usr/lib/hadoop/conf/slaves', 'w')",
                  "f.write('''%s''')" %datanodes,
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hadoop')

def install_hadoop_metrics(org='ntropy'):
    run('wget https://github.com/premal/config/raw/master/hadoop/hadoop-metrics2.properties -O hadoop-metrics2.properties')

    try:
        public_dns_name = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0].public_dns_name
    except IndexError:
        public_dns_name = run('python -c "import socket, re; print socket.gethostbyname(socket.gethostname())"')

    code_lines = ["f = open('hadoop-metrics2.properties').read()",
                  "out = f.replace('REPLACE_WITH_GANGLIA_MASTER', '%s')" %public_dns_name,
                  "f = open('/usr/lib/hadoop/conf/hadoop-metrics2.properties', 'w')",
                  "f.write(out)",
                  "f.close()"]
    sudo('python -c "%s"' %'; '.join(code_lines), user='hadoop')

def install_hadoop_daemon():
    sudo('wget https://github.com/premal/config/raw/master/hadoop/hadoop-daemon.sh -O /usr/lib/hadoop/bin/hadoop-daemon.sh', user='hadoop')

def install_hadoop_symlinks():
    sudo('ln -s /usr/lib/hadoop/logs /var/log/hadoop')

#################################################################################
# HBASE SERVICES
#################################################################################
def start_hbase(org='ntropy'):
    env.hosts = get_hosts(org=org, service_type='hbase', state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __start_hbase()

def __start_hbase(org='ntropy'):
    with cd('/usr/lib/hbase'):
        run('sudo -u hbase bin/start-hbase.sh')

def stop_hbase(org='ntropy'):
    env.hosts = get_hosts(org=org, service_type='hbase', state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __stop_hbase()

def __stop_hbase():
    with cd('/usr/lib/hbase'):
        run('sudo -u hbase bin/stop-hbase.sh')

def restart_hbase(org='ntropy'):
    env.hosts = get_hosts(org=org, service_type='hbase', state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __restart_hbase()

def __restart_hbase(org='ntropy'):
    __stop_hbase()
    __start_hbase()

def start_regionserver():
    with cd('/usr/lib/hbase'):
        run('sudo -u hbase bin/hbase-daemon.sh start regionserver')

def stop_regionserver():
    with cd('/usr/lib/hbase'):
        run('sudo -u hbase bin/hbase-daemon.sh stop regionserver')

def restart_regionserver():
    stop_regionserver()
    start_regionserver()

def kill_hbase(org="ntropy"):
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        run('sudo pkill -f hbase')

#################################################################################
# HBASE HDFS SERVICES
#################################################################################
def format_namenode(service_type, org='ntropy'):
    env.hosts = get_hosts(org=org, service_type=service_type, state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __format_namenode()

def __format_namenode():
    with cd('/usr/lib/hadoop'):
        run('echo Y | sudo -u hadoop bin/hadoop namenode -format')

def start_namenode(service_type, org='ntropy'):
    env.hosts = get_hosts(org=org, service_type=service_type, state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __start_namenode()

def __start_namenode():
    with cd('/usr/lib/hadoop'):
        run('sudo -u hadoop bin/start-dfs.sh')

    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('/usr/lib/hadoop/bin/hadoop fs -ls /hbase')

    if result.failed:
        run('sudo -u hadoop /usr/lib/hadoop/bin/hadoop fs -mkdir /hbase')
        run('sudo -u hadoop /usr/lib/hadoop/bin/hadoop fs -chown -R hbase:hbase /hbase')

def stop_namenode(service_type, org='ntropy'):
    env.hosts = get_hosts(org=org, service_type=service_type, state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __stop_namenode()

def __stop_namenode():
    with cd('/usr/lib/hadoop'):
        run('sudo -u hadoop bin/stop-dfs.sh')

def restart_namenode(service_type, org='ntropy'):
    env.hosts = get_hosts(org=org, service_type=service_type, state='running', master=True)
    for host in env.hosts:
        with(settings(host_string=host)):
            __restart_namenode()

def __restart_namenode():
    with cd('/usr/lib/hadoop'):
        __stop_namenode()
        __start_namenode()

def start_datanode(org='ntropy'):
    with cd('/usr/lib/hadoop'):
        run('sudo -u hadoop bin/hadoop-daemon.sh start datanode')

def stop_datanode(org='ntropy'):
    with cd('/usr/lib/hadoop'):
        run('sudo -u hadoop bin/hadoop-daemon.sh stop datanode')

def restart_datanode(org='ntropy'):
    stop_datanode(org=org)
    start_datanode(org=org)

#################################################################################
# CREATE SERVERS
#################################################################################
def create_mysql_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    aws.create_new_instances('mysql', org=org, instance_type=instance_type)

def create_zookeeper_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)
    before_instances = aws.get_instances(service_type='zookeeper', org=org, state='running')
    aws.create_new_instances('zookeeper', instance_type, org=org, num_instances=num_instances)
    print 'Waiting 60 seconds for aws to initialize the instances'
    time.sleep(60)
    after_instances = aws.get_instances(service_type='zookeeper', org=org, state='running')

    for host in [x.public_dns_name for x in after_instances]:
        with settings(host_string=host):
            install_zookeeper_config(org=org, branch=branch)

    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            start_zookeeper()

def create_kafka_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)
    before_instances = aws.get_instances(service_type='kafka', org=org, state='running')
    aws.create_new_instances('kafka', instance_type, org=org, num_instances=num_instances)
    print 'Waiting 60 seconds for aws to initialize the instances'
    time.sleep(60)
    after_instances = aws.get_instances(service_type='kafka', org=org, state='running')
    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            install_kafka_config(org=org, branch=branch)
            start_kafka()
        aws.add_instances_to_loadbalancer(service_type='kafka', instances=[instance], org='ntropy')

def create_beacon_web_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)
    before_instances = aws.get_instances(service_type='beacon-web', org=org, state='running')
    aws.create_new_instances('beacon-web', instance_type, org=org, num_instances=num_instances)
    print 'Waiting 120 seconds for aws to initialize the instances'
    time.sleep(120)
    after_instances = aws.get_instances(service_type='beacon-web', org=org, state='running')
    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            install_beacon_web_code_config(org=org, branch=branch)
            restart_beacon_web()
        #aws.add_instances_to_loadbalancer(service_type='beacon-web', instances=[instance], org='ntropy')

"""
def create_frontend_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)
    before_instances = aws.get_instances(service_type='frontend', org=org, state='running')
    aws.create_new_instances('frontend', instance_type, org=org, num_instances=num_instances)
    print 'Waiting 120 seconds for aws to initialize the instances'
    time.sleep(120)
    after_instances = aws.get_instances(service_type='frontend', org=org, state='running')
    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            install_beacon_web_code_config(org=org, branch=branch)
            restart_beacon_web()
        aws.add_instances_to_loadbalancer(service_type='frontend', instances=[instance], org='ntropy')
"""

def create_storm_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)

    before_instances = aws.get_instances(service_type='storm', org=org, state='running')
    aws.create_new_instances('storm', instance_type, org=org, num_instances=num_instances)

    print 'Waiting 120 seconds for aws to initialize the instances'
    time.sleep(120)

    after_instances = aws.get_instances(service_type='storm', org=org, state='running')

    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            install_storm_code_config(org=org, branch=branch)
            if instance.tags.get('Name2').endswith('master'):
                start_storm_master()
            elif instance.tags.get('Name2').endswith('slave'):
                start_storm_worker()

def create_hbase_servers(org='ntropy', num_instances=1, instance_type='t1.micro', branch='master'):
    num_instances = int(num_instances)

    before_instances = aws.get_instances(service_type='hbase', org=org, state='running')
    aws.create_new_instances('hbase', instance_type, org=org, num_instances=num_instances)

    print 'Waiting 120 seconds for aws to initialize the instances'
    time.sleep(120)

    after_instances = aws.get_instances(service_type='hbase', org=org, state='running')

    instance_volumes = []
    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue
        with settings(host_string=instance.public_dns_name):
            install_hbase_hdfs_config(org=org, branch=branch)

    print before_instances
    print after_instances

    # master starts datanodes and regionservers.
    # so when slaves are getting initialized with the master,
    # then don't need to start the slave processes separately
    master_started = False
    for instance in after_instances:
        if instance.id in [x.id for x in before_instances]:
            continue

        if instance.tags.get('Name2').endswith('master'):
            with settings(host_string=instance.public_dns_name):
                __format_namenode()
                __start_namenode()
                __start_hbase()
                master_started = True

        elif instance.tags.get('Name2').endswith('slave'):
            if master_started:
                continue
            with settings(host_string=instance.public_dns_name):
                pass
                start_datanode()
                start_regionserver()

#################################################################################
# CREATE CLUSTER
#################################################################################
def create_cluster(org='ntropy', branch='master',
                   num_mysql=1, mysql_instance_type='t1.micro',
                   num_zookeeper=1, zookeeper_instance_type='t1.micro',
                   num_kafka=1, kafka_instance_type='t1.micro',
                   num_beacon_web=1, beacon_web_instance_type='t1.micro',
                   num_storm=1, storm_instance_type='t1.micro',
                   num_hbase=1, hbase_instance_type='t1.micro',
                   num_frontend=1, frontend_instance_type='t1.micro',
                   num_api=1, api_instance_type='t1.micro'):

    create_mysql_servers(org=org, num_instances=num_mysql, instance_type=mysql_instance_type, branch=branch)
    create_zookeeper_servers(org=org, num_instances=num_zookeeper, instance_type=mysql_instance_type, branch=branch)
    create_kafka_servers(org=org, num_instances=num_kafka, instance_type=mysql_instance_type, branch=branch)
    create_beacon_web_servers(org=org, num_instances=num_beacon_web, instance_type=mysql_instance_type, branch=branch)
    #create_frontend_servers(org=org, num_instances=num_frontend, instance_type=frontend_instance_type, branch=branch)
    #create_api_servers(org=org, num_instances=num_api, instance_type=api_instance_type, branch=branch)
    create_storm_servers(org=org, num_instances=num_storm, instance_type=mysql_instance_type, branch=branch)
    create_hbase_servers(org=org, num_instances=num_hbase, instance_type=mysql_instance_type, branch=branch)

#################################################################################
# GANGLIA SOFTWARE
#################################################################################
def install_ganglia_dependencies():
    sudo('apt-get -y install build-essential libapr1-dev libconfuse-dev libexpat1-dev python-dev')

def install_ganglia_master():
    install_ganglia_dependencies()
    sudo('apt-get -y install ganglia-monitor ganglia-webfrontend gmetad')
    install_ganglia_rrd_dir()

def install_ganglia_slave():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        print 'Installing ganglia'
        install_ganglia_dependencies()
        sudo('apt-get -y install ganglia-monitor')
        install_ganglia_rrd_dir()

def install_ganglia_rrd_dir():
    sudo('mkdir -p /var/lib/ganglia/rrds')
    sudo('chown -R ganglia:ganglia /var/lib/ganglia/')

#################################################################################
# GANGLIA CONFIG
#################################################################################
def install_ganglia_master_gmetad_config(service_type, org='ntropy', branch='develop', checkout=True):
    if checkout:
        install_code()
        checkout_branch(branch)

    sudo('cp /var/ntropy/conf/ganglia/%s-gmetad-conf /etc/ganglia/gmetad.conf' %service_type)

def install_ganglia_master_gmond_config(service_type, org='ntropy', branch='develop', checkout=True):
    if checkout:
        install_code()
        checkout_branch(branch)

    sudo('cp /var/ntropy/conf/ganglia/%s-master-gmond.conf /etc/ganglia/gmond.conf' %service_type)

def install_ganglia_slave_gmond_config(service_type, org='ntropy', branch='develop', checkout=True):
    if checkout:
        install_code()
        checkout_branch(branch)

    master = aws.get_instances(service_type='hbase', org=org, state='running', master=True)[0]
    hInstances = aws.get_instances(service_type='hbase', org=org, state='running', slave=True)
    for instance in hInstances:
        if (''.join(re.findall(r'\d+', instance.private_ip_address)) ==
            run('python -c "import socket, re; print \'\'.join(re.findall(r\'\d+\', socket.gethostbyname(socket.gethostname())))"')):
            code_lines = ["f = open('%s-slave-gmond.conf').read()" %service_type,
                          "out = f.replace('REPLACE_WITH_SLAVE_LOCATION', '%s')" %''.join(re.findall(r'\d+', instance.ip_address)),
                          "out = out.replace('REPLACE_WITH_MASTER', '%s')" %master.public_dns_name,
                          "f = open('/etc/ganglia/gmond.conf', 'w')",
                          "f.write(out)",
                          "f.close()"
            ]

            with cd('/var/ntropy/conf/ganglia'):
                run('sudo python -c "%s"' %'; '.join(code_lines))

#################################################################################
# GANGLIA SERVICE
#################################################################################
def start_ganglia_master():
    sudo('/etc/init.d/gmetad start')
    sudo('/etc/init.d/ganglia-monitor start')

def start_ganglia_slave():
    sudo('/etc/init.d/ganglia-monitor start')

def stop_ganglia_master():
    sudo('/etc/init.d/gmetad stop')
    sudo('/etc/init.d/ganglia-monitor stop')

def stop_ganglia_slave():
    sudo('/etc/init.d/ganglia-monitor stop')

def restart_ganglia_master():
    start_ganglia_master()
    start_ganglia_slave()

def restart_ganglia_slave():
    stop_ganglia_master()
    stop_ganglia_slave()

#################################################################################
# GANGLIA DISK STATS
#################################################################################
def install_ganglia_disk_stats():
    sudo('mkdir -p /usr/lib/ganglia/python_modules')
    with cd('/usr/lib/ganglia/python_modules'):
        sudo('wget https://raw.github.com/ganglia/gmond_python_modules/master/diskstat/python_modules/diskstat.py -O diskstat.py')

def run_ganglia_disk_stats():
    sudo ('nohup sh -c "python /usr/lib/ganglia/python_modules/diskstat.py -g &"')


