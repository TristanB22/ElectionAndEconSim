-- agent data core table

DROP TABLE IF EXISTS world_sim_agents.l2_agent_core;

CREATE TABLE l2_agent_core (
    LALVOTERID VARCHAR(64) PRIMARY KEY,
    `SEQUENCE` INT NULL,
    `Voters_StateVoterID` VARCHAR(50) NULL,
    `Voters_CountyVoterID` INT NULL,
    `Voters_FirstName` VARCHAR(255) NULL,
    `Voters_MiddleName` VARCHAR(255) NULL,
    `Voters_LastName` VARCHAR(255) NULL,
    `Voters_NameSuffix` VARCHAR(10) NULL,
    `Voters_SequenceZigZag` INT NULL,
    `Voters_SequenceOddEven` INT NULL,
    `Voters_Gender` VARCHAR(1) NULL,
    `Voters_Age` INT NULL,
    `Voters_BirthDate` DATE NULL,
    `Voters_PlaceOfBirth` VARCHAR(255) NULL,
    `Voters_Active` VARCHAR(1) NULL,
    `Voters_CalculatedRegDate` DATE NULL,
    `Voters_OfficialRegDate` DATE NULL,
    `Voters_FIPS` INT NULL,
    `Voters_MovedFrom_Date` DATE NULL,
    `Voters_MovedFrom_State` VARCHAR(255) NULL,
    `Voters_MovedFrom_Party_Description` VARCHAR(255) NULL,
    `Voters_MovedFrom_VotingPerformanceEvenYearGeneralAndPrimary` VARCHAR(255) NULL,
    `Voters_MovedFrom_VotingPerformanceEvenYearGeneral` VARCHAR(255) NULL,
    `Voters_MovedFrom_VotingPerformanceEvenYearPrimary` VARCHAR(255) NULL,
    `Voters_MovedFrom_VotingPerformanceMinorElection` VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
