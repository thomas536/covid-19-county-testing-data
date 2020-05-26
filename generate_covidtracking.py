#!/usr/bin/env python2.7

"""Generate daily.csv for counties similar to covidtracking.com."""

import csv
import itertools
import lib_fips

from datetime import date
from datetime import datetime
from xlrd import open_workbook


def get_fips_county(value, default=None):
  value = "%05d" % int(value)
  result = lib_fips.FIPSToCounty.get(value)
  if result is not None:
    return result[-1]
  return default


def get_fips_state_abbr(value, default=None):
  value = "%02d" % int(value)
  result = lib_fips.FIPSToState.get(value)
  if result is not None:
    return result["abbreviation"]
  return default


fieldnames = [
    "date", "state", "fips", "positive", "negative", "pending",
    "total", "totalTestResults", "negativeIncrease", "positiveIncrease",
    "totalTestResultsIncrease"]


def get_san_francisco_county():
  path = "raw/CA/06075/rows.csv?accessType=DOWNLOAD"
  fips = "06075"
  with open(path) as f:
    rows = sorted(csv.DictReader(f), key=lambda row: row["result_date"])
    """
    items = {}
    for row in rows:
      dt = datetime.strptime(row["result_date"], '%Y/%m/%d').date()
      items[dt] = row
    """

    positive = 0
    negative = 0
    total = 0
    totalTestResults = 0
    prev_date = 0
    for row in rows:
      negativeIncrease = int(row["neg"] or "0")
      negative += negativeIncrease
      positiveIncrease = int(row["pos"] or "0")
      positive += positiveIncrease
      pending = 0  # pending is not in this data
      # totalTestResults = (pos + neg)
      totalTestResultsIncrease = int(row["tests"] or "0")
      totalTestResults += totalTestResultsIncrease
      total += totalTestResultsIncrease + pending
      output_row = {}
      output_row["date"] = int(row["result_date"].replace("/", ""))
      assert prev_date < output_row["date"]
      prev_date = output_row["date"]
      output_row["state"] = "CA"
      output_row["fips"] = fips
      output_row["positive"] = positive
      output_row["negative"] = negative
      output_row["pending"] = pending
      output_row["total"] = total
      output_row["totalTestResults"] = totalTestResults
      output_row["negativeIncrease"] = negativeIncrease
      output_row["positiveIncrease"] = positiveIncrease
      output_row["totalTestResultsIncrease"] = totalTestResultsIncrease
      yield output_row


def get_santa_clara_county():
  path = "raw/CA/06085/manual.xls"
  fips = "06085"
  workbook = open_workbook(filename=path)
  sheet = workbook.sheet_by_name("Sheet1")

  # read header
  nrow = 0
  columns = []
  for ncol in xrange(sheet.ncols):
    columns.append((ncol, sheet.cell(nrow, ncol).value))

  positive = 0
  negative = 0
  total = 0
  totalTestResults = 0
  for nrow in range(1, sheet.nrows):
    row = {}
    for ncol, column in columns:
      value = sheet.cell(nrow, ncol).value
      if value != "":
        row[column] = value

    negativeIncrease = int(row["Negative Results"] or "0")
    negative += negativeIncrease
    positiveIncrease = int(row["Positive Results"] or "0")
    positive += positiveIncrease
    pending = int(row["Pending Results"] or "0")
    # totalTestResults = (pos + neg)
    totalTestResultsIncrease = negativeIncrease + positiveIncrease
    totalTestResults += totalTestResultsIncrease
    total += totalTestResultsIncrease + pending
    # https://stackoverflow.com/a/31359287/12989329
    dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(row["Date Results Were Received"]) - 2)

    output_row = {}
    output_row["date"] = int(dt.strftime("%Y%m%d"))
    output_row["state"] = "CA"
    output_row["fips"] = fips
    output_row["positive"] = positive
    output_row["negative"] = negative
    output_row["pending"] = pending
    output_row["total"] = total
    output_row["totalTestResults"] = totalTestResults
    output_row["negativeIncrease"] = negativeIncrease
    output_row["positiveIncrease"] = positiveIncrease
    output_row["totalTestResultsIncrease"] = totalTestResultsIncrease
    yield output_row


def get_texas():
  path = "raw/TX/TexasCOVID-19CumulativeTestsOverTimebyCounty.xlsx"
  workbook = open_workbook(filename=path)
  sheet = workbook.sheet_by_name("Total Tests Received")

  # read header
  nrow = 1
  columns = []
  for ncol in xrange(sheet.ncols):
    columns.append((ncol, sheet.cell(nrow, ncol).value))

  # hard code months to avoid having to fight with locales
  months = {
      "January": 1,
      "February": 2,
      "March": 3,
      "April": 4,
      "May": 5,
      "June": 6,
      "July": 7,
      "August": 8,
      "September": 9,
      "October": 10,
      "November": 11,
      "December": 12,
  }
  county_name_to_fips = {}
  for fips, (state_name, county_name) in lib_fips.FIPSToCounty.iteritems():
    if state_name == "Texas":
      assert county_name.endswith(" County")
      county_name = county_name.replace(" County", "")
      county_name_to_fips[county_name] = fips

  rows = {}
  for nrow in range(2, sheet.nrows):
    row = {}
    for ncol, column in columns:
      value = sheet.cell(nrow, ncol).value
      if value != "":
        row[column] = value

    if not row:
      continue

    county_name = row.pop("County")
    if county_name != "":
      rows[county_name] = row

  for county_name, fips in county_name_to_fips.iteritems():
    row = rows[county_name]

    values = []
    for key, value in row.iteritems():
      # key is something like "Tests Through April 2"
      parts = key.rsplit(" ", 2)
      assert parts[0] == "Tests Through"
      month = months[parts[1]]
      day = int(parts[2].rstrip("*"))
      year = 2020
      dt = date(year, month, day)

      try:
        value = int(value)
      except ValueError:
        continue

      values.append((dt, value))

    values.sort()

    prev_value = 0
    for dt, value in values:
      totalTestResults = value
      total = value
      totalTestResultsIncrease = value - prev_value
      prev_value = value

      output_row = {}
      output_row["date"] = int(dt.strftime("%Y%m%d"))
      output_row["state"] = "TX"
      output_row["fips"] = fips
      output_row["total"] = total
      output_row["totalTestResults"] = totalTestResults
      output_row["totalTestResultsIncrease"] = totalTestResultsIncrease
      yield output_row


"""
date,state,positive,negative,pending,hospitalizedCurrently,hospitalizedCumulative,inIcuCurrently,inIcuCumulative,onVentilatorCurrently,onVentilatorCumulative,recovered,dataQualityGrade,lastUpdateEt,hash,dateChecked,death,hospitalized,total,totalTestResults,posNeg,fips,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
20200523,AK,408,41943,,10,,,,,,358,C,5/23/2020 15:00,078f2242d7eae1fdde12af6639e71547e42a2eec,2020-05-23T20:00:00Z,10,,42351,42351,42351,02,0,0,901,4,905
"""
output_rows = itertools.chain(
    get_san_francisco_county(),
    get_santa_clara_county(),
    get_texas(),
)
output_path = "daily.csv"
with open(output_path, "w") as f:
  writer = csv.DictWriter(f, fieldnames, quoting=csv.QUOTE_NONNUMERIC)
  writer.writeheader()
  for row in output_rows:
    writer.writerow(row)
