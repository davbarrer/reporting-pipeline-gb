-- Create a sequence for each table starting in the last id +1 after the migration
CREATE SEQUENCE IF NOT EXISTS departments_id_seq START WITH 13;
CREATE SEQUENCE IF NOT EXISTS jobs_id_seq START WITH 184;
CREATE SEQUENCE IF NOT EXISTS hired_employees_id_seq START WITH 2000;

-- Link the sequence to the `id` column
ALTER TABLE departments ALTER COLUMN id SET DEFAULT nextval('departments_id_seq');
ALTER TABLE jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq');
ALTER TABLE hired_employees ALTER COLUMN id SET DEFAULT nextval('hired_employees_id_seq');

-- Ensure the sequences start from the next available ID
SELECT setval('departments_id_seq', (SELECT MAX(id) FROM departments));
SELECT setval('jobs_id_seq', (SELECT MAX(id) FROM jobs));
SELECT setval('hired_employees_id_seq', (SELECT MAX(id) FROM hired_employees));
