-- @conn mappingasia-dev root

-- @block CREATE USERS
create user datascience with encrypted password 'TZAUfThGBTL7ps_2C4VU';
create user readonly with encrypted password 'T20bIKiMUm9d49xY_2j6';

-- @block CREATE SCHEMA
create schema datascience;

-- @block  MAX PRIVILEGES
GRANT ALL ON SCHEMA datascience TO datascience;
GRANT USAGE ON SCHEMA datascience TO datascience;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA datascience TO datascience;

-- @block  READ ONLY PRIVILEGES
GRANT USAGE ON SCHEMA datascience TO readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA datascience TO readonly;

-- @block  SELECT CURRENT ROLES
select * from information_schema.role_table_grants;


-- @block grant all data to admin
-- @conn mappingasia-dev datascience
GRANT ALL ON SCHEMA datascience TO dbm20190818;
GRANT USAGE ON SCHEMA datascience TO dbm20190818;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA datascience TO dbm20190818;