#!/usr/bin/env python3

from kubernetes import client, watch
import psycopg2
import json
from functions import get_config, process_event


runtime_config = get_config()
crds = client.CustomObjectsApi()
conn = psycopg2.connect(**runtime_config['db_credentials'])


resource_version = ''

if __name__ == "__main__":
    while True:
        print('postgres-controller initializing')
        stream = watch.Watch().stream(crds.list_cluster_custom_object, 'postgresql.org', 'v1', 'pgdatabases', resource_version=resource_version)
        try:
            for event in stream:
                event_type = event["type"]
                obj = event["object"]
                metadata = obj.get('metadata')
                spec = obj.get('spec')

                if not metadata or not spec:
                    print('No metadata or spec in object, skipping: {0}'.format(json.dumps(obj, indent=1)))
                    continue

                if event_type == 'DELETED' and runtime_config['drop_on_deletion'] == False:
                    print('ignoring deletion for DB {0} because DROP_ON_DELETION is not enabled'.format(metadata['name']))
                    continue

                if metadata['resourceVersion'] is not None:
                    resource_version = metadata['resourceVersion']
                    print(resource_version)

                process_event(conn, crds, obj, event_type)

        except client.rest.ApiException as e:
            if e.status == 404:
                print('Custom Resource Definition not created in cluster')
                break
            else:
                raise e
        except KeyboardInterrupt:
            break
