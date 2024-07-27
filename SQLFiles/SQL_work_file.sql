#----------------------------first insert into main callsigns data table from 2022 year----------------------------#
insert into main.ft8_stationinfo (`id`, `callsign`, `dxcc_id`, `grid`, `lastseen`, `ituZone`)
SELECT Ta.id, Ta.callsign, Ta.dxcc_id, LEFT(Ta.locator, 6) as grid, Ta.lastseen, 0 from main.stationinfo2022 as Ta
where Ta.locator is not null and Ta.dxcc_id is not null #and Ta.callsign='JS2CTL' #and Ta.decoderSoftware is not null
#and Ta.id = (select max(Tc.id) from main.stationinfo2022 as Tc where Ta.callsign = Tc.callsign);


#----------------------------first insert into main callsigns data table from 2021 year----------------------------#
# insert into main.ft8_stationinfo (`id`, `callsign`, `dxcc_id`, `grid`, `lastseen`, `ituZone`)
# SELECT Ta.id, Ta.callsign, Ta.dxcc_id, LEFT(Ta.locator, 6) as grid, Ta.lastseen, 0, rate from main.stationinfo2021 as Ta
# where Ta.locator is not null and Ta.dxcc_id is not null #and Ta.callsign='UN7Z' #and Ta.decoderSoftware is not null
 # and Ta.id = (select max(Tc.id) from main.stationinfo2021 as Tc where Ta.callsign = Tc.callsign);




#--------------------second insert into main callsigns data table, only new, non existing callsigns from 2020 year--------------------#
# insert into main.ft8_stationinfo (`id`, `callsign`, `dxcc_id`, `grid`, `lastseen`, `ituZone`)
# SELECT Ta.id, Ta.callsign, Ta.dxcc_id, LEFT(Ta.locator, 6) as grid, Ta.lastseen, 0 from main.stationinfo2020 as Ta
# where Ta.locator is not null and Ta.dxcc_id is not null 
# and NOT EXISTS(SELECT Tc.id FROM main.ft8_stationinfo as Tc WHERE Ta.callsign = Tc.callsign);




#--------------------third insert into main callsigns data table, only new, non existing callsigns from 2019 year--------------------#
# insert into main.ft8_stationinfo (`id`, `callsign`, `dxcc_id`, `grid`, `lastseen`, `ituZone`)
# SELECT Ta.id, Ta.callsign, Ta.dxcc_id, LEFT(Ta.locator, 6) as grid, Ta.lastseen, 0 from main.stationinfo2019 as Ta
# where Ta.locator is not null and Ta.dxcc_id is not null
# and NOT EXISTS(SELECT Tc.id FROM main.ft8_stationinfo as Tc WHERE Ta.callsign = Tc.callsign);







#----------------------------checked counts of callsigns that not exist in another table---------------------------#
# SELECT Ta.callsign, LEFT(Ta.locator, 6) as grid, Ta.lastseen, Ta.dxcc_id from main.stationinfo2021 as Ta
# where Ta.locator is not null and Ta.dxcc_id is not null and Ta.decoderSoftware is not null
# and NOT EXISTS(SELECT * FROM main.stationinfo2020 as Tb WHERE Ta.callsign = Tb.callsign);
#------result: 70672 records exist in 2020-2021, but not in 2019-2020----------------------------------------------#
#------------------------------------------------------------------------------------------------------------------#
# SELECT Ta.callsign, LEFT(Ta.locator, 6) as grid, Ta.lastseen, Ta.dxcc_id from main.stationinfo2020 as Ta
# where Ta.locator is not null and Ta.dxcc_id is not null and Ta.decoderSoftware is not null
# and NOT EXISTS(SELECT * FROM main.stationinfo2021 as Tb WHERE Ta.callsign = Tb.callsign);
#------result: 34852 records exist in 2019-2020, but not in 2020-2021----------------------------------------------#
#------------------------------------------------------------------------------------------------------------------#



--SELECT toYYYYMM(toDateTime(1672272010)) AS column, toTypeName(column) AS x

--SELECT * FROM system.parts_columns




SELECT min(utc) AS minUTC, max(utc) AS maxUTC FROM spots_2023_01;



---# main insert/update script
insert into main.ft8_stationinfo (`id`, `callsign`, `dxcc_id`, `grid`, `lastseen`, `ituZone`)
SELECT Ta.id, Ta.callsign, Ta.dxcc_id, LEFT(Ta.locator, 6) as grid, Ta.lastseen, 0 from main.stationinfo2024 as Ta
where Ta.locator is not null and Ta.dxcc_id is not null #and Ta.callsign='JS2CTL' #and Ta.decoderSoftware is not null
#and Ta.id = (select max(Tc.id) from main.stationinfo2022 as Tc where Ta.callsign = Tc.callsign);






SELECT *
FROM spots_2023_01
WHERE band='invalid' AND utc >= 1672507800 AND utc <= 1672508700
GROUP BY band, zone1, zone2


SELECT count(*) FROM spots_01_2023 WHERE band='20m';



CREATE TABLE IF NOT EXISTS default.dxcc_list
    (`prefix` String,
     `entity` String,
     `cont` String,
     `itu` String,
     `cq` String,
     `entity_code` UInt16,
     `deleted` UInt8)
ENGINE = MergeTree
ORDER BY (entity_code)
PRIMARY KEY (entity_code);



SELECT
    toStartOfInterval(toDateTime(utc, 'UTC'), toIntervalMinute(15)) AS interval_start,
    sum(cnt) AS row_count
FROM  spots_sum_grid_ll_2024_07
WHERE  utc >= (SELECT min(utc) AS minUTC FROM spots_sum_grid_ll_2024_07) AND utc <= (SELECT max(utc) AS maxUTC FROM spots_sum_grid_ll_2024_07)
  -- AND band='15m'
   AND zone1='30'
   AND zone2='6'
GROUP BY interval_start
ORDER BY interval_start ASC;


SELECT
    toStartOfInterval(toDateTime(utc), toIntervalMinute(15)) AS interval_start,
    count(*) AS row_count
FROM  spots_sum_grid_ll_2024_07
WHERE  utc >= (SELECT min(utc) AS minUTC FROM spots_sum_grid_ll_2024_07) AND utc <= (SELECT max(utc) AS maxUTC FROM spots_sum_grid_ll_2024_07)
GROUP BY interval_start
ORDER BY interval_start ASC;



-- CREATE TABLE IF NOT EXISTS default.spots_sum_{tableSuffix}
--            (`utc` Int32,
--            `band` String,
--            `zone1` Int32,
--            `zone2` Int32,
--            `cnt` UInt8
--            )ENGINE = SummingMergeTree
--            ORDER BY (utc, band, zone1, zone2)
--            PARTITION BY toYYYYMM(toDateTime(utc))
--            PRIMARY KEY (utc, band, zone1, zone2);



SELECT grid1, grid2, geoDistance(lon1, lat1, lon2, lat2)/1000 as kmDistance
FROM default.spots_sum_grid_ll_2024_07
WHERE band = '160m'
GROUP BY grid1, grid2, lon1, lat1, lon2, lat2
ORDER BY kmDistance DESC




SELECT lat1, lon1, sum(cnt) as cnt1 FROM default.spots_sum_grid_ll_2023_01 WHERE band = '160m' GROUP BY lat1, lon1 HAVING cnt1 > 5







SELECT
    toStartOfInterval(toDateTime(utc, 'UTC'), toIntervalMinute(15)) AS interval_start,
    sum(cnt) AS row_count
FROM spots_sum_2023_01
WHERE
     utc >= (SELECT min(utc) AS minUTC FROM spots_sum_2023_01) AND utc <= (SELECT max(utc) AS maxUTC FROM spots_sum_2023_01)
     AND band='40m'
GROUP BY interval_start
ORDER BY interval_start ASC
UNION ALL
SELECT
    toStartOfInterval(toDateTime(utc, 'UTC'), toIntervalMinute(15)) AS interval_start,
    sum(cnt) AS row_count
FROM spots_sum_2023_02
WHERE
     utc >= (SELECT min(utc) AS minUTC FROM spots_sum_2023_02) AND utc <= (SELECT max(utc) AS maxUTC FROM spots_sum_2023_02)
     AND band='40m'
GROUP BY interval_start
ORDER BY interval_start ASC
UNION ALL
SELECT
    toStartOfInterval(toDateTime(utc, 'UTC'), toIntervalMinute(15)) AS interval_start,
    sum(cnt) AS row_count
FROM spots_sum_2023_03
WHERE
     utc >= (SELECT min(utc) AS minUTC FROM spots_sum_2023_03) AND utc <= (SELECT max(utc) AS maxUTC FROM spots_sum_2023_03)
     AND band='40m'
GROUP BY interval_start
ORDER BY interval_start ASC;














