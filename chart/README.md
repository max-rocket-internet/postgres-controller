# Kubernetes PostgreSQL Controller

This chart creates a [postgres-controller](https://github.com/max-rocket-internet/postgres-controller) deployment and a `PostgresDatabase` Custom Resource Definition.

## TL;DR;

```console
$ helm install stable/postgres-controller
```

## Prerequisites

- Kubernetes 1.8+

## Installing the Chart

You will need to set at least 3 parameters when installing. These options set the database hostname, username and password. To install the chart with the release name `my-release`:

```console
helm install --name my-release stable/postgres-controller --set postgres.host=my-rds-instance.rds.amazonaws.com --set postgres.user=root --set postgres.password=swordfish
```

## Uninstalling the Chart

To delete the chart:

```console
$ helm delete my-release
```

## Configuration

The following table lists the configurable parameters for this chart and their default values.

| Parameter                          | Description                               | Default                        |
| ---------------------------------- | ----------------------------------------- |------------------------------- |
| `annotations`                      | Optional deployment annotations           | `{}`                           |
| `affinity`                         | Map of node/pod affinities                | `{}`                           |
| `image.repository`                 | Image                                     | `futurish/postgres-controller` |
| `image.tag`                        | Image tag                                 | `0.1`                          |
| `image.pullPolicy`                 | Image pull policy                         | `IfNotPresent`                 |
| `rbac.create`                      | RBAC                                      | `true`                         |
| `resources`                        | CPU limit                                 | `{}`                           |
| `tolerations`                      | Optional deployment tolerations           | `{}`                           |
| `postgres.host`                    | Postgres hostname                         | `NULL`                         |
| `postgres.user`                    | Postgres user                             | `NULL`                         |
| `postgres.password`                | Postgres password                         | `NULL`                         |
| `log_level`                        | Log level for controller (`info`|`debug`) | `info`                         |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install` or provide a YAML file containing the values for the above parameters:

```console
$ helm install --name my-release stable/postgres-controller --values values.yaml
```
