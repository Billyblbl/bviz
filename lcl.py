import calendar
import csv
from enum import Enum
import json
from datetime import datetime
import os

class Timespan:
	def __init__(self, dates):
		parsed = [datetime.strptime(d, "%d/%m/%Y") for d in dates]
		self.begin = min(parsed)
		self.end = max(parsed)

	def __str__(self):
		return self.begin.strftime("%d/%m/%Y") + "-" + self.end.strftime("%d/%m/%Y")

class Report:
	def __init__(self, timespan : Timespan, movements : float, status : float, analysis : dict):
		self.timespan = timespan
		self.movements = movements
		self.status = status
		self.analysis = analysis

	def to_dict(self):
		return {
			'timespan' : str(self.timespan),
			'movements' : self.movements,
			'status' : self.status,
		} | self.analysis

class Category:
	def __init__(self, name, predicate, sub = []):
		self.name = name
		self.predicate = predicate
		self.sub = sub

def column(data, field : str):
	return [row[field] for row in data]

#* Extract the amount of money change in a bank entry as a float
def amount(entry) -> float:
	return float(entry['amount'].replace(',', '.'))

def from_specific(entry : dict, person : str) -> bool:
	return person in entry['label_in'] or person in entry['label_out']

bank_statement_fields = ["date", "amount", "type", "account", "label_out", "label_in", "tbd", "note"]
def read_bank_statement(filename):
	with open(filename, encoding="utf-8-sig") as file:
		reader = csv.DictReader(file, fieldnames=bank_statement_fields, delimiter=';')
		return [row for row in reader]

def analyse(parent_category : str, entries: list, categories : list = []) -> dict :
	analysis = dict()
	unused_entries = entries.copy()
	for cat in categories:
		sub_entries = [e for e in entries if cat.predicate(e)]
		analysis |= { cat.name : sum(amount(e) for e in sub_entries) } | analyse(cat.name, sub_entries, cat.sub)
		unused_entries = [e for e in unused_entries if e not in sub_entries]

	if len(unused_entries) != len(entries) and parent_category != "":
		analysis[parent_category + ".other"] = sum(amount(e) for e in unused_entries)
	return analysis

class Import:
	def __init__(self, filename):
		self.filename = os.path.abspath(filename)
		with open(self.filename) as inp:
			data = json.load(inp)
			self.begin = data['begin']
			self.end = data['end']
			self.complete = 'incomplete' not in data.keys()
			if not self.complete:
				self.incomplete_month_start = data['incomplete']
			self.files = [os.path.dirname(self.filename) + '/' + f for f in data['files']]
			self.entries = self.read_entries()

	def read_entries(self):
		entries = []
		[entries := entries + read_bank_statement(f) for f in self.files]
		return entries

	def section(self, timespan : Timespan):
		return filter(lambda e: e['date'] >= timespan.begin and e['date'] <= timespan.end, self.entries())

	class Granularity(Enum):
		Day = "day"
		Month = "month"
		Year = "year"

	def sectionned(self, granularity : Granularity, count : int = 1):
		class Section:
			def __init__(self, begin : datetime, end : datetime, entries = []):
				self.begin = begin
				self.end = end
				self.entries = entries
		sections = []
		for e in self.entries:
			date = datetime.strptime(e['date'], "%d/%m/%Y")
			section = next((s for s in sections if date >= s.begin and date <= s.end), None)
			if not section:
				match granularity:
					case Import.Granularity.Day:
						section = Section(begin = date, end = date.replace(day=date.day+count-1), entries = [e])
					case Import.Granularity.Month:
						section = Section(begin = date.replace(day=1), end = date.replace(day=calendar.monthrange(date.year, date.month+count-1)[1]), entries = [e])
					case Import.Granularity.Year:
						section = Section(begin = date.replace(month=1, day=1), end = date.replace(year=date.year+count-1, month=12, day=31), entries = [e])
				sections.append(section)
			else:
				section.entries.append(e)
		return iter(s.entries for s in sorted(sections, key=lambda s: s.begin))

def report(section, categories : list) -> Report:
	movements = [entry for entry in section if entry['account'] == '']
	return Report(
		timespan=str(Timespan(column(section, "date"))),
		movements=sum(amount(r) for r in movements),
		status=amount(next(entry for entry in section if entry['account'] != '')),
		analysis=analyse("", movements, categories),
	)
