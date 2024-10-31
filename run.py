import csv

from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx, implot
from app import App
import numpy as np

from lcl import Category, Import, Report, amount, from_specific, report

app = App()

categories = [
]

implot.create_context()

def dump_reports(reports: list[Report], filename: str) -> None:
	with open(filename, 'w', newline='') as output:
		writer = csv.DictWriter(output, fieldnames=reports[0].to_dict().keys(), delimiter=',')
		writer.writeheader()
		writer.writerows([r.to_dict() for r in reports])

reports = None

imported = []
import_file_dialog = None
import_selected = None

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:
				clicked_import, _ = imgui.menu_item("Import", None, None)
				if clicked_import:
					import_file_dialog = pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect)
				clicked_analyse, _ = imgui.menu_item("Analyse", None, None)
				if clicked_analyse and import_selected:
						reports = [report(section, categories) for section in import_selected.sectionned(Import.Granularity.Month)] 
				clicked_dump_reports, _ = imgui.menu_item("Dump Reports", None, None)
				if clicked_dump_reports and reports:
					dump_reports(reports, "reports.csv")
				clicked_exit, _ = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

	imgui.dock_space_over_viewport()

	with imgui_ctx.begin("Imports"):
		if imgui.button("Import"):
			import_file_dialog = pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect)

		if import_file_dialog and import_file_dialog.ready():
			for filepath in import_file_dialog.result():
				print(filepath)
				imported.append(Import(filepath))
			import_file_dialog = None

		with imgui_ctx.begin_table("##imports table", 2, flags=imgui.TableFlags_.resizable):
			imgui.table_next_column()
			with imgui_ctx.begin_list_box("##imports", imgui.get_content_region_avail()):
				for import_data in imported:
					_, selected = imgui.selectable(import_data.filename, import_selected.filename == import_data.filename if import_selected else False, imgui.SelectableFlags_.allow_double_click)
					if selected:
						import_selected = import_data
			imgui.table_next_column()
			with imgui_ctx.begin_list_box("##imports contents box", imgui.get_content_region_avail()):
				if import_selected and import_selected.entries:
					columns = import_selected.entries[0].keys()
					with imgui_ctx.begin_table("##import contents table", len(columns), flags=imgui.TableFlags_.resizable):
						for c in columns:
							imgui.table_setup_column(c)
						imgui.table_headers_row()
						for entry in import_selected.entries:
							imgui.table_next_row()
							for c in columns:
								imgui.table_next_column()
								imgui.text(entry[c])

	with imgui_ctx.begin("Categories"):
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

	with imgui_ctx.begin("Plot window"):
		if reports:
			implot.begin_plot("My Plot", imgui.get_content_region_avail())
			implot.setup_axes("Time", "Movement EUR")
			ticks = [r.timespan.span_str("%d/%m") for r in reports]
			implot.setup_axis_ticks(implot.ImAxis_.x1, 0.0, len(ticks)-1, len(ticks), ticks, False)
			def plot_categories(data : list[Report], categories: list[Category], group_size: float = 1, sub_cat_size : float = 0.5) -> None:
				value_of = lambda report, category: report.analysis[category.name] if category.name in report.analysis else 0
				values_of = lambda category: np.array([value_of(report, category) for report in data])
				arr = np.ascontiguousarray([values_of(category) for category in categories if category.active])
				implot.plot_bar_groups(
					label_ids=[c.name for c in categories if c.active],
					values=arr,
					group_count=len(data),
					group_size=group_size,
					flags=implot.BarGroupsFlags_.stacked,
					shift=group_size * sub_cat_size - 0.5 # offset to make the subcategory on the side of their parent,  -0.5 to center all
				)
				for category in categories:
					if (category.active and category.sub):
						plot_categories(data, category.sub, group_size=group_size * 0.5, sub_cat_size=sub_cat_size)
			plot_categories(reports, categories)
			implot.end_plot()

	app.render()

app.shutdown()
