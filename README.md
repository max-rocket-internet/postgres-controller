# Kubernetes postgres-controller

A simple controller and helm chart to manage Postgres databases in an existing Postgres instance from Kubernetes. Once installed, you can define a `PostgresDatabase` resource and it will be created in your Postgres database host. Great for use with AWS RDS.

Example resource that will create a database and role with access:

```
apiVersion: postgresql.org/v1
kind: PostgresDatabase
metadata:
  name: app1
spec:
  dbName: db1
  dbRoleName: user1
  dbRolePassword: swordfish
```

### Install the controller

Use the included [Helm](https://helm.sh/) chart and be sure you set the host, username and password for your Postgres instance:

```
helm install ./chart --set postgres.host=my-rds-instance.rds.amazonaws.com --set postgres.user=root --set postgres.password=swordfish
```

### Examples

See [examples](examples).

### Test locally

Start a postgres container:

```
docker run -d -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD=postgres postgres:9.6
```

Export required environment variables:

```
export DB_HOST=localhost
export DB_PASSWORD=postgres
export DB_USER=postgres
```

Run the controller

```
./controller.py
```
