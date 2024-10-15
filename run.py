import csv
import sys
from imgui_bundle import imgui, imgui_ctx, implot
from app import App
import numpy as np

from lcl import Category, Import, Report, amount, from_specific, report

app = App()

categories = [
]

implot.create_context()

input_f = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: run.py <input report json> [<output csv>]")
output_f = sys.argv[2] if len(sys.argv) > 2 else "default_report_output.csv"
reports = None
with open(output_f, 'w', newline='') as output:
	reports = [report(section, categories) for section in Import(input_f).sectionned(Import.Granularity.Month)]
	rows = [r.to_dict() for r in reports]
	writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=',')
	writer.writeheader()
	writer.writerows(rows)

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:
				clicked_new, selected_new = imgui.menu_item("New", None, None)
				clicked_exit, selected_exit = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

	imgui.dock_space_over_viewport()

	with imgui_ctx.begin("Plot window"):
		implot.begin_plot("My Plot", imgui.get_content_region_avail())
		implot.setup_axes("Time", "Movement EUR")
		ticks = [r.timespan.span_str("%d/%m") for r in reports]
		implot.setup_axis_ticks(implot.ImAxis_.x1, 0.0, len(ticks)-1, len(ticks), ticks, False)

		def plot_categories(data : list[Report], categories: list[Category], group_size: float = 1, sub_cat_size : float = 0.5) -> None:
			value_of = lambda report, category: report.analysis[category.name] if category.name in report.analysis else 0
			values_of = lambda category: np.array([value_of(report, category) for report in data])
			arr = np.ascontiguousarray([values_of(category) for category in categories])
			implot.plot_bar_groups(
				label_ids=[c.name for c in categories],
				values=arr,
				group_count=len(data),
				group_size=group_size,
				flags=implot.BarGroupsFlags_.stacked,
				shift=group_size * sub_cat_size - 0.5 # offset to make the subcategory on the side of their parent,  -0.5 to center all
			)
			for category in categories:
				if (category.sub):
					plot_categories(data, category.sub + [Category(category.name + ".other")], group_size=group_size * 0.5, sub_cat_size=sub_cat_size)

		plot_categories(reports, categories)
		implot.end_plot()

	app.render()

app.shutdown()
