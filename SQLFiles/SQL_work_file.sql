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
