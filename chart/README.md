# Kubernetes PostgreSQL Controller

This chart creates a [postgres-controller](https://github.com/max-rocket-internet/postgres-controller) deployment and a `PostgresDatabase` Custom Resource Definition.

## TL;DR;

You will need to set at least 3 parameters when installing. These options set the default database hostname, username and password:

```console
$ helm install --name my-release ./chart --set config.postgres_instances.default.host=my-rds-instance.rds.amazonaws.com --set config.postgres_instances.default.user=root --set config.postgres_instances.default.password=swordfish
```

## Prerequisites

- Kubernetes 1.8+

## Uninstalling the Chart

To delete the chart:

```console
$ helm delete --purge my-release
```

## Configuration

The following table lists the configurable parameters for this chart and their default values.

| Parameter          | Description                                                      | Default                        |
|--------------------|------------------------------------------------------------------|--------------------------------|
| `annotations`      | Optional deployment annotations                                  | `{}`                           |
| `affinity`         | Map of node/pod affinities                                       | `{}`                           |
| `image.repository` | Image                                                            | `maxrocketinternet/postgres-controller`      |
| `image.tag`        | Image tag                                                        | `0.5`                          |
| `image.pullPolicy` | Image pull policy                                                | `IfNotPresent`                 |
| `rbac.create`      | RBAC                                                             | `true`                         |
| `resources`        | Pod resource requests and limits                                 | `{}`                           |
| `tolerations`      | Optional deployment tolerations                                  | `[]`                           |
| `config`           | Map containing Postgres instances. See `values.yaml` for example | `{}`                           |
| `log_level`        | Log level for controller (`info`|`debug`)                        | `info`                         |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install` or provide a YAML file containing the values for the above parameters:

```console
$ helm install --name my-release ./chart --values my-values.yaml
```
