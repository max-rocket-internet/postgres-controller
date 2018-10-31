# To do

- Fix `openAPIV3Schema` validation in CRD definition so that it matches Postgres standards
- Fix `additionalPrinterColumns` in CRD definition
- Add update events of `PostgresDatabase` resources (only beta in k8s 1.11)
- Error checking and exception catching x1000
- Reduce docker image size
- Fix error:

    ```
    {"time":"2018-10-31 16:00:51,748", "level":"ERROR", "message":"No metadata or spec in object, skipping: {
     "kind": "Status",
     "apiVersion": "v1",
     "metadata": {},
     "status": "Failure",
     "message": "too old resource version: 93971 (1325590)",
     "reason": "Gone",
     "code": 410
    }"}
    ```

Features:

- Add CRD for managing Postgres roles
- Allow different access permissions for role
- Handle `MODIFIED` type of events?
