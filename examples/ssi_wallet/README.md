# Presentation Definitions for the SSI wallet hands-on

These files are served by the publisher at
`GET /verifier/presentation-definitions/{id}` and consumed by the
Sphereon-forked wallet when it handles an OID4VP Authorization Request.

The custom `iw3ip_dataset_id` top-level field lets the publisher map
`GET /verifier/request?dataset_id=...` to a specific definition without
hard-coding the mapping in Python.
