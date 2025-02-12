CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    department VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    job VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE hired_employees (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    hire_datetime TIMESTAMPTZ NOT NULL,  --handles ISO format with time zones to not lose info
    department_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Create indexes for fast lookups in the future queries
CREATE INDEX idx_hired_employees_department ON hired_employees(department_id);
CREATE INDEX idx_hired_employees_job ON hired_employees(job_id);
CREATE INDEX idx_hired_employees_datetime ON hired_employees(hire_datetime);
