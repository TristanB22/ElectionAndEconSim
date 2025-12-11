-- world sim conversations and channels database schema

-- drop and create the database
DROP DATABASE IF EXISTS world_sim_conversations;
CREATE DATABASE world_sim_conversations CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- conversation tables

DROP TABLE IF EXISTS conversation_commitments;
DROP TABLE IF EXISTS world_sim_conversations.conversation_turns;
DROP TABLE IF EXISTS world_sim_conversations.conversations;
DROP TABLE IF EXISTS world_sim_conversations.channels;
DROP TABLE IF EXISTS world_sim_conversations.channel_usage;
DROP TABLE IF EXISTS world_sim_conversations.knowledge_entities;
DROP TABLE IF EXISTS world_sim_conversations.knowledge_roles;
DROP TABLE IF EXISTS world_sim_conversations.opinions_people;
DROP TABLE IF EXISTS world_sim_conversations.opinions_places;

CREATE TABLE world_sim_conversations.conversations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL,
    agent_a_id VARCHAR(255) NOT NULL,
    agent_b_id VARCHAR(255) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    status ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    context JSON,
    summary TEXT,
    trust_delta_a DECIMAL(5,4) DEFAULT 0.0,
    trust_delta_b DECIMAL(5,4) DEFAULT 0.0,
    relationship_delta_a DECIMAL(5,4) DEFAULT 0.0,
    relationship_delta_b DECIMAL(5,4) DEFAULT 0.0,
    PRIMARY KEY (id),
    UNIQUE KEY unique_conversation (conversation_id),
    INDEX idx_sim_agents (simulation_id, agent_a_id, agent_b_id),
    INDEX idx_channel (channel_id),
    INDEX idx_status (status),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.conversation_turns (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    conversation_id VARCHAR(255) NOT NULL,
    turn_number INT NOT NULL,
    speaker_id VARCHAR(255) NOT NULL,
    message_text TEXT NOT NULL,
    message_type ENUM('text', 'action', 'commitment') DEFAULT 'text',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    PRIMARY KEY (id),
    INDEX idx_conversation_turn (conversation_id, turn_number),
    INDEX idx_speaker (speaker_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.conversation_commitments (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    conversation_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    commitment_text TEXT NOT NULL,
    due_time TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('open','kept','broken','cancelled') DEFAULT 'open',
    PRIMARY KEY (id),
    INDEX idx_conv (conversation_id),
    INDEX idx_agent (agent_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);




---- channel tables

CREATE TABLE world_sim_conversations.channels (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    topology ENUM('dm', 'feed', 'event') NOT NULL,
    targeting JSON,
    costs JSON,
    friction JSON,
    credibility_baseline DECIMAL(5,4) DEFAULT 0.5,
    latency_s INT DEFAULT 0,
    caps JSON,
    diffusion JSON,
    status ENUM('active', 'inactive', 'prototype') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    PRIMARY KEY (id),
    UNIQUE KEY unique_channel (channel_id),
    INDEX idx_sim_status (simulation_id, status),
    INDEX idx_topology (topology),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.channel_usage (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    channel_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    action_type ENUM('post', 'dm', 'organize_event') NOT NULL,
    target_id VARCHAR(255),
    content TEXT,
    metadata JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_sim_channel (simulation_id, channel_id),
    INDEX idx_agent (agent_id),
    INDEX idx_action (action_type),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

-- innovation tables

DROP TABLE IF EXISTS world_sim_conversations.innovation_ideas;
DROP TABLE IF EXISTS world_sim_conversations.innovation_prototypes;

CREATE TABLE world_sim_conversations.innovation_ideas (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    idea_id VARCHAR(255) NOT NULL,
    proposer_id VARCHAR(255) NOT NULL,
    artifact_type ENUM('media_channel', 'platform', 'organization', 'product', 'protocol', 'meme') NOT NULL,
    concept TEXT NOT NULL,
    target_users JSON,
    affordances JSON,
    status ENUM('proposed', 'prototyping', 'evaluating', 'published', 'rejected') DEFAULT 'proposed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY unique_idea (idea_id),
    INDEX idx_sim_proposer (simulation_id, proposer_id),
    INDEX idx_artifact_type (artifact_type),
    INDEX idx_status (status),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.innovation_prototypes (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    idea_id VARCHAR(255) NOT NULL,
    prototype_id VARCHAR(255) NOT NULL,
    channel_spec JSON NOT NULL,
    usage_count INT DEFAULT 0,
    retention_rate DECIMAL(5,4) DEFAULT 0.0,
    evaluation_score DECIMAL(5,4) DEFAULT 0.0,
    status ENUM('active', 'evaluating', 'published', 'killed') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP NULL,
    PRIMARY KEY (id),
    UNIQUE KEY unique_prototype (prototype_id),
    INDEX idx_idea (idea_id),
    INDEX idx_status (status),
    FOREIGN KEY (idea_id) REFERENCES innovation_ideas(idea_id) ON DELETE CASCADE
);



-- tables for the knowledge and opinions of the agents

CREATE TABLE world_sim_conversations.knowledge_entities (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    kind ENUM('place','firm','person','channel','role','product') NOT NULL,
    source VARCHAR(64) NOT NULL,
    confidence DECIMAL(5,4) DEFAULT 0.5,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    attrs JSON,
    PRIMARY KEY (id),
    INDEX idx_sim_agent (simulation_id, agent_id),
    INDEX idx_entity (entity_id),
    INDEX idx_kind (kind),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.knowledge_roles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    person_id VARCHAR(255) NOT NULL,
    role_name VARCHAR(255) NOT NULL,
    confidence DECIMAL(5,4) DEFAULT 0.5,
    source VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_sim_agent (simulation_id, agent_id),
    INDEX idx_person (person_id),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.opinions_people (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    person_id VARCHAR(255) NOT NULL,
    trust DECIMAL(5,4) DEFAULT 0.5,
    liking DECIMAL(5,4) DEFAULT 0.5,
    last_interaction TIMESTAMP NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_row (simulation_id, agent_id, person_id),
    INDEX idx_sim_agent (simulation_id, agent_id),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);

CREATE TABLE world_sim_conversations.opinions_places (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    simulation_id VARCHAR(64) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    place_id VARCHAR(255) NOT NULL,
    category VARCHAR(64) DEFAULT 'unknown',
    satisfaction DECIMAL(5,4) DEFAULT 0.0,
    last_visit TIMESTAMP NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uniq_row (simulation_id, agent_id, place_id),
    INDEX idx_sim_agent (simulation_id, agent_id),
    FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id) ON DELETE CASCADE
);
