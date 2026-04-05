PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE service (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	is_up BOOLEAN NOT NULL, 
	last_checked_at DATETIME, 
	first_down_at DATETIME, 
	last_alerted_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO service VALUES(1,'Smart Meter','https://smart-meter.syahnurnizam.com',1,'2026-04-05 10:27:45.122126',NULL,NULL,'2026-04-05 07:07:28.142101');
INSERT INTO service VALUES(2,'USMS Scraper','http://127.0.0.1:9200/usms',1,'2026-04-05 10:28:05.834977',NULL,NULL,'2026-04-05 07:16:46.416799');
COMMIT;
