-- @block
-- @conn mappingasia-dev datascience
select * from datascience.sdg_goals;
select * from datascience.sdg_targets;
select * from datascience.sdg_indicators;
select * from datascience.sdg_series;


-- @block
-- @conn mappingasia-dev datascience
select 
    * 
from datascience.sdg_series
where "id" like 'EN_ATM_CO2%';
