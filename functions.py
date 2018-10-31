# -*- coding: utf-8 -*-

import os
import sys
import json
from kubernetes import config
import logging
import psycopg2
import logging.handlers
import argparse
import yaml


logger = logging.getLogger()


def create_logger(log_level):
    '''
    Creates logging object
    '''
    json_format = logging.Formatter('{"time":"%(asctime)s", "level":"%(levelname)s", "message":"%(message)s"}')
    logger = logging.getLogger()
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(json_format)
    logger.addHandler(stdout_handler)

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
            self.yaml_config = yaml.load(fp)
            if 'postgres_instances' not in self.yaml_config or len(self.yaml_config['postgres_instances'].keys()) < 1:
                raise Exception('No postgres instances in configuration')

    def get_credentials(self, instance_id):
        '''
        Returns the correct instance credentials from current list in configuration
        '''
        creds = None

        if not instance_id:
            instance_id = 'default'

        for id, data in self.yaml_config['postgres_instances'].items():
            if id == instance_id:
                creds = data.copy()
                if 'dbname' not in creds:
                    creds['dbname'] = 'postgres'
                break

        return creds


def create_db_if_not_exists(cur, db_name):
    '''
    A function to create a database if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_database WHERE datname = '{}';".format(db_name))
    if not cur.fetchone():
        cur.execute("CREATE DATABASE {};".format(db_name))
        logger.info('Database {0} created'.format(db_name))
        return True
    else:
        logger.info('Database {0} already exists'.format(db_name))
        return False


def create_role_not_exists(cur, role_name, role_password):
    '''
    A function to create a role if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = '{}';".format(role_name))
    if not cur.fetchone():
        cur.execute("CREATE ROLE {0} PASSWORD '{1}' LOGIN;".format(role_name, role_password))
        logger.info('Role {0} created'.format(role_name))
        return True
    else:
        logger.info('Role {0} already exists'.format(role_name))
        return False


def process_event(crds, obj, event_type, runtime_config):
    '''
    Processes events in order to create or drop databases
    '''
    spec = obj.get('spec')
    metadata = obj.get('metadata')
    k8s_resource_name = metadata.get('name')


    logger.debug('Processing event: {0}'.format(json.dumps(obj, indent=1)))

    if event_type == 'MODIFIED':
        logger.debug('Ignoring modification for {0} DB {1}, not supported'.format(k8s_resource_name, spec['dbName']))
        return

    db_credentials = runtime_config.get_credentials(instance_id=spec.get('dbInstanceId'))

    if not db_credentials:
        logger.error('No corresponding postgres instance in configuration for {0}, instance id {1}'.format(k8s_resource_name, spec.get('dbInstanceId')))
        return

    conn = psycopg2.connect(**db_credentials)
    cur = conn.cursor()
    conn.set_session(autocommit=True)


    if event_type == 'DELETED':
        logger.info('Deleting PostgresDatabase {0}, dbName {1}'.format(k8s_resource_name, spec['dbName']))
        try:
            drop_db = spec['onDeletion']['dropDB']
        except KeyError:
            drop_db = False
        if drop_db:
            logger.info('Dropping {0} DB {1}'.format(k8s_resource_name, spec['dbName']))
            try:
                cur.execute("DROP DATABASE {0};".format(spec['dbName']))
            except psycopg2.OperationalError as e:
                logger.error('Dropping of {0} DB {1} failed {2}'.format(k8s_resource_name, spec['dbName'], e))
        else:
            logger.info('Ignoring deletion for {0} database {1}, onDeletion setting not enabled'.format(k8s_resource_name, spec['dbName']))

        try:
            drop_role = spec['onDeletion']['dropRole']
        except KeyError:
            drop_role = False
        if drop_role:
            try:
                cur.execute("DROP ROLE {0};".format(spec['dbRoleName']))
            except Exception as e:
                logger.error('Error when dropping role {0}: {1}'.format(spec['dbRoleName'], e))
            else:
                logger.info('Dropped role {0}'.format(spec['dbRoleName']))
        else:
            logger.info('Ignoring deletion for {0} role {1}, onDeletion setting not enabled'.format(k8s_resource_name, spec['dbName']))


    elif event_type == 'ADDED':
        logger.info('Adding PostgresDatabase {0}, dbName {1}'.format(k8s_resource_name, spec['dbName']))
        db_created = create_db_if_not_exists(cur, spec['dbName'])
        role_created = create_role_not_exists(cur, spec['dbRoleName'], spec['dbRolePassword'])
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE {0} to {1};".format(spec['dbName'], spec['dbRoleName']))

        if ('dbExtensions' in spec or 'extraSQL' in spec) and not db_created:
            logger.info('Ingoring extra SQL commands for {0} in DB {1} as it is already created'.format(k8s_resource_name, spec['dbName']))

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
                    logger.info('Creating extension {0} in DB {1}'.format(ext, spec['dbName']))
                    db_cur.execute('CREATE EXTENSION IF NOT EXISTS "{0}";'.format(ext))

            if 'extraSQL' in spec:
                db_conn = psycopg2.connect(**user_credentials)
                db_cur = db_conn.cursor()
                db_conn.set_session(autocommit=False)
                logger.info('Running extra SQL commands for {0} in DB {1}'.format(k8s_resource_name, spec['dbName']))
                try:
                    db_cur.execute(spec['extraSQL'])
                    db_conn.commit()
                except psycopg2.OperationalError as e:
                    logger.error('OperationalError when running extraSQL from {0} for DB {1}: {2}'.format(k8s_resource_name, spec['dbName'], e))
                except psycopg2.ProgrammingError as e:
                    logger.error('ProgrammingError when running extraSQL from {0} for DB {1}: {2}'.format(k8s_resource_name, spec['dbName'], e))

            db_cur.close()

    cur.close()
