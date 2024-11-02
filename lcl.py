import calendar
import csv
from enum import Enum
import json
from datetime import datetime
import os
from typing import Optional
from dateutil.relativedelta import relativedelta

class Granularity(Enum):
	Day = 0
	Month = 1
	Year = 2

	def __str__(self) -> str:
		return ['day', 'month', 'year'][int(self)]

class Timespan:

	@staticmethod
	def from_dates(dates):
		parsed = [datetime.strptime(d, "%d/%m/%Y") for d in dates]
		return Timespan(min(parsed), max(parsed))

	@staticmethod
	def from_date_granularity(date : datetime, granularity : Granularity, gran_count : int = 1):
		match granularity:
			case Granularity.Day:
				return Timespan(b=date, e=date + relativedelta(days=gran_count-1))
			case Granularity.Month:
				e = date + relativedelta(months=gran_count-1)
				return Timespan(b=date.replace(day=1), e=e.replace(day=calendar.monthrange(e.year, e.month)[1]))
			case Granularity.Year:
				return Timespan(b=date.replace(month=1, day=1), e=(date + relativedelta(years=gran_count-1)).replace(month=12, day=31))

	def __init__(self, b, e):
		self.begin = b
		self.end = e

	def __str__(self):
		return self.begin.strftime("%d/%m/%Y") + "-" + self.end.strftime("%d/%m/%Y")

	def begin_str(self, fmt : str = "%d/%m/%Y"):
		return self.begin.strftime(fmt)

	def end_str(self, fmt : str = "%d/%m/%Y"):
		return self.begin.strftime(fmt)

	def span_str(self, fmt : str = "%d/%m/%Y", separator : str = "-"):
		return self.begin.strftime(fmt) + separator + self.end.strftime(fmt)

	def sectionned(self, granularity : Granularity, count : int = 1) -> list:
		it = Timespan(Timespan.from_date_granularity(self.begin, granularity, count).begin, Timespan.from_date_granularity(self.end, granularity, count).end)
		sections = []
		while it.begin < it.end:
			match granularity:
				case Granularity.Day:
					sections.append(Timespan(b=it.begin, e=it.begin + relativedelta(days=count-1)))
					it.begin = it.begin + relativedelta(days=count)
				case Granularity.Month:
					e = it.begin + relativedelta(months=count-1)
					sections.append(Timespan(b=it.begin.replace(day=1), e=e.replace(day=calendar.monthrange(e.year, e.month)[1])))
					it.begin = (it.begin + relativedelta(months=count)).replace(day=1)
				case Granularity.Year:
					sections.append(Timespan(b=it.begin.replace(month=1, day=1), e=(it.begin + relativedelta(years=count-1)).replace(month=12, day=31)))
					it.begin = (it.begin + relativedelta(years=count)).replace(month=1, day=1)
		return sections

class Report:
	def __init__(self, timespan : Timespan, movements : float, status : Optional[float], analysis : dict):
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
	def __init__(self, name, predicate = lambda e: False, sub = []):
		self.name = name
		self.predicate = predicate
		self.sub = sub
		if self.sub:
			self.sub.append(Category(name + ".other"))
		self.active = True

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

	if parent_category != "" and categories: #* last category is always "*.other" if has parent & not empty
		analysis[categories[-1].name] = sum(amount(e) for e in unused_entries) if unused_entries else 0
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

	class Section:
		def __init__(self, timespan : Timespan, entries = []):
			self.timespan = timespan
			self.entries = entries

	def make_report(section : Section, categories : list) -> Report:
		movements = [entry for entry in section.entries if entry['account'] == '']
		return Report(
			timespan=section.timespan,
			movements=sum(amount(r) for r in movements),
			status=next(iter(amount(entry) for entry in section.entries if entry['account'] != ''), None),#* only sometimes present in a section
			analysis=analyse("", movements, categories),
		)

	def sectionned(self, granularity : Granularity, count : int = 1) -> list[Section]:
		#* Create sections (thats a whole lot of discarded parsing, easy perf gain here @OPTI)
		total_timespan = Timespan(
			min(datetime.strptime(e['date'], "%d/%m/%Y") for e in self.entries).replace(hour=0, minute=0, second=0),
			max(datetime.strptime(e['date'], "%d/%m/%Y") for e in self.entries).replace(hour=23, minute=59, second=59)
		)
		sections = [Import.Section(t, []) for t in total_timespan.sectionned(granularity, count)]
		#* Distribute entries in sections
		for e in self.entries:
			date = datetime.strptime(e['date'], "%d/%m/%Y")
			next((s for s in sections if date >= s.timespan.begin and date <= s.timespan.end)).entries.append(e)
		return sections

	def analyse(self, categories : list[Category], granularity : Granularity, count : int = 1):
		return [Import.make_report(s, categories) for s in self.sectionned(granularity, count)]
