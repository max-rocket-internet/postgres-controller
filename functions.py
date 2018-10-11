# -*- coding: utf-8 -*-

import os
import json
from kubernetes import config
import logging
import psycopg2
import logging.handlers


logger = logging.getLogger()


def convert_to_bool(value):
    '''
    Converts a value to a boolean
    '''
    return value in [1, 'true', 'True', 'yes', '1', True]


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


def get_config():
    '''
    Gets the run time configuration from the environment
    '''

    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()

    settings = {
        'db_credentials': {
            'host': os.environ['DB_HOST'],
            'port': os.getenv('DB_PORT', 5432),
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD'],
        },
        'log_level': os.getenv('LOG_LEVEL', 'info'),
    }

    return settings


def create_db_if_not_exists(cur, db_name):
    '''
    A function to create a database if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_database WHERE datname = '{}';".format(db_name))
    if not cur.fetchone():
        cur.execute("CREATE DATABASE {};".format(db_name))
    else:
        logger.debug('Database {0} already exists'.format(db_name))


def create_role_not_exists(cur, role_name, role_password):
    '''
    A function to create a role if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = '{}';".format(role_name))
    if not cur.fetchone():
        cur.execute("CREATE ROLE {0} PASSWORD '{1}' LOGIN;".format(role_name, role_password))
    else:
        logger.debug('Role {0} already exists'.format(role_name))


def process_event(crds, obj, event_type, runtime_config):
    '''
    Processes events in order to create or drop databases
    '''
    logger = logging.getLogger()
    spec = obj.get('spec')
    metadata = obj.get('metadata')


    logger.debug('Processing event: {0}'.format(json.dumps(obj, indent=1)))


    if event_type == 'MODIFIED':
        logger.debug('Ignoring modification for {0} DB {1}, not supported'.format(metadata.get('name'), spec['dbName']))
        return

    conn = psycopg2.connect(**runtime_config['db_credentials'])
    cur = conn.cursor()
    conn.set_session(autocommit=True)


    if event_type == 'DELETED':
        logger.info('Deleting PostgresDatabase {0}, dbName {1}'.format(metadata.get('name'), spec['dbName']))
        try:
            drop_db = spec['onDeletion']['dropDB']
        except KeyError:
            drop_db = False
        if drop_db:
            logger.info('Dropping {0} DB {1}'.format(metadata.get('name'), spec['dbName']))
            cur.execute("DROP DATABASE {0};".format(spec['dbName']))
        else:
            logger.info('Ignoring deletion for {0} database {1}, onDeletion setting not enabled'.format(metadata.get('name'), spec['dbName']))

        try:
            drop_role = spec['onDeletion']['dropRole']
        except KeyError:
            drop_db = False
        if drop_role:
            logger.info('Dropping {0} role {1}'.format(metadata.get('name'), spec['dbRoleName']))
            cur.execute("DROP ROLE {0};".format(spec['dbRoleName']))
        else:
            logger.info('Ignoring deletion for {0} role {1}, onDeletion setting not enabled'.format(metadata.get('name'), spec['dbName']))


    elif event_type == 'ADDED':
        logger.info('Adding PostgresDatabase {0}, dbName {1}'.format(metadata.get('name'), spec['dbName']))
        create_db_if_not_exists(cur, spec['dbName'])
        create_role_not_exists(cur, spec['dbRoleName'], spec['dbRolePassword'])
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE {0} to {1};".format(spec['dbName'], spec['dbRoleName']))

        if 'dbExtensions' in spec or 'extraSQL' in spec:
            db_conn = psycopg2.connect(**{**runtime_config['db_credentials'], **{'dbname': spec['dbName']}})
            db_cur = db_conn.cursor()

            if 'dbExtensions' in spec:
                db_conn.set_session(autocommit=True)
                for ext in spec['dbExtensions']:
                    logger.info('Creating extension {0} in DB {1}'.format(ext, spec['dbName']))
                    db_cur.execute("CREATE EXTENSION IF NOT EXISTS {0};".format(ext))

            if 'extraSQL' in spec:
                db_conn.set_session(autocommit=False)
                db_cur.execute(spec['extraSQL'])
                db_conn.commit()

            db_cur.close()

    cur.close()
