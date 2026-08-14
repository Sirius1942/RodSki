# Demo data

`data.sqlite` is the only test-data file used by this module. It contains:

- RodSki's EAV metadata tables: `rs_datatable`, `rs_datatable_field`,
  `rs_row`, and `rs_field`.
- The `DemoDB` logical data table with `Q_WRITE` and `Q_READ` rows.
- An `audit_log` business table used to prove that the denied write never ran.

`globalvalue.xml` configures `demo_db` as SQLite and resolves the database path
relative to the module directory as `data/data.sqlite`.
