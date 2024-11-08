import calendar
from datetime import datetime
from enum import Enum
from dateutil.relativedelta import relativedelta
from imgui_bundle import imgui, imgui_ctx, implot

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

def input_date(label : str, date : datetime) -> tuple[bool, datetime]:
	changed = False
	changed, num_dates = imgui.input_int3(label, [date.day if date else 1, date.month if date else 1, date.year if date else 1])
	d, m, y = num_dates
	m = max(1, min(12, m))
	d = max(1, min(calendar.monthrange(y, m)[1], d))
	if (changed and date):
		date = date.replace(day=d, month=m, year=y)
	elif changed:
		date = datetime(year=y, month=m, day=d)
	return changed, date
