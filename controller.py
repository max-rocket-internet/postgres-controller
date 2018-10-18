#!/usr/bin/env python3

from kubernetes import client, watch
import json
from functions import get_config, process_event, create_logger


runtime_config = get_config()
crds = client.CustomObjectsApi()
logger = create_logger(log_level=runtime_config['log_level'])


resource_version = ''

if __name__ == "__main__":
    while True:
        logger.info('postgres-controller initializing')
        stream = watch.Watch().stream(crds.list_cluster_custom_object, 'postgresql.org', 'v1', 'pgdatabases', resource_version=resource_version)
        try:
            for event in stream:
                event_type = event["type"]
                obj = event["object"]
                metadata = obj.get('metadata')
                spec = obj.get('spec')

                if not metadata or not spec:
                    logger.error('No metadata or spec in object, skipping: {0}'.format(json.dumps(obj, indent=1)))
                    continue

                if metadata['resourceVersion'] is not None:
                    resource_version = metadata['resourceVersion']
                    logger.debug('resourceVersion now: {0}'.format(resource_version))

                process_event(crds, obj, event_type, runtime_config)

        except client.rest.ApiException as e:
            if e.status == 404:
                logger.error('Custom Resource Definition not created in cluster')
                break
            else:
                raise e
        except KeyboardInterrupt:
            break
