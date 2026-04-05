-- L2 Political Table 1
DROP TABLE IF EXISTS world_sim_agents.l2_political_part_1;

CREATE TABLE IF NOT EXISTS world_sim_agents.l2_political_part_1 (
    LALVOTERID VARCHAR(64) PRIMARY KEY,
    `ConsumerData_Single_Parent_in_Household` VARCHAR(1) NULL,
    `ConsumerData_African_American_Professional_in_Household` VARCHAR(1) NULL,
    `Parties_Description` VARCHAR(50) NULL,
    `VoterParties_Change_Changed_Party` VARCHAR(255) NULL,
    `ConsumerData_Moderate_Republican_Flag` VARCHAR(1) NULL,
    `ConsumerData_Moderate_Republican_Score` VARCHAR(10) NULL,
    `ConsumerData_Conservative_Republican_Flag` VARCHAR(1) NULL,
    `ConsumerData_Conservative_Republican_Score` VARCHAR(10) NULL,
    `ConsumerData_Likely_to_Vote_for_3rd_Party_or_Republican_Flag` VARCHAR(1) NULL,
    `ConsumerData_Likely_to_Vote_for_3rd_Party_or_Republican_Score` VARCHAR(10) NULL,
    `County_Commissioner_District` TEXT NULL,
    `County_Supervisorial_District` TEXT NULL,
    `Precinct` TEXT NULL,
    `District_Attorney` TEXT NULL,
    `US_Congressional_District` TEXT NULL,
    `State_Senate_District` TEXT NULL,
    `State_House_District` TEXT NULL,
    `State_Legislative_District` TEXT NULL,
    `Borough_Ward` TEXT NULL,
    `City_Council_Commissioner_District` TEXT NULL,
    `City_Mayoral_District` TEXT NULL,
    `City_Ward` TEXT NULL,
    `Proposed_City_Commissioner_District` TEXT NULL,
    `Town_District` TEXT NULL,
    `Town_Ward` TEXT NULL,
    `Township_Ward` TEXT NULL,
    `Village_Ward` TEXT NULL,
    `Judicial_Appellate_District` TEXT NULL,
    `Judicial_Chancery_Court` TEXT NULL,
    `Judicial_Circuit_Court_District` TEXT NULL,
    `Judicial_County_Board_of_Review_District` TEXT NULL,
    `Judicial_County_Court_District` TEXT NULL,
    `Judicial_District` TEXT NULL,
    `Judicial_District_Court_District` TEXT NULL,
    `Judicial_Family_Court_District` TEXT NULL,
    `Judicial_Jury_District` TEXT NULL,
    `Judicial_Juvenile_Court_District` TEXT NULL,
    `Judicial_Municipal_Court_District` TEXT NULL,
    `Judicial_Sub_Circuit_District` TEXT NULL,
    `Judicial_Superior_Court_District` TEXT NULL,
    `Judicial_Supreme_Court_District` TEXT NULL,
    `City_School_District` TEXT NULL,
    `College_Board_District` TEXT NULL,
    `Community_College_Commissioner_District` TEXT NULL,
    `Community_College_SubDistrict` TEXT NULL,
    `County_Board_of_Education_District` TEXT NULL,
    `County_Board_of_Education_SubDistrict` TEXT NULL,
    `County_Community_College_District` TEXT NULL,
    `County_Superintendent_of_Schools_District` TEXT NULL,
    `County_Unified_School_District` TEXT NULL,
    `Education_Commission_District` TEXT NULL,
    `Educational_Service_District` TEXT NULL,
    `Elementary_School_District` TEXT NULL,
    `Elementary_School_SubDistrict` TEXT NULL,
    `Exempted_Village_School_District` TEXT NULL,
    `High_School_District` TEXT NULL,
    `High_School_SubDistrict` TEXT NULL,
    `Proposed_Elementary_School_District` TEXT NULL,
    `Proposed_Unified_School_District` TEXT NULL,
    `Regional_Office_of_Education_District` TEXT NULL,
    `School_Board_District` TEXT NULL,
    `School_District` TEXT NULL,
    `School_District_Vocational` TEXT NULL,
    `School_Facilities_Improvement_District` TEXT NULL,
    `Superintendent_of_Schools_District` TEXT NULL,
    `Unified_School_District` TEXT NULL,
    `Unified_School_SubDistrict` TEXT NULL,
    `c_2024_Proposed_Congressional_District` TEXT NULL,
    `c_2024_Proposed_State_Senate_District` TEXT NULL,
    `c_2024_Proposed_State_House_District` TEXT NULL,
    `c_2024_Proposed_State_Legislative_District` TEXT NULL,
    `c_2001_US_Congressional_District` TEXT NULL,
    `c_2001_State_House_District` TEXT NULL,
    `c_2001_State_Legislative_District` TEXT NULL,
    `c_2001_State_Senate_District` TEXT NULL,
    `c_2010_US_Congressional_District` TEXT NULL,
    `c_2010_State_House_District` TEXT NULL,
    `c_2010_State_Legislative_District` TEXT NULL,
    `c_2010_State_Senate_District` TEXT NULL,
    `c_4H_Livestock_District` TEXT NULL,
    `Airport_District` TEXT NULL,
    `Annexation_District` TEXT NULL,
    `Aquatic_Center_District` TEXT NULL,
    `Aquatic_District` TEXT NULL,
    `Assessment_District` TEXT NULL,
    `Board_of_Education_District` TEXT NULL,
    `Board_of_Education_SubDistrict` TEXT NULL,
    `Bonds_District` TEXT NULL,
    `Cemetery_District` TEXT NULL,
    `Central_Committee_District` TEXT NULL,
    `Chemical_Control_District` TEXT NULL,
    `Coast_Water_District` TEXT NULL,
    `Committee_Super_District` TEXT NULL,
    `Communications_District` TEXT NULL,
    `Community_Council_District` TEXT NULL,
    `Community_Council_SubDistrict` TEXT NULL,
    `Community_Facilities_District` TEXT NULL,
    `Community_Facilities_SubDistrict` TEXT NULL,
    `Community_Hospital_District` TEXT NULL,
    `Community_Service_District` TEXT NULL,
    `Community_Service_SubDistrict` TEXT NULL,
    `Congressional_Township` TEXT NULL,
    `Conservation_District` TEXT NULL,
    `Conservation_SubDistrict` TEXT NULL,
    `Consolidated_Water_District` TEXT NULL,
    `Control_Zone_District` TEXT NULL,
    `Corrections_District` TEXT NULL,
    `County_Fire_District` TEXT NULL,
    `County_Hospital_District` TEXT NULL,
    `County_Legislative_District` TEXT NULL,
    `County_Library_District` TEXT NULL,
    `County_Memorial_District` TEXT NULL,
    `County_Paramedic_District` TEXT NULL,
    `County_Service_Area_SubDistrict` TEXT NULL,
    `County_Sewer_District` TEXT NULL,
    `County_Water_District` TEXT NULL,
    `County_Water_Landowner_District` TEXT NULL,
    `County_Water_SubDistrict` TEXT NULL,
    `Democratic_Convention_Member` TEXT NULL,
    `Democratic_Zone` TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;





-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Commissioner_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Supervisorial_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Precinct TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN District_Attorney TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN US_Congressional_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN State_Senate_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN State_House_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN State_Legislative_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Borough_Ward TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN City_Council_Commissioner_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN City_Mayoral_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN City_Ward TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Proposed_City_Commissioner_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Town_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Town_Ward TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Township_Ward TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Village_Ward TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Appellate_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Chancery_Court TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Circuit_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_County_Board_of_Review_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_County_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_District_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Family_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Jury_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Juvenile_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Municipal_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Sub_Circuit_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Superior_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Judicial_Supreme_Court_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN City_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN College_Board_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_College_Commissioner_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_College_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Board_of_Education_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Board_of_Education_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Community_College_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Superintendent_of_Schools_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Unified_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Education_Commission_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Educational_Service_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Elementary_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Elementary_School_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Exempted_Village_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN High_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN High_School_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Proposed_Elementary_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Proposed_Unified_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Regional_Office_of_Education_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN School_Board_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN School_District_Vocational TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN School_Facilities_Improvement_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Superintendent_of_Schools_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Unified_School_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Unified_School_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2024_Proposed_Congressional_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2024_Proposed_State_Senate_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2024_Proposed_State_House_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2024_Proposed_State_Legislative_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2001_US_Congressional_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2001_State_House_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2001_State_Legislative_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2001_State_Senate_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2010_US_Congressional_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2010_State_House_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2010_State_Legislative_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_2010_State_Senate_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN c_4H_Livestock_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Airport_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Annexation_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Aquatic_Center_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Aquatic_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Assessment_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Board_of_Education_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Board_of_Education_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Bonds_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Cemetery_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Central_Committee_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Chemical_Control_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Coast_Water_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Committee_Super_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Communications_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Council_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Council_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Facilities_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Facilities_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Hospital_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Service_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Community_Service_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Congressional_Township TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Conservation_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Conservation_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Consolidated_Water_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Control_Zone_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Corrections_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Fire_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Hospital_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Legislative_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Library_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Memorial_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Paramedic_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Service_Area_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Sewer_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Water_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Water_Landowner_District TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN County_Water_SubDistrict TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Democratic_Convention_Member TEXT;
-- ALTER TABLE world_sim_agents.l2_political_part_1 MODIFY COLUMN Democratic_Zone TEXT;