-- create table main.report_2021_09_05_2 like main.report_2021_09_05;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN ipOriginId;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN frequency;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN sequenceNumber;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN `source`;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN senderStatus;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN senderDxcc;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN receiverDxcc;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN iMD;
-- ALTER TABLE main.report_2021_09_05_2 DROP COLUMN senderMobileLocator;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX sdx_fss;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX rdx_fss;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX tx_seq;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX rx_seq;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX calltime;
-- ALTER TABLE main.report_2021_09_05_2 DROP INDEX source_rx;
-- ALTER TABLE main.report_2021_09_05_2 DROP PRIMARY KEY;
-- commit;

INSERT INTO main.report_2021_09_05_2 (`senderInfoId`, `receiverInfoId`, `mode`, `sNR`, `flowStartSeconds`, `band`)
select `senderInfoId`, `receiverInfoId`, `mode`, `sNR`, `flowStartSeconds`, `band` from main.report_2021_09_05;

/*Selects for unwanted rows - if > 0 then delete it*/
# SELECT count(*) FROM main.report_2021_09_05 as Tr where Tr.mode != 'FT8' and Tr.mode != 'FT4';
# SELECT count(*) FROM main.report_2021_09_05 as Tr where NOT EXISTS(SELECT 1 FROM main.ft8_stationinfo WHERE ID=Tr.senderInfoId);
# SELECT count(*) FROM main.report_2021_09_05 as Tr where NOT EXISTS(SELECT 1 FROM main.ft8_stationinfo WHERE ID=Tr.receiverInfoId);
# SELECT count(*) FROM main.report_2021_09_05 as Tr where Tr.flowStartSeconds < 1609459200;
# SELECT * FROM main.report_2021_09_05 as Tr where Tr.senderDxcc is null and Tr.receiverDxcc is null;

# DELETE FROM main.report_2021_09_01 as Tr where Tr.mode != 'FT8' and Tr.mode != 'FT4';
# DELETE FROM main.report_2021_09_01 as Tr where NOT EXISTS(SELECT 1 FROM main.ft8_stationinfo WHERE ID=Tr.senderInfoId);
# DELETE FROM main.report_2021_09_01 as Tr where NOT EXISTS(SELECT 1 FROM main.ft8_stationinfo WHERE ID=Tr.receiverInfoId);


SELECT min(FROM_UNIXTIME(Tr.flowStartSeconds)), max(FROM_UNIXTIME(Tr.flowStartSeconds))
FROM main.report_2021_09_05 as Tr 
JOIN ( SELECT at.ituZone as ZoneS, at.id FROM main.ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)
JOIN ( SELECT at.ituZone as ZoneR, at.id FROM main.ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)
where ZoneS = 18 and ZoneR = 30 and Tr.band = '17m';

SET time_zone='+00:00';
SELECT Tr.mode, Tr.sNR, Tr.band, FROM_UNIXTIME(flowStartSeconds), b.callsignS, b.ZoneS, c.callsignR, c.ZoneR
FROM main.report_2021_09_05 as Tr 
JOIN ( SELECT at.callsign AS callsignS, at.ituZone as ZoneS, at.id FROM main.ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)
JOIN ( SELECT at.callsign AS callsignR, at.ituZone as ZoneR, at.id FROM main.ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)
and ZoneS = 1 and ZoneR = 2 and Tr.band = '6m';


SELECT min(FROM_UNIXTIME(flowStartSeconds)), max(FROM_UNIXTIME(flowStartSeconds))
FROM main.report_2021_09_05 as Tr 
JOIN ( SELECT at.ituZone as ZoneS, at.id FROM main.ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)
JOIN ( SELECT at.ituZone as ZoneR, at.id FROM main.ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)
where ZoneS = 5 and ZoneR = 8 and Tr.band = '6m';

SET time_zone='+00:00';
SELECT avg(Tr.sNR), count(Tr.mode) as cnt, Tr.flowStartSeconds, from_unixtime(Tr.flowStartSeconds)
FROM main.report_2021_09_05 as Tr 
JOIN ( SELECT at.ituZone as ZoneS, at.id FROM main.ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)
JOIN ( SELECT at.ituZone as ZoneR, at.id FROM main.ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)
where ZoneS = 1 and ZoneR = 23 and Tr.band = '20m' group by Tr.flowStartSeconds order by Tr.flowStartSeconds;

SET time_zone='+00:00';
SELECT count(Tr.mode)
FROM main.report_2021_09_05 as Tr 
JOIN ( SELECT at.ituZone as ZoneS, at.id FROM main.ft8_stationinfo at) b ON (Tr.senderInfoId = b.id)
JOIN ( SELECT at.ituZone as ZoneR, at.id FROM main.ft8_stationinfo at) c ON (Tr.receiverInfoId = c.id)
where ZoneS = 5 and ZoneR = 8 and Tr.band = '20m';


#SELECT decoderSoftware, count(decoderSoftware) as counts FROM main.stationinfo2021 group by decoderSoftware

#SELECT * FROM main.stationinfo2021 WHERE ID=30573816;
#SELECT * FROM main.stationinfo2020 WHERE ID=30573816;
#SELECT * FROM main.stationinfo2019 WHERE ID=30573816;
#SELECT * FROM main.stationinfo2021 WHERE callsign='SWLJO52';
#SELECT * FROM main.ft8_stationinfo WHERE callsign='SWLJO52';

SELECT min(flowStartSeconds), FROM_UNIXTIME(flowStartSeconds), sNR FROM main.report where flowStartSeconds > 1609459200;

#2021 year = 1609459200
#SELECT count(flowStartSeconds) FROM main.report where flowStartSeconds <= 1630540800;

select id, ituZone FROM main.ft8_stationinfo WHERE callsign='UN7ZO';
#select count(*) FROM main.stationinfo2021 as Ta where Ta.locator is not null and Ta.dxcc_id is not null;

#delete FROM main.ft8_stationinfo;

-- CREATE TABLE `main`.`alt_report-2021_09_01` (
--   `sequenceNumber` bigint NOT NULL,
--   `utc` int unsigned NOT NULL DEFAULT '0',
--   `band` varchar(8) DEFAULT NULL,
--   `zone1` int DEFAULT NULL,
--   `zone2` int DEFAULT NULL
-- ) ENGINE=InnoDB AUTO_INCREMENT=22330779881 DEFAULT CHARSET=latin1 STATS_SAMPLE_PAGES=100


SELECT band, count(*) as cnt FROM main.zone_counts_2021_09_05 group by band order by cnt desc;

# SELECT count(*) FROM main.report_2021_09_05;

