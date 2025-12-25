-- tables for the weather data
-- this is mostly just config for downloading data since we are saving real files
-- to our directory structure that we have

DROP DATABASE IF EXISTS world_sim_weather;
CREATE DATABASE world_sim_weather CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE world_sim_weather;

-- table for the weather data columns that we
-- want to pull

CREATE TABLE IF NOT EXISTS world_sim_weather.weather_data_columns (
    column_code VARCHAR(10) NOT NULL PRIMARY KEY,
    column_description TEXT NOT NULL,
    frequency VARCHAR(32) NOT NULL
);

INSERT INTO world_sim_weather.weather_data_columns (column_code, column_description, frequency) VALUES
    ("2t","2 m air temperature (K)","instantaneous"),
	("2d","2 m dew-point temperature (K)","instantaneous"),
	("sp","Surface pressure (Pa)","instantaneous"),
	("msl","Mean sea-level pressure (Pa)","instantaneous"),
	("skt","Skin (surface) temperature (K)","instantaneous"),
	("tsn","Temperature of snow layer (K)","instantaneous"),
	("tp","Total precipitation (m water)","hourly accumulation"),
	("cp","Convective precipitation (m)","hourly accumulation"),
	("lsp","Large-scale (stratiform) precipitation (m)","hourly accumulation"),
	("sf","Snowfall (m water equivalent)","hourly accumulation"),
	("sd","Snow depth (m water equivalent)","instantaneous"),
	("smlt","Snowmelt (m water equivalent)","hourly accumulation"),
	("sro","Surface runoff (m)","hourly accumulation"),
	("e","Evaporation (m water equivalent)","hourly accumulation"),
	("swvl1","Volumetric soil water, layer 1 (m³ m⁻³)","instantaneous"),
	("swvl2","Volumetric soil water, layer 2 (m³ m⁻³)","instantaneous"),
	("swvl3","Volumetric soil water, layer 3 (m³ m⁻³)","instantaneous"),
	("swvl4","Volumetric soil water, layer 4 (m³ m⁻³)","instantaneous"),
	("ssrd","Surface solar radiation downwards (J m⁻²)","hourly accumulation"),
	("ssr","Surface net solar radiation (J m⁻²)","hourly accumulation"),
	("strd","Surface thermal (longwave) radiation downwards (J m⁻²)","hourly accumulation"),
	("str","Surface net thermal (longwave) radiation (J m⁻²)","hourly accumulation"),
	("ssrdc","Clear-sky surface solar radiation downwards (J m⁻²)","hourly accumulation"),
	("strdc","Clear-sky surface thermal radiation downwards (J m⁻²)","hourly accumulation"),
	("10u","10 m wind, u-component (m s⁻¹)","instantaneous"),
	("10v","10 m wind, v-component (m s⁻¹)","instantaneous"),
	("10fg","10 m wind gust since previous hour (m s⁻¹)","hourly max"),
	("100u","100 m wind, u-component (m s⁻¹)","instantaneous"),
	("100v","100 m wind, v-component (m s⁻¹)","instantaneous"),
	("blh","Boundary-layer height (m)","instantaneous"),
	("tcc","Total cloud cover (0–1)","instantaneous"),
	("lcc","Low cloud cover (0–1)","instantaneous"),
	("mcc","Medium cloud cover (0–1)","instantaneous"),
	("hcc","High cloud cover (0–1)","instantaneous"),
	("cbh","Cloud-base height (m)","instantaneous"),
	("sst","Sea-surface temperature (K)","instantaneous"),
	("ci","Sea-ice area fraction (0–1)","instantaneous"),
	("lmlt","Lake mixed-layer temperature (K)","instantaneous"),
	("licd","Lake ice depth (m)","instantaneous"),
	("lsm","Land–sea mask (0–1; land≈1, sea≈0)","invariant"),
	("sshf","Surface sensible heat flux (J m⁻²)","hourly accumulation"),
	("slhf","Surface latent heat flux (J m⁻²)","hourly accumulation"),
	("lai_lv","Leaf area index — low vegetation (m² m⁻²)","monthly climatology"),
	("lai_hv","Leaf area index — high vegetation (m² m⁻²)","monthly climatology"),
	("fal","Forecast albedo (0–1)","instantaneous"),
	("asn","Snow albedo (0–1)","instantaneous"),
	("rsn","Snow density (kg m⁻³)","instantaneous"),
	("cape","Convective available potential energy (J kg⁻¹)","instantaneous"),
	("tcwv","Total column water vapour (kg m⁻²)","instantaneous");