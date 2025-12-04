-- make the tables that we want to work with
-- this file contains exclusively logic for the main agents table
DROP TABLE IF EXISTS world_sim_agents.agent_personal_summaries;
DROP TABLE IF EXISTS world_sim_agents.agents;

-- create the main agents table
CREATE TABLE IF NOT EXISTS world_sim_agents.agents (
    l2_voter_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- create the agent personal summaries table
CREATE TABLE IF NOT EXISTS world_sim_agents.agent_personal_summaries (
    agent_id VARCHAR(64) PRIMARY KEY,
    summary_type VARCHAR(100) NOT NULL,
    reasoning TEXT NOT NULL,
    content TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (agent_id) REFERENCES world_sim_agents.agents(l2_voter_id) ON DELETE CASCADE,
    INDEX idx_agent_type (agent_id, summary_type),
    INDEX idx_last_updated (last_updated)
);

