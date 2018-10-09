# To do

- Fix `openAPIV3Schema` validation in CRD definition so that it matches Postgres standards
- Fix `additionalPrinterColumns` in CRD definition
- Reduce docker image size
- Add update events of `PostgresDatabase` resources
- Error checking x1000
- Add proper logging instead of `print`
- Add command line arguments

Features:

- Add CRD for managing Postgres roles
- Allow different access permissions for role
- Allow per DB deletion option using annotation
