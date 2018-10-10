# To do

- Fix `openAPIV3Schema` validation in CRD definition so that it matches Postgres standards
- Fix `additionalPrinterColumns` in CRD definition
- Add update events of `PostgresDatabase` resources
- Error checking x1000
- Add command line arguments for debug etc
- Reduce docker image size

Features:

- Add CRD for managing Postgres roles
- Allow different access permissions for role
- Handle `MODIFIED` type of events?
