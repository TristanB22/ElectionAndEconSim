-- make the databases that we want to work with

DROP DATABASE IF EXISTS world_sim_agents;
DROP DATABASE IF EXISTS world_sim_firms;
DROP DATABASE IF EXISTS world_sim_simulations;
DROP DATABASE IF EXISTS world_sim_alternative_data;
DROP DATABASE IF EXISTS world_sim_census;

-- create the databases
CREATE DATABASE IF NOT EXISTS world_sim_agents CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS world_sim_firms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS world_sim_simulations CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS world_sim_alternative_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS world_sim_census CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
