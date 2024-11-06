import calendar
import csv
from enum import Enum
import json
from datetime import datetime
from os import path
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
	def from_dates(dates, fmt : str = "%d/%m/%Y"):
		parsed = [datetime.strptime(d, fmt) for d in dates]
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

	def __init__(self, filename : str = None):
		self.filename : str = filename if filename else "unsaved.json"
		self.begin : datetime = None
		self.end : datetime = None
		self.files: list[str] = []
		self.entries : list[dict] = []
		self.version_id = 0
		if filename:
			self.load(filename)

	@staticmethod
	def from_file(filename, datetime_fmt = "%Y/%m/%d") -> "Import":
		new = Import()
		new.load(filename, datetime_fmt=datetime_fmt)
		return new

	def to_json(self, datetime_fmt = "%d/%m/%Y"):
		if self.begin is None or self.end is None:
			raise Exception("Timespan not set")
		return {
			'begin' : self.begin.strftime(datetime_fmt),
			'end' : self.end.strftime(datetime_fmt),
			'files' : [path.relpath(f, path.dirname(self.filename)) for f in self.files],
		}

	def valid(self) -> bool:
		return self.begin is not None and self.end is not None

	def save(self, filename = None, datetime_fmt = "%Y/%m/%d"):
		try:
			if filename:
				self.filename = filename
			with open(self.filename, 'w') as out:
				json.dump(self.to_json(datetime_fmt=datetime_fmt), out)
		except Exception as e:
			print(e)

	def load(self, filename = None, datetime_fmt = "%Y/%m/%d"):
		try:
			if filename:
				self.filename = filename
			with open(self.filename) as inp:
				if inp is None:
					raise Exception("File not found")
				data = json.load(inp)
				self.begin = datetime.strptime(data['begin'], datetime_fmt)
				self.end = datetime.strptime(data['end'], datetime_fmt)
				self.files = [path.dirname(self.filename) + '/' + f for f in data['files']]
				self.load_entries()
		except Exception as e:
			print(e)

	def read_entries(self, apply_filter = True):
		entries = []
		[entries := entries + read_bank_statement(f) for f in self.files]
		if apply_filter and self.valid():
			entries = [e for e in entries if datetime.strptime(e['date'], "%d/%m/%Y") >= self.begin and datetime.strptime(e['date'], "%d/%m/%Y") <= self.end]
		return entries

	def load_entries(self):
		print("loading entries")
		self.entries = self.read_entries()
		self.version_id += 1

	def section(self, timespan : Timespan):
		return filter(lambda e: e['date'] >= timespan.begin and e['date'] <= timespan.end, self.entries())

	def select_dates_from_contents(self):
		entries = self.read_entries(apply_filter=False)
		self.begin = min(datetime.strptime(e['date'], "%d/%m/%Y") for e in entries)
		self.end = max(datetime.strptime(e['date'], "%d/%m/%Y") for e in entries)

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
		if self.entries is None or len(self.entries) == 0:
			return []
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
