import csv
from datetime import datetime
from typing import Optional
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, implot, ImVec2, imgui_ctx
import numpy as np
from category import Category, categorise
from imports import Import, amount
from schedule import Timespan, Granularity

class Report:
	def __init__(self, timespan : Timespan, movements : float, status : Optional[tuple[datetime, float]], categorised : dict):
		self.timespan : Timespan = timespan
		self.movements : float = movements
		self.status : Optional[tuple[datetime, float]] = status
		self.categorised : dict = categorised #* flattened from categories

	@staticmethod
	def from_section(section : Import.Section, categories : list):
		movements = [entry for entry in section.entries if entry['account'] == '']
		status_entry = next(iter(entry for entry in section.entries if entry['account'] != ''), None)
		return Report(
			timespan=section.timespan,
			movements=sum(amount(r) for r in movements),
			status=(datetime.strptime(status_entry['date'], "%d/%m/%Y"), amount(status_entry)) if status_entry else None,#* only sometimes present in a section
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
	implot.begin_plot("categorical analysis", size)
	implot.setup_axes("Time", "EUR")
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
		self.dump_save_dialog : pfd.save_file = None
		self.dump_target : list[Report] = None

	@staticmethod
	def can_analyse(imp : Import, categories : list[Category]) -> bool:
		return imp is not None and imp.valid() and categories is not None

	def analyse(self, imp : Import, categories : list[Category]) -> list[Report]:
		return analyse(imp, categories, self.granularity_type, self.granularity_count)

	def draw_config(self, title : str, categories : list[Category] = []) -> bool:
		changed_gran = False
		with imgui_ctx.begin(title) as window:
			if window:
				changed_gran, self.granularity_type, self.granularity_count = input_granularity("Granularity", (self.granularity_type, self.granularity_count))
				imgui.separator()
				with imgui_ctx.begin_list_box("##categories"):
					def recursive_checkbox(category : Category, parent_active : bool = True) -> None:
						flags = (
							(imgui.TreeNodeFlags_.selected if category.active and parent_active else 0) |
							(imgui.TreeNodeFlags_.leaf if len(category.sub) == 0 else 0) |
							imgui.TreeNodeFlags_.open_on_arrow |
							imgui.TreeNodeFlags_.open_on_double_click
						)
						tree = imgui.tree_node_ex(category.name, flags=flags)
						if parent_active and imgui.is_item_clicked() and not imgui.is_item_toggled_open():
							category.active = not category.active
						if (tree):
							for sub in category.sub:
								recursive_checkbox(sub, parent_active and category.active)
							imgui.tree_pop()
					for category in categories:
						recursive_checkbox(category)
		return changed_gran

	def dump(self, analysis : list[Report]) -> None:
		self.dump_save_dialog = pfd.save_file("Save to", "categorical_analysis-" + datetime.now().strftime("%d_%m_%Y") + "-" + self.granularity_type.name + "-" + str(self.granularity_count) + ".csv", filters=["*.csv"])
		self.dump_target = analysis

	def draw_categorical(self, title : str, analysis :list[Report], categories : list[Category]) -> None:
		if self.dump_save_dialog and self.dump_save_dialog.ready():
			filepath = self.dump_save_dialog.result()
			if (filepath):
				dump_reports(analysis, filepath)
			self.dump_save_dialog = None
			self.dump_target = None
		with imgui_ctx.begin(title) as window:
			if window and analysis and len(analysis) > 0:
				self.dump_button("Dump", analysis)
				plot_analysis(
					categories=categories,
					analysis=analysis,
					size=imgui.get_content_region_avail()
				)

	def draw_status(self, title : str, analysis : list[Report]) -> None:
		with imgui_ctx.begin(title) as window:
			if window and analysis and len(analysis) > 0:
				if imgui.button("Dump"):
					self.dump(analysis)
				implot.begin_plot("Status tracking", imgui.get_content_region_avail())
				implot.setup_axes("Time", "EUR")
				implot.setup_axis_scale(implot.ImAxis_.x1, implot.Scale_.time)

				implot.plot_line(
					label_id="Amount",
					xs=np.ascontiguousarray([report.status[0].timestamp() for report in analysis if report.status is not None]),
					ys=np.ascontiguousarray([report.status[1] for report in analysis if report.status is not None])
				)

				implot.plot_line(
					label_id="Income",
					xs=np.ascontiguousarray([report.timespan.timestamp() for report in analysis]),
					ys=np.ascontiguousarray([report.movements for report in analysis])
				)

				implot.end_plot()

#endregion UI
