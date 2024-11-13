import csv
from enum import Enum
from typing import Optional
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, implot, ImVec2, imgui_ctx
import numpy as np
from category import Category, categorise
from imports import Import, amount
from schedule import Timespan, Granularity

class Report:
	def __init__(self, timespan : Timespan, movements : float, status : Optional[float], categorised : dict):
		self.timespan : Timespan = timespan
		self.movements : float = movements
		self.status : Optional[float] = status
		self.categorised : dict = categorised #* flattened from categories

	@staticmethod
	def from_section(section : Import.Section, categories : list):
		movements = [entry for entry in section.entries if entry['account'] == '']
		return Report(
			timespan=section.timespan,
			movements=sum(amount(r) for r in movements),
			status=next(iter(amount(entry) for entry in section.entries if entry['account'] != ''), None),#* only sometimes present in a section
			categorised=categorise("", movements, categories),
		)

	def to_dict(self):
		return {
			'timespan' : str(self.timespan),
			'movements' : self.movements,
			'status' : self.status,
		} | self.categorised

def analyse(imp: Import, categories : list[Category], granularity : Granularity, count : int = 1) -> list[Report]:
	return [Report.from_section(s, categories) for s in imp.sectionned(granularity, count)]

def dump_reports(reports: list[Report], filename: str) -> None:
	print("dumping to " + filename)
	with open(filename, 'w', newline='') as output:
		writer = csv.DictWriter(output, fieldnames=reports[0].to_dict().keys(), delimiter=',')
		writer.writeheader()
		writer.writerows([r.to_dict() for r in reports])

def plot_analysis(categories :  list[Category], analysis : list[Report], size : ImVec2 = ImVec2(0, 0)) -> None:
	size = size if size.x > 0 or size.y > 0 else imgui.get_content_region_avail()
	implot.begin_plot("My Plot", size)
	implot.setup_axes("Time", "Movement EUR")
	ticks = [r.timespan.span_str("%d/%m") for r in analysis]
	if len(ticks) > 1:
		implot.setup_axis_ticks(implot.ImAxis_.x1, 0.0, max(1, len(ticks)-1), len(ticks), ticks, False)
	def plot_categories(anls : list[Report], cats: list[Category], group_size: float = 1, sub_cat_size : float = 0.5) -> None:
		value_of = lambda report, category: report.categorised[category.name] if category.name in report.categorised else 0
		values_of = lambda category: np.array([value_of(report, category) for report in anls])
		arr = np.ascontiguousarray([values_of(category) for category in cats if category.active])
		implot.plot_bar_groups(
			label_ids=[c.name for c in cats if c.active],
			values=arr,
			group_count=len(anls),
			group_size=group_size,
			flags=implot.BarGroupsFlags_.stacked,
			shift=group_size * sub_cat_size - 0.5 # offset to make the subcategory on the side of their parent,  -0.5 to center all
		)
		for category in cats:
			if (category.active and category.sub):
				plot_categories(anls, category.sub, group_size=group_size * 0.5, sub_cat_size=sub_cat_size)
	plot_categories(analysis, categories)
	implot.end_plot()

def input_granularity(title: str, granularity : tuple[Granularity, int]) -> tuple[bool, Granularity, int]:
	gran_type, gran_count = granularity
	changed = False
	with imgui_ctx.tree_node(title) as tree:
		if (tree):
			with imgui_ctx.begin_table("##granularity", 2, flags=imgui.TableFlags_.resizable):
				imgui.table_next_column()
				changed_type, gran_type_new = imgui.combo("Scale", gran_type.value, ["Day", "Month", "Year"])
				gran_type = Granularity(gran_type_new)
				imgui.table_next_column()
				changed_count, gran_count = imgui.input_int("Count", gran_count)
				changed = changed_type or changed_count
	return changed, gran_type, max(1, gran_count)


#region UI

class UI:

	def __init__(self):
		self.granularity_type : Granularity = Granularity.Month
		self.granularity_count : int = 1
		self.analysis : list[Report] = None
		self.dump_save_dialog : pfd.save_file = None

	def draw(self, title : str, imp : Import, categories : list[Category], dirty : bool = False) -> None:
		with imgui_ctx.begin(title) as window:
			if window:
				with imgui_ctx.begin_table("##analysis table", 2, flags=imgui.TableFlags_.resizable):
					imgui.table_next_column()
					changed_gran, self.granularity_type, self.granularity_count = input_granularity("Granularity", (self.granularity_type, self.granularity_count))
					if dirty:
						self.analysis = None
					if imp and (changed_gran or (not self.analysis)):
						try:
							self.analysis = analyse(imp, categories, self.granularity_type, self.granularity_count)
						except Exception as e:
							print("error", e)
					if imp and imgui.button("Dump"):
						self.dump_save_dialog = pfd.save_file("Save to", imp.filename + "-" + self.granularity_type.name + str(self.granularity_count) + "-analysis.csv", filters=["*.csv"])
					if self.dump_save_dialog and self.dump_save_dialog.ready():
						filepath = self.dump_save_dialog.result()
						if (filepath):
							dump_reports(self.analysis, filepath)
						self.dump_save_dialog = None
					if self.analysis:
						plot_analysis(
							categories=categories,
							analysis=self.analysis,
							size=imgui.get_content_region_avail()
						)
					imgui.table_next_column()
					def recursive_checkbox(category : Category) -> bool:
						_, category.active = imgui.checkbox(category.name, category.active)
						if category.active and category.sub:
							imgui.same_line()
							with imgui_ctx.tree_node("##" + category.name) as tree:
								if (tree):
									for sub in category.sub:
										recursive_checkbox(sub)
							return True
						return False
					for category in categories:
						recursive_checkbox(category)
#endregion UI
