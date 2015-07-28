-- this schema sql will destroy all data in database
BEGIN TRANSACTION;

DROP TABLE IF EXISTS users;
CREATE TABLE users
(
	id VARCHAR PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	password VARCHAR(50) NOT NULL,
	admin INTEGER,
	created_at INTEGER NOT NULL,
	seq INTEGER
);

--add initial user
INSERT INTO users(id, name, password, admin, created_at)VALUES("8b523253-d12b-4901-b3e8-c5bc7dff100d", "admin", "admin", 1, 1437453425);

DROP TABLE IF EXISTS arrays;
CREATE TABLE arrays
(
	id VARCHAR(50) PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	device VARCHAR(50) NOT NULL,
	level INTEGER NOT NULL,
	capacity BIGINT NOT NULL,
	chunk_size INTEGER NOT NULL,
	created_at INTEGER NOT NULL,
	state INTEGER
);

DROP TABLE IF EXISTS disks;
CREATE TABLE disks
(
	id VARCHAR(50) PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	state INTEGER,
	array_id VARCHAR(50),
	slot INTEGER
);

DROP TABLE IF EXISTS pvs;
CREATE TABLE pvs
(
	id VARCHAR(50) PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	uuid VARCHAR(50) NOT NULL,
	vg_name VARCHAR(50),
	state INTEGER
);

DROP TABLE IF EXISTS vgs;
CREATE TABLE vgs
(
	id VARCHAR(50) PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	state INTEGER,
	size BIGINT
);

DROP TABLE IF EXISTS lvms;
CREATE TABLE lvms
(
	id VARCHAR(50) PRIMARY KEY,
	name VARCHAR(50) NOT NULL,
	path VARCHAR(50) NOT NULL,
	vg_name VARCHAR(50) NOT NULL,
	state INTEGER,
	size BIGINT
);

COMMIT;
