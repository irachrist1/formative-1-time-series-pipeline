-- Query 1: latest recorded traffic observation.
SELECT tr.id, tr.date_time, tr.traffic_volume, wc.weather_main
FROM traffic_records AS tr
JOIN weather_conditions AS wc ON wc.id = tr.weather_condition_id
ORDER BY tr.date_time DESC
LIMIT 1;

-- Query 2: records in a date range.
SELECT tr.date_time, tr.traffic_volume, tr.temp, tr.rain_1h
FROM traffic_records AS tr
WHERE tr.date_time BETWEEN '2018-09-01 00:00:00' AND '2018-09-07 23:59:59'
ORDER BY tr.date_time;

-- Query 3: average traffic by weather category.
SELECT wc.weather_main, ROUND(AVG(tr.traffic_volume), 2) AS average_traffic, COUNT(*) AS hourly_records
FROM traffic_records AS tr
JOIN weather_conditions AS wc ON wc.id = tr.weather_condition_id
GROUP BY wc.weather_main
ORDER BY average_traffic DESC;

-- Query 4: peak average hour of day.
SELECT HOUR(date_time) AS hour_of_day, ROUND(AVG(traffic_volume), 2) AS average_traffic
FROM traffic_records
GROUP BY HOUR(date_time)
ORDER BY average_traffic DESC
LIMIT 5;

