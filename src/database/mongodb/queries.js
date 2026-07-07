// Query 1: latest record.
db.traffic_records.find({}).sort({date_time: -1}).limit(1);

// Query 2: records in a date range.
db.traffic_records.find({
  date_time: {
    $gte: ISODate("2018-09-01T00:00:00Z"),
    $lte: ISODate("2018-09-07T23:59:59Z")
  }
}).sort({date_time: 1});

// Query 3: average traffic by weather category.
db.traffic_records.aggregate([
  {$group: {
    _id: "$weather.weather_main",
    average_traffic: {$avg: "$traffic_volume"},
    hourly_records: {$sum: 1}
  }},
  {$sort: {average_traffic: -1}}
]);

// Query 4: five busiest hours of day on average.
db.traffic_records.aggregate([
  {$group: {
    _id: {$hour: "$date_time"},
    average_traffic: {$avg: "$traffic_volume"}
  }},
  {$sort: {average_traffic: -1}},
  {$limit: 5}
]);

