# To do

- Fix `openAPIV3Schema` validation in CRD definition so that it matches Postgres standards
- Fix `additionalPrinterColumns` in CRD definition
- Add update events of `PostgresDatabase` resources (only beta in k8s 1.11)
- Error checking and exception catching x1000
- Reduce docker image size
- Handle SIGTERM
- Write a class for handling events

Features:

- Add CRD for managing Postgres roles
- Allow granular permissions for dbRoleName
- Handle `MODIFIED` type of events?
