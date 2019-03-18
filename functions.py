# -*- coding: utf-8 -*-

import os
import sys
import json
import re
from kubernetes import config
import logging
import psycopg2
import logging.handlers
import argparse
import yaml


logger = logging.getLogger()


class K8sLoggingFilter(logging.Filter):
    '''
    A small filter to add add extra logging data if not present
    '''
    def filter(self, record):
        if not hasattr(record, 'resource_name'):
            record.resource_name = '-'
        return True


def create_logger(log_level):
    '''
    Creates logging object
    '''
    json_format = logging.Formatter('{"time":"%(asctime)s", "level":"%(levelname)s", "resource_name":"%(resource_name)s", "message":"%(message)s"}')
    filter = K8sLoggingFilter()
    logger = logging.getLogger()
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(json_format)
    logger.addHandler(stdout_handler)
    logger.addFilter(filter)

    if log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif log_level == 'info':
        logger.setLevel(logging.INFO)
    else:
        raise Exception('Unsupported log_level {0}'.format(log_level))

    return logger


class PostgresControllerConfig(object):
    '''
    Manages run time configuration
    '''
    def __init__(self):
        if 'KUBERNETES_PORT' in os.environ:
            config.load_incluster_config()
        else:
            config.load_kube_config()

        parser = argparse.ArgumentParser(description='A simple k8s controller to create PostgresSQL databases.')
        parser.add_argument('-c', '--config-file', help='Path to config file.', default=os.environ.get('CONFIG_FILE', None))
        parser.add_argument('-l', '--log-level', help='Log level.', choices=['info', 'debug'], default=os.environ.get('LOG_LEVEL', 'info'))
        self.args = parser.parse_args()

        if not self.args.config_file:
            parser.print_usage()
            sys.exit()

        with open(self.args.config_file) as fp:
            self.yaml_config = yaml.safe_load(fp)
            if 'postgres_instances' not in self.yaml_config or len(self.yaml_config['postgres_instances'].keys()) < 1:
                raise Exception('No postgres instances in configuration')

    def get_credentials(self, instance_id):
        '''
        Returns the correct instance credentials from current list in configuration
        '''
        creds = None

        if instance_id == None:
            instance_id = 'default'

        for id, data in self.yaml_config['postgres_instances'].items():
            if id == instance_id:
                creds = data.copy()
                if 'dbname' not in creds:
                    creds['dbname'] = 'postgres'
                break

        return creds


def parse_too_old_failure(message):
    '''
    Parse an error from watch API when resource version is too old
    '''
    regex = r"too old resource version: .* \((.*)\)"

    result = re.search(regex, message)
    if result == None:
        return None

    match = result.group(1)
    if match == None:
        return None

    try:
        return int(match)
    except:
        return None


def create_db_if_not_exists(cur, db_name):
    '''
    A function to create a database if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_database WHERE datname = '{}';".format(db_name))
    if not cur.fetchone():
        cur.execute("CREATE DATABASE {};".format(db_name))
        return True
    else:
        return False


def create_role_not_exists(cur, role_name, role_password):
    '''
    A function to create a role if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = '{}';".format(role_name))
    if not cur.fetchone():
        cur.execute("CREATE ROLE {0} PASSWORD '{1}' LOGIN;".format(role_name, role_password))
        return True
    else:
        return False


def process_event(crds, obj, event_type, runtime_config):
    '''
    Processes events in order to create or drop databases
    '''
    spec = obj.get('spec')
    metadata = obj.get('metadata')
    k8s_resource_name = metadata.get('name')

    logger = logging.LoggerAdapter(logging.getLogger(), {'resource_name': k8s_resource_name})

    logger.debug('Processing event {0}: {1}'.format(event_type, json.dumps(obj, indent=1)))

    if event_type == 'MODIFIED':
        logger.debug('Ignoring modification for DB {0}, not supported'.format(spec['dbName']))
        return

    db_credentials = runtime_config.get_credentials(instance_id=spec.get('dbInstanceId'))

    if db_credentials == None:
        logger.error('No corresponding postgres instance in configuration for instance id {0}'.format(spec.get('dbInstanceId')))
        return

    try:
        conn = psycopg2.connect(**db_credentials)
        cur = conn.cursor()
        conn.set_session(autocommit=True)
    except Exception as e:
        logger.error('Error when connecting to DB instance {0}: {1}'.format(spec.get('dbInstanceId'), e))
        return


    if event_type == 'DELETED':
        try:
            drop_db = spec['onDeletion']['dropDB']
        except KeyError:
            drop_db = False

        if drop_db == True:
            try:
                cur.execute("DROP DATABASE {0};".format(spec['dbName']))
            except psycopg2.OperationalError as e:
                logger.error('Dropping of dbName {0} failed: {1}'.format(spec['dbName'], e))
            else:
                logger.info('Dropped dbName {0}'.format(spec['dbName']))
        else:
            logger.info('Ignoring deletion for dbName {0}, onDeletion setting not enabled'.format(spec['dbName']))

        try:
            drop_role = spec['onDeletion']['dropRole']
        except KeyError:
            drop_role = False

        if drop_role == True:
            try:
                cur.execute("DROP ROLE {0};".format(spec['dbRoleName']))
            except Exception as e:
                logger.error('Error when dropping role {0}: {1}'.format(spec['dbRoleName'], e))
            else:
                logger.info('Dropped role {0}'.format(spec['dbRoleName']))
        else:
            logger.info('Ignoring deletion of role {0}, onDeletion setting not enabled'.format(spec['dbRoleName']))

        logger.info('Deleted')


    elif event_type == 'ADDED':
        logger.info('Adding dbName {0}'.format(spec['dbName']))

        db_created = create_db_if_not_exists(cur, spec['dbName'])
        if db_created:
            logger.info('Database {0} created'.format(spec['dbName']))
        else:
            logger.info('Database {0} already exists'.format(spec['dbName']))

        role_created = create_role_not_exists(cur, spec['dbRoleName'], spec['dbRolePassword'])
        if role_created:
            logger.info('Role {0} created'.format(spec['dbRoleName']))
        else:
            logger.info('Role {0} already exists'.format(spec['dbRoleName']))

        cur.execute("GRANT ALL PRIVILEGES ON DATABASE {0} to {1};".format(spec['dbName'], spec['dbRoleName']))

        if ('dbExtensions' in spec or 'extraSQL' in spec) and not db_created:
            logger.info('Ingoring extra SQL commands dbName {0} as it is already created'.format(spec['dbName']))

        elif ('dbExtensions' in spec or 'extraSQL' in spec) and db_created:
            user_credentials = {
                **db_credentials,
                **{
                    'dbname': spec['dbName'],
                    'user': spec['dbRoleName'],
                    'password':  spec['dbRolePassword'],
                }
            }

            admin_credentials = {
                **db_credentials,
                **{
                    'dbname': spec['dbName']
                },
            }

            if 'dbExtensions' in spec:
                db_conn = psycopg2.connect(**admin_credentials)
                db_cur = db_conn.cursor()
                db_conn.set_session(autocommit=True)
                for ext in spec['dbExtensions']:
                    logger.info('Creating extension {0} in dbName {1}'.format(ext, spec['dbName']))
                    db_cur.execute('CREATE EXTENSION IF NOT EXISTS "{0}";'.format(ext))

            if 'extraSQL' in spec:
                db_conn = psycopg2.connect(**user_credentials)
                db_cur = db_conn.cursor()
                db_conn.set_session(autocommit=False)
                logger.info('Running extra SQL commands for in dbName {0}'.format(spec['dbName']))
                try:
                    db_cur.execute(spec['extraSQL'])
                    db_conn.commit()
                except psycopg2.OperationalError as e:
                    logger.error('OperationalError when running extraSQL for dbName {0}: {1}'.format(spec['dbName'], e))
                except psycopg2.ProgrammingError as e:
                    logger.error('ProgrammingError when running extraSQL for dbName {0}: {1}'.format(spec['dbName'], e))

            db_cur.close()

        logger.info('Added PostgresDatabase dbName {0}'.format(spec['dbName']))

    cur.close()
