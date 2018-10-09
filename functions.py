# -*- coding: utf-8 -*-

import os
from kubernetes import config


def convert_to_bool(value):
    '''
    Converts a value to a boolean
    '''
    return value in [1, 'true', 'True', 'yes', '1', True]


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
            'dbname': os.getenv('DB_NAME', 'postgres'),
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD'],
        },
        'drop_on_deletion': convert_to_bool(os.getenv('DROP_ON_DELETION', False)),
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
        print('DB {0} already exists'.format(db_name))


def create_role_not_exists(cur, role_name, role_password):
    '''
    A function to create a role if it does not already exist
    '''
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = '{}';".format(role_name))
    if not cur.fetchone():
        cur.execute("CREATE ROLE {0} PASSWORD '{1}' LOGIN;".format(role_name, role_password))
    else:
        print('Role {0} already exists'.format(role_name))


def process_event(conn, crds, obj, event_type):
    '''
    Processes events in order to create or drop databases
    '''
    spec = obj.get('spec')
    metadata = obj.get('metadata')

    cur = conn.cursor()
    conn.set_session(autocommit=True)

    print('Updating {0} DB {1}'.format(metadata.get('name'), spec['dbName']))

    create_db_if_not_exists(cur, spec['dbName'])
    create_role_not_exists(cur, spec['dbRoleName'], spec['dbRolePassword'])
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE {0} to {1};".format(spec['dbName'], spec['dbRoleName']))

    if spec.get('dbExtensions'):
        for ext in spec['dbExtensions']:
            print('Creating extension {0} in DB {1}'.format(ext, spec['dbName']))
            cur.execute("CREATE EXTENSION IF NOT EXISTS {0};".format(ext))

    if spec.get('extraSQL'):
        conn.set_session(autocommit=False)
        cur.execute(spec['extraSQL'])
        conn.commit()

    cur.close()
