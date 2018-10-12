# Kubernetes postgres-controller

  <img src="https://raw.githubusercontent.com/max-rocket-internet/postgres-controller/master/img/k8s-logo.png" width="100"> + <img src="https://raw.githubusercontent.com/max-rocket-internet/postgres-controller/master/img/postgres-logo.png" width="100">

A simple k8s controller to create PostgresSQL databases. Once you install the controller and point it at your existing PostgresSQL database instance, you can create `PostgresDatabase` resource in k8s and the controller will create a database in your PostgresSQL instance, create a role that with access to this database and optionally install any extensions and run extra SQL commands.

Example resource:

```yaml
apiVersion: postgresql.org/v1
kind: PostgresDatabase
metadata:
  name: app1
spec:
  dbName: db1
  dbRoleName: user1
  dbRolePassword: swordfish
```

Pull requests welcome.

### Installation

Use the included [Helm](https://helm.sh/) chart and set the host, username and password for your PostgresSQL instance:

```
helm install ./chart --set postgres.host=my-rds-instance.rds.amazonaws.com --set postgres.user=root --set postgres.password=admin_password
```

### Examples

See [examples](examples) to for how to add extensions, extra SQL commands and also how to drop databases when the k8s resource is deleted.

### Testing

To test locally, start a postgres container:

```
docker run -d -p 127.0.0.1:5432:5432 -e POSTGRES_PASSWORD=postgres postgres:9.6
```

Export required environment variables:

```
export DB_HOST=localhost
export DB_PASSWORD=postgres
export DB_USER=postgres
```

Start the controller, it will use your default kubectl configuration/context:

```
./controller.py
```

Create or change some resources:

```
kubectl apply -f examples/simple.yaml
```
