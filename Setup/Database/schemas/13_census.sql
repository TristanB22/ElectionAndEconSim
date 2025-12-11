-- Census Tables
-- For census data

DROP TABLE IF EXISTS world_sim_census.census_data;
DROP TABLE IF EXISTS world_sim_census.census_columns;
DROP TABLE IF EXISTS world_sim_census.code_to_db;


CREATE TABLE world_sim_census.code_to_db (
	code VARCHAR(32) NOT NULL PRIMARY KEY,
	-- db_name VARCHAR(255) NOT NULL,
	db_description TEXT NOT NULL,
	link_type ENUM('profile', 'subject', 'housing') NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
-- Core ACS tables for agent/net-worth modeling (single insert)
INSERT INTO world_sim_census.code_to_db (code, db_description, link_type) VALUES
    -- Demographics & income priors
    ('S0101', 'ACS Age and Sex', 'subject'),
    ('S1501', 'ACS Educational Attainment', 'subject'),
    ('S1901', 'ACS Income Last 12 Months', 'subject'),
    ('B19001', 'Household Income in the Past 12 Months (Distribution)', 'housing'),
    -- Profiles (coarse aggregates for QA)
    ('DP02', 'ACS Select Social Characteristics', 'profile'),
    ('DP03', 'ACS Select Economic Characteristics', 'profile'),
    ('DP04', 'ACS Select Housing Characteristics', 'profile'),
    ('DP05', 'ACS Demographic and Housing Estimates', 'profile'),
    -- Housing tenure & value distributions
    ('B25003', 'Housing Tenure (Owner/Renter)', 'housing'),
    ('B25075', 'Value of Owner-Occupied Housing Units (Distribution)', 'housing'),
    ('B25077', 'Median Value (Owner-Occupied)', 'housing'),
    -- Mortgage/HELOC prevalence
    ('B25081', 'Mortgage Status (Owner-Occupied Units)', 'housing'),
    ('B25085', 'Presence of Second Mortgage or HELOC by Mortgage Status', 'housing'),
    -- Vehicles by household/tenure
    ('B08201', 'Household Size by Vehicles Available', 'housing'),
    ('B25044', 'Tenure by Vehicles Available', 'housing');



-- -- This table will store census data values per record
CREATE TABLE IF NOT EXISTS world_sim_census.census_columns (
	census_code VARCHAR(32) NOT NULL, -- Links to code in code_to_db
	year INT NOT NULL,
	var_code VARCHAR(64) NOT NULL,       -- Name of the variable (e.g., B01001_001E, B01001_002E, etc.)
	column_label TEXT NOT NULL, -- Name of the column/variable
	column_concept TEXT NOT NULL, -- Name of the column/variable
	predicate_type VARCHAR(32) NOT NULL,
	group_code VARCHAR(255) NOT NULL,
	limit_value BIGINT UNSIGNED NOT NULL,
	predicate_only BOOLEAN NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (census_code, year, var_code),
	FOREIGN KEY (census_code) REFERENCES world_sim_census.code_to_db(code) ON DELETE CASCADE
);

-- table for the data itself
CREATE TABLE IF NOT EXISTS world_sim_census.census_data (
    census_code VARCHAR(32) NOT NULL, -- Links to code in code_to_db
	year INT NOT NULL,
	var_code VARCHAR(64) NOT NULL,       -- Name of the variable (e.g., B01001_001E, B01001_002E, etc.)
	geo_id VARCHAR(128) NOT NULL, -- e.g. '16000US0203000-04000'
	geo_name VARCHAR(128) NOT NULL, -- e.g. 'Montgomery County, Alabama'
	geo_state char(8) NOT NULL, -- e.g. 'Alabama'
	geo_county char(8) NOT NULL, -- e.g. 'Montgomery County'
	estimated_value DECIMAL(15,4) NOT NULL,
	moe DECIMAL(15,4) NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (census_code, year, var_code, geo_id),
	FOREIGN KEY (census_code, year, var_code) REFERENCES world_sim_census.census_columns(census_code, year, var_code) ON DELETE CASCADE,
	INDEX idx_census_data_code_year (census_code, year),
	INDEX idx_census_data_var_code (var_code),
	INDEX idx_census_data_geo_id (geo_id),
	INDEX idx_census_data_geo_name (geo_name),
	INDEX idx_census_data_state_county (geo_state, geo_county)
);







-- table for census csvs (deduplicated/harmonized columns)
DROP TABLE IF EXISTS world_sim_census.pums_h;
CREATE TABLE IF NOT EXISTS world_sim_census.pums_h (
    -- ID for bookkeeping, not primary. Uniqueness by (year, SERIALNO), see below.
    year INT NOT NULL,
    RT CHAR(8),
    SERIALNO VARCHAR(13) NOT NULL,  -- e.g. '2023GQ0000247'
    DIVISION CHAR(8),
    PUMA CHAR(8) NOT NULL,
    REGION CHAR(8),
    STATE INT UNSIGNED NOT NULL,
    ADJHSG VARCHAR(8) NOT NULL,
    -- Harmonized: Only keep ADJINC (drop ADJUST)
    ADJINC VARCHAR(8) NOT NULL,
    WGTP INT NOT NULL,
    NP SMALLINT NOT NULL,
    -- Harmonized: Only keep TYPEHUGQ (drop TYPE)
    TYPEHUGQ CHAR(8),
    FS CHAR(8),
    FFSP CHAR(8),

    -- Only keep canonical replicate weights WGTP1–WGTP80 (drop lowercase wgtp*)
    WGTP1 INT NOT NULL, WGTP2 INT NOT NULL, WGTP3 INT NOT NULL, WGTP4 INT NOT NULL, WGTP5 INT NOT NULL,
    WGTP6 INT NOT NULL, WGTP7 INT NOT NULL, WGTP8 INT NOT NULL, WGTP9 INT NOT NULL, WGTP10 INT NOT NULL,
    WGTP11 INT NOT NULL, WGTP12 INT NOT NULL, WGTP13 INT NOT NULL, WGTP14 INT NOT NULL, WGTP15 INT NOT NULL,
    WGTP16 INT NOT NULL, WGTP17 INT NOT NULL, WGTP18 INT NOT NULL, WGTP19 INT NOT NULL, WGTP20 INT NOT NULL,
    WGTP21 INT NOT NULL, WGTP22 INT NOT NULL, WGTP23 INT NOT NULL, WGTP24 INT NOT NULL, WGTP25 INT NOT NULL,
    WGTP26 INT NOT NULL, WGTP27 INT NOT NULL, WGTP28 INT NOT NULL, WGTP29 INT NOT NULL, WGTP30 INT NOT NULL,
    WGTP31 INT NOT NULL, WGTP32 INT NOT NULL, WGTP33 INT NOT NULL, WGTP34 INT NOT NULL, WGTP35 INT NOT NULL,
    WGTP36 INT NOT NULL, WGTP37 INT NOT NULL, WGTP38 INT NOT NULL, WGTP39 INT NOT NULL, WGTP40 INT NOT NULL,
    WGTP41 INT NOT NULL, WGTP42 INT NOT NULL, WGTP43 INT NOT NULL, WGTP44 INT NOT NULL, WGTP45 INT NOT NULL,
    WGTP46 INT NOT NULL, WGTP47 INT NOT NULL, WGTP48 INT NOT NULL, WGTP49 INT NOT NULL, WGTP50 INT NOT NULL,
    WGTP51 INT NOT NULL, WGTP52 INT NOT NULL, WGTP53 INT NOT NULL, WGTP54 INT NOT NULL, WGTP55 INT NOT NULL,
    WGTP56 INT NOT NULL, WGTP57 INT NOT NULL, WGTP58 INT NOT NULL, WGTP59 INT NOT NULL, WGTP60 INT NOT NULL,
    WGTP61 INT NOT NULL, WGTP62 INT NOT NULL, WGTP63 INT NOT NULL, WGTP64 INT NOT NULL, WGTP65 INT NOT NULL,
    WGTP66 INT NOT NULL, WGTP67 INT NOT NULL, WGTP68 INT NOT NULL, WGTP69 INT NOT NULL, WGTP70 INT NOT NULL,
    WGTP71 INT NOT NULL, WGTP72 INT NOT NULL, WGTP73 INT NOT NULL, WGTP74 INT NOT NULL, WGTP75 INT NOT NULL,
    WGTP76 INT NOT NULL, WGTP77 INT NOT NULL, WGTP78 INT NOT NULL, WGTP79 INT NOT NULL, WGTP80 INT NOT NULL,

    -- TYPE removed (use TYPEHUGQ per mapping)

    ACCESS INT UNSIGNED,
    ACR INT UNSIGNED,
    AGS INT UNSIGNED,
    BATH INT UNSIGNED,

    -- Harmonized: BDSP for bedrooms (drop BDS)
    BDSP INT UNSIGNED,

    BLD INT UNSIGNED,
    BROADBND INT UNSIGNED,
    COMPOTHX INT UNSIGNED,
    CONP INT,  -- Annual condo fee cost (dollars)
    DIALUP INT UNSIGNED,
    ELEP INT,  -- Annual electricity cost (dollars)
    FULP INT,  -- Annual fuel cost (dollars)
    GASP INT,  -- Annual gas cost (dollars)
    HFL INT UNSIGNED,
    HISPEED INT UNSIGNED,
    HOTWAT INT UNSIGNED,
    INSP INT,  -- Annual insurance cost (dollars)
    LAPTOP INT UNSIGNED,
    MRGI INT UNSIGNED,
    MRGP INT,  -- Monthly mortgage payment (dollars)
    MRGT INT UNSIGNED,
    MRGX INT UNSIGNED,
    OTHSVCEX INT UNSIGNED,
    REFR INT UNSIGNED,

    -- Harmonized: RMSP for rooms (drop RMS)
    RMSP INT UNSIGNED,

    RWAT INT UNSIGNED,
    RWATPR INT UNSIGNED,
    SATELLITE INT UNSIGNED,
    SINK INT UNSIGNED,
    SMARTPHONE INT UNSIGNED,
    STOV INT UNSIGNED,
    TABLET INT UNSIGNED,
    TEL INT UNSIGNED,
    TEN INT UNSIGNED,

    -- Harmonized: VALP for value (drop VAL)
    VALP INT,  -- Property value (dollars)

    VEH INT UNSIGNED,
    WATP INT,  -- Annual water cost (dollars)

    -- Harmonized: YBL (drop FMVYP)
    YBL INT UNSIGNED,

    FES INT UNSIGNED,
    -- Keep both incomes, definition differs
    FINCP INT,  -- Family income (dollars)
    FPARC INT UNSIGNED,
    HHL INT UNSIGNED,
    HHLANP INT UNSIGNED,
    HHT INT UNSIGNED,
    HINCP INT,  -- Household income (dollars)
    HUGCL INT UNSIGNED,
    HUPAC INT UNSIGNED,
    HUPAOC INT UNSIGNED,
    HUPARC INT UNSIGNED,
    KIT INT UNSIGNED,
    LNGI INT UNSIGNED,
    MULTG INT UNSIGNED,
    MV INT UNSIGNED,
    NOC INT UNSIGNED,
    NPF INT UNSIGNED,
    NPP INT UNSIGNED,
    NR INT UNSIGNED,
    NRC INT UNSIGNED,
    OCPIP INT UNSIGNED,
    PARTNER INT UNSIGNED,
    PLM INT UNSIGNED,
    PLMPRP INT UNSIGNED,
    PSF INT UNSIGNED,
    R18 INT UNSIGNED,
    R60 INT UNSIGNED,
    R65 INT UNSIGNED,
    RESMODE INT UNSIGNED,
    SMOCP INT,  -- Selected monthly owner costs (dollars)
    SMX INT UNSIGNED,
    SRNT INT UNSIGNED,
    SSMC INT UNSIGNED,
    SVAL INT,  -- Second property value (dollars)
    TAXP INT,  -- Annual property tax (dollars)
    WIF INT UNSIGNED,
    WKEXREL INT UNSIGNED,
    WORKSTAT INT UNSIGNED,

    -- Family/household flags, sampled as 1 char
    FACCESSP INT UNSIGNED,
    FACRP INT UNSIGNED,
    FAGSP INT UNSIGNED,
    FBATHP INT UNSIGNED,
    FBDSP INT UNSIGNED,
    FBLDP INT UNSIGNED,
    FBROADBNDP INT UNSIGNED,
    FCOMPOTHXP INT UNSIGNED,
    FCONP INT UNSIGNED,
    FDIALUPP INT UNSIGNED,
    FELEP INT UNSIGNED,
    FFINCP INT UNSIGNED,
    FFULP INT UNSIGNED,
    FGASP INT UNSIGNED,
    FGRNTP INT UNSIGNED,
    FHFLP INT UNSIGNED,
    FHINCP INT UNSIGNED,
    FHISPEEDP INT UNSIGNED,
    FHOTWATP INT UNSIGNED,
    FINSP INT UNSIGNED,
    FKITP INT UNSIGNED,
    FLAPTOPP INT UNSIGNED,
    FMHP INT UNSIGNED,
    FMRGIP INT UNSIGNED,
    FMRGP INT UNSIGNED,
    FMRGTP INT UNSIGNED,
    FMRGXP INT UNSIGNED,
    FMVYP INT UNSIGNED,
    FOTHSVCEXP INT UNSIGNED,
    FPLMP INT UNSIGNED,
    FPLMPRP INT UNSIGNED,
    FREFRP INT UNSIGNED,
    FRMSP INT UNSIGNED,
    FRNTMP INT UNSIGNED,
    FRNTP INT UNSIGNED,
    FRWATP INT UNSIGNED,
    FRWATPRP INT UNSIGNED,
    FSATELLITEP INT UNSIGNED,
    FSINKP INT UNSIGNED,
    FSMARTPHONP INT UNSIGNED,
    FSMOCP INT UNSIGNED,
    FSMP INT UNSIGNED,
    FSMXHP INT UNSIGNED,
    FSMXSP INT UNSIGNED,
    FSTOVP INT UNSIGNED,
    FTABLETP INT UNSIGNED,
    FTAXP INT UNSIGNED,
    FTELP INT UNSIGNED,
    FTENP INT UNSIGNED,
    FVACSP INT UNSIGNED,
    FVALP INT UNSIGNED,
    FVEHP INT UNSIGNED,
    FWATP INT UNSIGNED,
    FYBLP INT UNSIGNED,

    RNTM INT UNSIGNED,  -- Rent meals included (categorical)
    RNTP INT,  -- Monthly rent payment (dollars)
    GRNTP INT,  -- Gross monthly rent (dollars)
    GRPIP INT,  -- Gross rent as percentage of income (integer percentage)
    VACS INT UNSIGNED,
    MHP INT UNSIGNED,
    SMP INT UNSIGNED,

    -- INTERNET ACCESS MODES (harmonized: keep BROADBND, also allow legacy DSL/MODEM/FIBEROP as categorical for old/compatibility)
    BUS INT UNSIGNED,
    TOIL INT UNSIGNED,
    FBUSP INT UNSIGNED,
    FDSLP INT UNSIGNED,
    FFIBEROPP INT UNSIGNED,
    FHANDHELDP INT UNSIGNED,
    FMODEMP INT UNSIGNED,
    FTOILP INT UNSIGNED,
    HANDHELD INT UNSIGNED,
    DSL INT UNSIGNED,
    FIBEROP INT UNSIGNED,
    MODEM INT UNSIGNED,

    -- Remove ADJUST (use ADJINC)
    -- Remove duplicated BDS, RMS, VAL, FMVYP (replaced above)

    -- These were not previously declared in the CREATE TABLE above:
    SRNTEMP INT UNSIGNED,        -- e.g. '0'
    FWIFP INT UNSIGNED,          -- e.g. '0'
    FSRNTEMP INT UNSIGNED,       -- e.g. '0'
    FFS INT UNSIGNED,            -- e.g. '0'
    FFFSP INT UNSIGNED,          -- e.g. '0'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_year_serialno (year, SERIALNO)
);



-- table for census csvs (person, deduplicated/harmonized columns)
DROP TABLE IF EXISTS world_sim_census.pums_p;
CREATE TABLE IF NOT EXISTS world_sim_census.pums_p (
    -- identity
    year INT NOT NULL,                                 -- acs year of the file
    RT CHAR(8),                               -- 'P'
    SERIALNO VARCHAR(13) NOT NULL,                     -- links back to household
    SPORDER CHAR(8) NOT NULL,                          -- person number within serial
    DIVISION CHAR(8),
    PUMA CHAR(8) NOT NULL,
    REGION CHAR(8),
    STATE CHAR(8) NOT NULL,                               -- from STATE/ST
    ADJINC VARCHAR(8) NOT NULL,                        -- use ADJINC; map ADJUST -> ADJINC if needed

    -- person weight (canonical)
    PWGTP INT NOT NULL,
    -- keep only canonical replicate weights PWGTP1–PWGTP80
    PWGTP1 INT NOT NULL,  PWGTP2 INT NOT NULL,  PWGTP3 INT NOT NULL,  PWGTP4 INT NOT NULL,  PWGTP5 INT NOT NULL,
    PWGTP6 INT NOT NULL,  PWGTP7 INT NOT NULL,  PWGTP8 INT NOT NULL,  PWGTP9 INT NOT NULL,  PWGTP10 INT NOT NULL,
    PWGTP11 INT NOT NULL, PWGTP12 INT NOT NULL, PWGTP13 INT NOT NULL, PWGTP14 INT NOT NULL, PWGTP15 INT NOT NULL,
    PWGTP16 INT NOT NULL, PWGTP17 INT NOT NULL, PWGTP18 INT NOT NULL, PWGTP19 INT NOT NULL, PWGTP20 INT NOT NULL,
    PWGTP21 INT NOT NULL, PWGTP22 INT NOT NULL, PWGTP23 INT NOT NULL, PWGTP24 INT NOT NULL, PWGTP25 INT NOT NULL,
    PWGTP26 INT NOT NULL, PWGTP27 INT NOT NULL, PWGTP28 INT NOT NULL, PWGTP29 INT NOT NULL, PWGTP30 INT NOT NULL,
    PWGTP31 INT NOT NULL, PWGTP32 INT NOT NULL, PWGTP33 INT NOT NULL, PWGTP34 INT NOT NULL, PWGTP35 INT NOT NULL,
    PWGTP36 INT NOT NULL, PWGTP37 INT NOT NULL, PWGTP38 INT NOT NULL, PWGTP39 INT NOT NULL, PWGTP40 INT NOT NULL,
    PWGTP41 INT NOT NULL, PWGTP42 INT NOT NULL, PWGTP43 INT NOT NULL, PWGTP44 INT NOT NULL, PWGTP45 INT NOT NULL,
    PWGTP46 INT NOT NULL, PWGTP47 INT NOT NULL, PWGTP48 INT NOT NULL, PWGTP49 INT NOT NULL, PWGTP50 INT NOT NULL,
    PWGTP51 INT NOT NULL, PWGTP52 INT NOT NULL, PWGTP53 INT NOT NULL, PWGTP54 INT NOT NULL, PWGTP55 INT NOT NULL,
    PWGTP56 INT NOT NULL, PWGTP57 INT NOT NULL, PWGTP58 INT NOT NULL, PWGTP59 INT NOT NULL, PWGTP60 INT NOT NULL,
    PWGTP61 INT NOT NULL, PWGTP62 INT NOT NULL, PWGTP63 INT NOT NULL, PWGTP64 INT NOT NULL, PWGTP65 INT NOT NULL,
    PWGTP66 INT NOT NULL, PWGTP67 INT NOT NULL, PWGTP68 INT NOT NULL, PWGTP69 INT NOT NULL, PWGTP70 INT NOT NULL,
    PWGTP71 INT NOT NULL, PWGTP72 INT NOT NULL, PWGTP73 INT NOT NULL, PWGTP74 INT NOT NULL, PWGTP75 INT NOT NULL,
    PWGTP76 INT NOT NULL, PWGTP77 INT NOT NULL, PWGTP78 INT NOT NULL, PWGTP79 INT NOT NULL, PWGTP80 INT NOT NULL,

    -- core demographics
    AGEP INT,
    SEX INT UNSIGNED,
    HISP INT UNSIGNED,
    RAC1P INT UNSIGNED,
    RAC2P INT UNSIGNED,
    RAC3P INT UNSIGNED,
    RACAIAN INT UNSIGNED,
    RACASN INT UNSIGNED,
    RACBLK INT UNSIGNED,
    RACNH INT UNSIGNED,
    RACNHPI INT UNSIGNED,
    RACNUM INT UNSIGNED,
    RACPI INT UNSIGNED,
    RACSOR INT UNSIGNED,
    RACWHT INT UNSIGNED,
    WAOB INT UNSIGNED,
    QTRBIR INT UNSIGNED,
    RELP INT UNSIGNED,              -- basic relationship
    RELSHIPP INT UNSIGNED,          -- detailed relationship
    MSP INT UNSIGNED,               -- marital status current
    MAR INT UNSIGNED,               -- marital status ever
    MARHD INT UNSIGNED,
    MARHM INT UNSIGNED,
    MARHT INT UNSIGNED,
    MARHW INT UNSIGNED,
    MARHYP INT UNSIGNED,
    -- family-related derived
    ESP INT UNSIGNED,
    NOP INT UNSIGNED,

    -- nativity / migration / citizenship
    CIT INT UNSIGNED,
    NATIVITY INT UNSIGNED,
    CITWP INT UNSIGNED,
    MIG INT UNSIGNED,
    MIGPUMA INT UNSIGNED,
    MIGSP INT UNSIGNED,
    POBP INT UNSIGNED,

    -- language / english ability
    LANX INT UNSIGNED,
    LANP INT UNSIGNED,
    ENG INT UNSIGNED,

    -- disability
    DEAR INT UNSIGNED,
    DEYE INT UNSIGNED,
    DOUT INT UNSIGNED,
    DPHY INT UNSIGNED,
    DREM INT UNSIGNED,
    DDRS INT UNSIGNED,
    DIS INT UNSIGNED,

    -- schooling
    SCH INT UNSIGNED,
    SCHG INT UNSIGNED,
    SCHL INT UNSIGNED,
    FSCHP INT UNSIGNED,
    FSCHGP INT UNSIGNED,
    FSCHLP INT UNSIGNED,

    -- income / earnings (person level)
    PINCP INT,
    PERNP INT,
    WAGP INT,
    OIP INT,
    PAP INT,
    RETP INT,
    SSIP INT,
    SSP INT,
    INTP INT,
    SEPM INT DEFAULT 0,                 -- if some years use SEPM / SEMP
    SEMP INT,                  -- self-employment
    POVPIP INT,

    -- health insurance
    HICOV INT UNSIGNED,
    HIMRKS INT UNSIGNED,
    HINS1 INT UNSIGNED,
    HINS2 INT UNSIGNED,
    HINS3 INT UNSIGNED,
    HINS4 INT UNSIGNED,
    HINS5 INT UNSIGNED,
    HINS6 INT UNSIGNED,
    HINS7 INT UNSIGNED,
    PRIVCOV INT UNSIGNED,
    PUBCOV INT UNSIGNED,

    -- employment / work status
    ESR INT UNSIGNED,
    COW INT UNSIGNED,
    WRK INT UNSIGNED,
    WKL INT UNSIGNED,
    WKW INT UNSIGNED,
    WKWN INT UNSIGNED,
    WKHP INT UNSIGNED,
    UWRK INT UNSIGNED,

    -- commuting
    JWTRNS INT UNSIGNED,
    JWTR INT UNSIGNED,
    JWMNP INT UNSIGNED,
    JWRIP INT UNSIGNED,
    JWAP INT UNSIGNED,
    JWDP INT UNSIGNED,

    -- occupation / industry / soc
    INDP INT UNSIGNED,
    NAICSP CHAR(8),
    OCCP INT UNSIGNED,
    SOCP CHAR(8),
    FOD1P INT UNSIGNED,
    FOD2P INT UNSIGNED,
    SCIENGP INT UNSIGNED,
    SCIENGRLP INT UNSIGNED,

    -- military / veteran
    MIL INT UNSIGNED,
    VPS INT UNSIGNED,

    -- fertility (for females)
    FER INT UNSIGNED,

    -- mortgage / loan payment flags (person-level copies)
    MLPA INT UNSIGNED,
    MLPB INT UNSIGNED,
    MLPCD INT UNSIGNED,
    MLPE INT UNSIGNED,
    MLPFG INT UNSIGNED,
    MLPH INT UNSIGNED,
    MLPIK INT UNSIGNED,
    MLPJ INT UNSIGNED,
    MLPI INT UNSIGNED,
    MLPK INT UNSIGNED,

    -- disability-related amounts
    DRAT INT UNSIGNED,
    DRATX INT UNSIGNED,

    -- ancestry
    ANC INT UNSIGNED,
    ANC1P INT UNSIGNED,
    ANC2P INT UNSIGNED,

    -- year-of-entry / period
    YOEP INT UNSIGNED,
    DECADE INT UNSIGNED,

    -- place-of-work
    POWPUMA INT UNSIGNED,
    POWSP INT UNSIGNED,

    -- person-level allocation flags (FxxxP ...)
    FAGEP INT UNSIGNED,
    FANCP INT UNSIGNED,
    FCITP INT UNSIGNED,
    FCITWP INT UNSIGNED,
    FCOWP INT UNSIGNED,
    FDDRSP INT UNSIGNED,
    FDEARP INT UNSIGNED,
    FDEYEP INT UNSIGNED,
    FDISP INT UNSIGNED,
    FDOUTP INT UNSIGNED,
    FDPHYP INT UNSIGNED,
    FDRATP INT UNSIGNED,
    FDRATXP INT UNSIGNED,
    FDREMP INT UNSIGNED,
    FENGP INT UNSIGNED,
    FESRP INT UNSIGNED,
    FFERP INT UNSIGNED,
    FFODP INT UNSIGNED,
    FGCLP INT UNSIGNED,
    FGCMP INT UNSIGNED,
    FGCRP INT UNSIGNED,
    FHICOVP INT UNSIGNED,
    FHIMRKSP INT UNSIGNED,
    FHINS1P INT UNSIGNED,
    FHINS2P INT UNSIGNED,
    FHINS3C INT UNSIGNED,
    FHINS3P INT UNSIGNED,
    FHINS4P INT UNSIGNED,
    FHINS5P INT UNSIGNED,
    FHINS6P INT UNSIGNED,
    FHINS7P INT UNSIGNED,
    FHISP INT UNSIGNED,
    FINDP INT UNSIGNED,
    FINTP INT UNSIGNED,
    FJWDP INT UNSIGNED,
    FJWMNP INT UNSIGNED,
    FJWRIP INT UNSIGNED,
    FJWTRNSP INT UNSIGNED,
    FLANP INT UNSIGNED,
    FLANXP INT UNSIGNED,
    FMARP INT UNSIGNED,
    FMARHDP INT UNSIGNED,
    FMARHMP INT UNSIGNED,
    FMARHTP INT UNSIGNED,
    FMARHWP INT UNSIGNED,
    FMARHYP INT UNSIGNED,
    FMIGP INT UNSIGNED,
    FMIGSP INT UNSIGNED,
    FMILPP INT UNSIGNED,
    FMILSP INT UNSIGNED,
    FOCCP INT UNSIGNED,
    FOIP INT UNSIGNED,
    FPAP INT UNSIGNED,
    FPERNP INT UNSIGNED,
    FPINCP INT UNSIGNED,
    FPOBP INT UNSIGNED,
    FPOWSP INT UNSIGNED,
    FPRIVCOVP INT UNSIGNED,
    FPUBCOVP INT UNSIGNED,
    FRACP INT UNSIGNED,
    FRELSHIPP INT UNSIGNED,
    FRETP INT UNSIGNED,
    FSEMP INT UNSIGNED,
    FSEXP INT UNSIGNED,
    FSSIP INT UNSIGNED,
    FSSP INT UNSIGNED,
    FWAGP INT UNSIGNED,
    FWKHP INT UNSIGNED,
    FWKLP INT UNSIGNED,
    FWKWNP INT UNSIGNED,
    FWRKP INT UNSIGNED,
    FYOEP INT UNSIGNED,

    -- extra person flags that show up in sample
    GCL INT UNSIGNED,
    GCM INT UNSIGNED,
    GCR INT UNSIGNED,
    OC INT UNSIGNED,
    PAOC INT UNSIGNED,
    RC INT UNSIGNED,
    SSPA INT UNSIGNED,
    DS INT UNSIGNED,
    DWRK INT UNSIGNED,
    FDWRKP INT UNSIGNED,
    FMILYP INT UNSIGNED,
    MILY INT UNSIGNED,
    SFN INT UNSIGNED,
    SFR INT UNSIGNED,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY ux_year_serialno_sporder (year, SERIALNO, SPORDER)
);







-- Optional/extended ACS tables (kept for later; run if needed)
-- INSERT INTO world_sim_census.code_to_db (code, db_description, link_type) VALUES
--     ('P1', 'ACS Total Population', 'subject'),
--     ('B25003A', 'Tenure (White Alone Householder)', 'housing'),
--     ('B25003B', 'Tenure (Black or African American Alone Householder)', 'housing'),
--     ('B25003C', 'Tenure (American Indian and Alaska Native Alone Householder)', 'housing'),
--     ('B25003D', 'Tenure (Asian Alone Householder)', 'housing'),
--     ('B25003E', 'Tenure (Native Hawaiian and Other Pacific Islander Alone Householder)', 'housing'),
--     ('B25003F', 'Tenure (Some Other Race Alone Householder)', 'housing'),
--     ('B25003G', 'Tenure (Two or More Races Householder)', 'housing'),
--     ('B25003H', 'Tenure (White Alone, Not Hispanic or Latino Householder)', 'housing'),
--     ('B25003I', 'Tenure (Hispanic or Latino Householder)', 'housing'),
--     ('B25007', 'Tenure by Age of Householder', 'housing'),
--     ('B25008', 'Population in Occupied Housing Units by Tenure', 'housing'),
--     ('B25009', 'Tenure by Household Size', 'housing'),
--     ('B25010', 'Average Household Size by Tenure', 'housing'),
--     ('B25011', 'Tenure by Household Type and Age of Householder', 'housing'),
--     ('B25013', 'Tenure by Educational Attainment of Householder', 'housing'),
--     ('B25014', 'Tenure by Occupants per Room', 'housing'),
--     ('B25015', 'Tenure by Age of Householder by Occupants per Room', 'housing'),
--     ('B25016', 'Tenure by Plumbing Facilities by Occupants per Room', 'housing'),
--     ('B25020', 'Tenure by Rooms', 'housing'),
--     ('B25021', 'Median Number of Rooms by Tenure', 'housing'),
--     ('B25022', 'Aggregate Number of Rooms by Tenure', 'housing'),
--     ('B25026', 'Population in Occupied Units by Tenure by Year Moved In', 'housing'),
--     ('B25032', 'Tenure by Units in Structure', 'housing'),
--     ('B25033', 'Population in Occupied Units by Tenure by Units in Structure', 'housing'),
--     ('B25036', 'Tenure by Year Structure Built', 'housing'),
--     ('B25037', 'Median Year Structure Built by Tenure', 'housing'),
--     ('B25038', 'Tenure by Year Householder Moved Into Unit', 'housing'),
--     ('B25039', 'Median Year Householder Moved In by Tenure', 'housing'),
--     ('B25042', 'Tenure by Bedrooms', 'housing'),
--     ('B25043', 'Telephone Service by Tenure and Age', 'housing'),
--     ('B25045', 'Tenure by Vehicles Available by Age of Householder', 'housing'),
--     ('B25046', 'Aggregate Vehicles Available by Tenure', 'housing'),
--     ('B25076', 'Lower Value Quartile (Dollars)', 'housing'),
--     ('B25078', 'Upper Value Quartile (Dollars)', 'housing'),
--     ('B25079', 'Aggregate Value by Age of Householder', 'housing'),
--     ('B25080', 'Aggregate Value by Units in Structure', 'housing'),
--     ('B25094', 'Selected Monthly Owner Costs', 'housing'),
--     ('B25096', 'Mortgage Status by Value', 'housing'),
--     ('B25097', 'Mortgage Status by Median Value', 'housing'),
--     ('B25106', 'Housing Costs as % of Income by Tenure', 'housing'),
--     ('B25107', 'Median Value by Year Structure Built', 'housing'),
	-- ('B25108', 'Aggregate Value (Dollars) by Year Structure Built', 'housing'),
	-- ('B25109', 'Median Value by Year Householder Moved Into Unit', 'housing'),
	-- ('B25110', 'Aggregate Value (Dollars) by Year Householder Moved Into Unit', 'housing'),
	-- ('B25111', 'Median Gross Rent by Year Structure Built', 'housing'),
	-- ('B25112', 'Aggregate Gross Rent (Dollars) by Year Structure Built', 'housing'),
	-- ('B25113', 'Median Gross Rent by Year Householder Moved Into Unit', 'housing'),
	-- ('B25114', 'Aggregate Gross Rent (Dollars) by Year Householder Moved Into Unit', 'housing'),
	-- ('B25115', 'Tenure by Household Type and Presence and Age of Own Children', 'housing'),
	-- ('B25116', 'Tenure by Household Size by Age of Householder', 'housing'),
	-- ('B25117', 'Tenure by House Heating Fuel', 'housing'),
	-- ('B25118', 'Tenure by Household Income in the Past 12 Months (in 2024 Inflation-Adjusted Dollars)', 'housing'),
	-- ('B25119', 'Median Household Income in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) by Tenure', 'housing'),
	-- ('B25120', 'Aggregate Household Income in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) by Tenure and Mortgage Status', 'housing'),
	-- ('B25123', 'Tenure by Selected Physical and Financial Conditions', 'housing'),
	-- ('B25124', 'Tenure by Household Size by Units in Structure', 'housing'),
	-- ('B25125', 'Tenure by Age of Householder by Units in Structure', 'housing'),
	-- ('B25126', 'Tenure by Age of Householder by Year Structure Built', 'housing'),
	-- ('B25127', 'Tenure by Year Structure Built by Units in Structure', 'housing'),
	-- ('B25128', 'Tenure by Age of Householder by Year Householder Moved Into Unit', 'housing'),
	-- ('B25129', 'Tenure by Year Householder Moved Into Unit by Units in Structure', 'housing'),
	-- ('B99252', 'Allocation of Tenure', 'housing');



-- -- -- other data
-- INSERT INTO world_sim_census.code_to_db (code, db_description, link_type) VALUES
-- 	('S0102', 's0102_population_60_over_us', 'Population 60 Years and Over in the United States', 'subject'),
-- 	('S0103', 's0103_population_65_over_us', 'Population 65 Years and Over in the United States', 'subject'),
-- 	('S0501', 's0501_native_foreign_born_characteristics', 'Selected Characteristics of the Native and Foreign-Born Populations', 'subject'),
-- 	('S0502', 's0502_foreign_born_period_entry_us', 'Selected Characteristics of the Foreign-Born Population by Period of Entry Into the United States', 'subject'),
-- 	('S0503', 's0503_foreign_born_region_birth_europe', 'Selected Characteristics of the Foreign-Born Population by Region of Birth: Europe', 'subject'),
-- 	('S0504', 's0504_foreign_born_region_birth_africa_na_oceania', 'Selected Characteristics of the Foreign-Born Population by Region of Birth: Africa, Northern America, and Oceania', 'subject'),
-- 	('S0505', 's0505_foreign_born_region_birth_asia', 'Selected Characteristics of the Foreign-Born Population by Region of Birth: Asia', 'subject'),
-- 	('S0506', 's0506_foreign_born_region_birth_latam', 'Selected Characteristics of the Foreign-Born Population by Region of Birth: Latin America', 'subject'),
-- 	('S0601', 's0601_total_native_characteristics_us', 'Selected Characteristics of the Total and Native Populations in the United States', 'subject'),
-- 	('S0701', 's0701_geographic_mobility_us', 'Geographic Mobility by Selected Characteristics in the United States', 'subject'),
-- 	('S0702', 's0702_movers_between_regions', 'Movers Between Regions', 'subject'),
-- 	('S0801', 's0801_commuting_characteristics_sex', 'Commuting Characteristics by Sex', 'subject'),
-- 	('S0802', 's0802_transportation_work_characteristics', 'Means of Transportation to Work by Selected Characteristics', 'subject'),
-- 	('S0804', 's0804_transportation_workplace_geography', 'Means of Transportation to Work by Selected Characteristics for Workplace Geography', 'subject'),
-- 	('S0901', 's0901_children_characteristics', 'Children Characteristics', 'subject'),
-- 	('S0902', 's0902_teenagers_15_19_characteristics', 'Characteristics of Teenagers 15 to 19 Years Old', 'subject'),
-- 	('S1001', 's1001_grandchildren_characteristics', 'Grandchildren Characteristics', 'subject'),
-- 	('S1002', 's1002_grandparents', 'Grandparents', 'subject'),
-- 	('S1101', 's1101_households_families', 'Households and Families', 'subject'),
-- 	('S1201', 's1201_marital_status', 'Marital Status', 'subject'),
-- 	('S1251', 's1251_recent_marital_event_people', 'Characteristics of People With a Marital Event in the Last 12 Months', 'subject'),
-- 	('S1301', 's1301_fertility', 'Fertility', 'subject'),
-- 	('S1401', 's1401_school_enrollment', 'School Enrollment', 'subject'),
-- 	('S1502', 's1502_bachelors_degree_field', 'Field of Bachelors Degree for First Major', 'subject'),
-- 	('S1601', 's1601_language_home', 'Language Spoken at Home', 'subject'),
-- 	('S1602', 's1602_limited_english_households', 'Limited English Speaking Households', 'subject'),
-- 	('S1603', 's1603_characteristics_by_language', 'Characteristics of People by Language Spoken at Home', 'subject'),
-- 	('S1702', 's1702_family_poverty_status', 'Poverty Status in the Past 12 Months of Families', 'subject'),
-- 	('S1703', 's1703_selected_poverty_characteristics', 'Selected Characteristics of People at Specified Levels of Poverty in the Past 12 Months', 'subject'),
-- 	('S1810', 's1810_disability_characteristics', 'Disability Characteristics', 'subject'),
-- 	('S1811', 's1811_economic_char_by_disability', 'Selected Economic Characteristics for the Civilian Noninstitutionalized Population by Disability Status', 'subject'),
-- 	('S1902', 's1902_mean_income_last_12mo', 'Mean Income in the Past 12 Months (in 2024 Inflation-Adjusted Dollars)', 'subject'),
-- 	('S1903', 's1903_median_income_last_12mo', 'Median Income in the Past 12 Months (in 2024 Inflation-Adjusted Dollars)', 'subject'),
-- 	('S2001', 's2001_earnings_last_12mo', 'Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars)', 'subject'),
-- 	('S2002', 's2002_median_earnings_gender', 'Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) of Workers by Sex and Womens Earnings as a Percentage of Mens Earnings by Selected Characteristics', 'subject'),
-- 	('S2101', 's2101_veteran_status', 'Veteran Status', 'subject'),
-- 	('S2201', 's2201_snap_food_stamps', 'Food Stamps/Supplemental Nutrition Assistance Program (SNAP)', 'subject'),
-- 	('S2301', 's2301_employment_status', 'Employment Status', 'subject'),
-- 	('S2302', 's2302_employment_characteristics_families', 'Employment Characteristics of Families', 'subject'),
-- 	('S2303', 's2303_work_status_last_12mo', 'Work Status in the Past 12 Months', 'subject'),
-- 	('S2401', 's2401_occupation_sex_employed_16plus', 'Occupation by Sex for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2402', 's2402_occupation_sex_fulltime_yearround', 'Occupation by Sex for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2403', 's2403_industry_sex_employed_16plus', 'Industry by Sex for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2404', 's2404_industry_sex_fulltime_yearround', 'Industry by Sex for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2405', 's2405_industry_by_occupation_employed_16plus', 'Industry by Occupation for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2406', 's2406_occupation_by_worker_class_employed_16plus', 'Occupation by Class of Worker for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2407', 's2407_industry_by_worker_class_employed_16plus', 'Industry by Class of Worker for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2408', 's2408_worker_class_by_sex_employed_16plus', 'Class of Worker by Sex for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2409', 's2409_worker_class_by_sex_fulltime_yearround', 'Class of Worker by Sex for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2411', 's2411_occupation_sex_median_earnings_16plus', 'Occupation by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2412', 's2412_occupation_sex_median_earnings_fulltime_yearround', 'Occupation by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2413', 's2413_industry_sex_median_earnings_16plus', 'Industry by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2414', 's2414_industry_sex_median_earnings_fulltime_yearround', 'Industry by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2418', 's2418_worker_class_sex_median_earnings_16plus', 'Class of Worker by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2419', 's2419_worker_class_sex_median_earnings_fulltime_yearround', 'Class of Worker by Sex and Median Earnings in the Past 12 Months (in 2024 Inflation-Adjusted Dollars) for the Full-Time, Year-Round Civilian Employed Population 16 Years and Over', 'subject'),
-- 	('S2501', 's2501_occupancy_characteristics', 'Occupancy Characteristics', 'subject'),
-- 	('S2502', 's2502_demographic_characteristics_occupied_housing', 'Demographic Characteristics for Occupied Housing Units', 'subject'),
-- 	('S2503', 's2503_financial_characteristics', 'Financial Characteristics', 'subject'),
-- 	('S2504', 's2504_physical_housing_characteristics_occupied', 'Physical Housing Characteristics for Occupied Housing Units', 'subject'),
-- 	('S2506', 's2506_financial_characteristics_housing_with_mortgage', 'Financial Characteristics for Housing Units With a Mortgage', 'subject'),
-- 	('S2507', 's2507_financial_characteristics_housing_without_mortgage', 'Financial Characteristics for Housing Units Without a Mortgage', 'subject'),
-- 	('S2601A', 's2601_group_quarters_population_a_us', 'Characteristics of the Group Quarters Population in the United States', 'subject'),
-- 	('S2601C', 's2601_group_quarters_population_c_us', 'Characteristics of the Group Quarters Population in the United States', 'subject'),
-- 	('S2602', 's2602_group_quarters_population_3types', 'Characteristics of the Group Quarters Population by Group Quarters Type (3 Types)', 'subject'),
-- 	('S2603', 's2603_group_quarters_population_5types', 'Characteristics of the Group Quarters Population by Group Quarters Type (5 Types)', 'subject'),
-- 	('S2701', 's2701_health_insurance_coverage_us', 'Selected Characteristics of Health Insurance Coverage in the United States', 'subject'),
-- 	('S2702', 's2702_uninsured_characteristics_us', 'Selected Characteristics of the Uninsured in the United States', 'subject'),
-- 	('S2704', 's2704_public_health_insurance_type_characteristics', 'Public Health Insurance Coverage by Type and Selected Characteristics', 'subject'),
-- 	('S2801', 's2801_computers_internet', 'Types of Computers and Internet Subscriptions', 'subject'),
-- 	('S2802', 's2802_internet_subscriptions_characteristics', 'Types of Internet Subscriptions by Selected Characteristics', 'subject'),
-- 	('S2901', 's2901_citizen_voting_age_population', 'Citizen, Voting-Age Population by Selected Characteristics', 'subject');





-- -- american community survey information
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200101', 'population_by_sex', 'Population by Sex', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200102', 'population_under_18_by_age', 'Population Under 18 Years by Age', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200103', 'median_age_by_sex', 'Median Age by Sex', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200104', 'population_by_age', 'Population by Age', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200201', 'population_by_race', 'Race', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200301', 'hispanic_latino_origin', 'Hispanic or Latino Origin', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200501', 'citizenship_status_us', 'Citizenship Status in the United States', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200503', 'place_of_birth_us', 'Place of Birth in the United States', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200701', 'geographical_mobility_us', 'Geographical Mobility in the Past Year in the United States', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200801', 'means_of_transportation', 'Means of Transportation to Work', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200802', 'travel_time_to_work', 'Travel Time to Work', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200901', 'household_type', 'Household Type', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201001', 'marital_status_over_15', 'Marital Status for the Population 15 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201101', 'own_children_under_18', 'Own Children Under 18 Years by Family Type', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201102', 'households_with_persons_over_60', 'Households by Presence of People 60 Years and Over by Household Type', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201401', 'school_enrollment_by_level', 'School Enrollment by Level of School for the Population 3 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201501', 'educational_attainment_over_25', 'Educational Attainment for the Population 25 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201601', 'household_language', 'Household Language', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201701', 'poverty_status_by_age', 'Poverty Status in the Past 12 Months by Age', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201702', 'ratio_income_to_poverty', 'Ratio of Income to Poverty Level in the Past 12 Months', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201703', 'poverty_status_families_by_household', 'Poverty Status in the Past 12 Months of Families by Household Type', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201801', 'disability_status_by_age', 'Disability Status by Age', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201802', 'work_experience_by_disability', 'Work Experience by Disability Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201803', 'types_of_disabilities', 'Types of Disabilities', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201901', 'household_income_last_12mo', 'Household Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201902', 'median_household_income_last_12mo', 'Median Household Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201903', 'family_income_last_12mo', 'Family Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201904', 'median_family_income_last_12mo', 'Median Family Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201905', 'median_nonfamily_household_income_last_12mo', 'Median Nonfamily Household Income in the Past 12 Months (in 2023 Inflation-Adjusted Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202002', 'median_earnings_by_sex_and_work_experience', 'Median Earnings in the Past 12 Months (in 2023 Inflation-Adjusted Dollars) by Sex by Work Experience in the Past 12 Months for the Population 16 Years and Over With Earnings in the Past 12 Months', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202101', 'veteran_status_by_age', 'Veteran Status for the Civilian Population 18 Years and Over by Age', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202102', 'service_connected_disability_status_veterans', 'Service-Connected Disability-Rating Status for Civilian Veterans 18 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202201', 'food_stamp_receipt_with_children', 'Receipt of Food Stamps/SNAP in the Past 12 Months by Presence of Children Under 18 Years for Households', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202301', 'employment_status_over_16', 'Employment Status for the Population 16 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202302', 'sex_by_fulltime_work_status_16_to_64', 'Sex by Full-Time Work Status in the Past 12 Months for the Population 16 to 64 Years', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202401', 'occupation_civilian_employed_16plus', 'Occupation for the Civilian Employed Population 16 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202402', 'class_of_worker_civilian_employed_16plus', 'Class of Worker for the Civilian Employed Population 16 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202403', 'industry_civilian_employed_16plus', 'Industry for the Civilian Employed Population 16 Years and Over', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202501', 'occupancy_status', 'Occupancy Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202502', 'housing_tenure', 'Housing Tenure', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202503', 'population_in_occupied_units_by_tenure', 'Total Population in Occupied Housing Units by Tenure', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202504', 'units_in_structure', 'Units in Structure', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202505', 'year_structure_built', 'Year Structure Built', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202506', 'year_householder_moved_in', 'Year Householder Moved Into Unit', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202507', 'gross_rent', 'Gross Rent', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202508', 'mortgage_status', 'Mortgage Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202509', 'housing_value', 'Housing Value', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202510', 'median_housing_value', 'Median Value (Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202511', 'median_gross_rent', 'Median Gross Rent (Dollars)', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202601', 'group_quarters_population', 'Group Quarters Population', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202701', 'age_by_health_insurance_coverage', 'Age by Health Insurance Coverage Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202702', 'private_health_insurance_status', 'Private Health Insurance Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202703', 'public_health_insurance_status', 'Public Health Insurance Status', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202801', 'computer_and_internet_access', 'Presence of a Computer and Type of Internet Subscription in Household', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K209801', 'unweighted_housing_unit_sample', 'Unweighted Housing Unit Sample', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K209803', 'unweighted_total_population_sample', 'Unweighted Total Population Sample', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200001', 'unweighted_population_sample_count', 'UNWEIGHTED SAMPLE COUNT OF THE POPULATION', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K200002', 'unweighted_housing_units', 'UNWEIGHTED SAMPLE HOUSING UNITS', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K201906', 'median_income_by_sex_work_experience', 'MEDIAN INCOME IN THE PAST 12 MONTHS (IN 2014 INFLATION-ADJUSTED DOLLARS) BY SEX BY WORK EXPERIENCE IN THE PAST 12 MONTHS FOR THE POPULATION 15 YEARS AND OVER WITH INCOME 2014: ACS 1-Year Supplemental Estimates', 'profile');
-- INSERT INTO world_sim_census.code_to_db (code, db_name, db_description, link_type) VALUES ('K202001', 'earnings_past_12_months', 'EARNINGS IN THE PAST 12 MONTHS (IN 2014 INFLATION-ADJUSTED DOLLARS) FOR THE POPULATION 16 YEARS AND OVER WITH EARNINGS IN THE PAST 12 MONTHS 2014: ACS 1-Year Supplemental Estimates', 'profile');

