-- @block
-- @conn mappingasia-dev datascience
select 
	"official_name_en" as "name",
	"UNTERM_English_Formal" as "name_long",
	"ISO3166_1_Alpha_2" as "iso_a2",
	"ISO3166_1_Alpha_3" as "iso_a3",
	"ISO3166_1_numeric" as "iso_numeric",
	"M49" as "unsd_m49",
	"Continent" as "continent",
	"Developed_or_Developing_Countries" as "developed_developing",
	"Languages" as "lang",
	"Region_Code" as region_code,
	"Region_Name" as region_name,
	"Sub_region_Code" as subregion_code,
	"Sub_region_Name" as subregion_name,
	"is_independent" as is_independent
from datascience.country_list
where "Region_Name" = 'Asia'
and "Developed_or_Developing_Countries" = 'Developed';