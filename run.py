from app import App
from imgui_bundle import imgui, imgui_ctx, implot
import imports
import analysis
import category
import console

app = App("bankviz")

implot.create_context()

import_ui = imports.UI()
category_ui = category.UI()
analysis_ui = analysis.UI()
analysis_reports : list[analysis.Report] = []
console_ui = console.UI()

opened_import_window : bool = True
opened_category_window : bool = True
opened_analysis_config_window : bool = True
opened_analysis_categorical_window : bool = True
opened_analysis_status_window : bool = True
opened_console_window : bool = True

console.log("default", "main", "Initialized UIs")

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("App", True) as menu:
			if menu:
				if imgui.menu_item("Exit", None, None)[0]:
					app.close_next_update()

		import_ui.menu("Imports")
		category_ui.menu("Categories")
		if analysis_ui.menu("Analysis", analysis_reports, analysis_ui.can_analyse(import_ui.get_selection(), category_ui.categories)):
			analysis_reports = analysis_ui.analyse(import_ui.get_selection(), category_ui.categories)
			console.log("default", "main", f"Analysed : {len(analysis_reports)} reports")
			console.log("default", "main", f"Analysis reason : manual")
		force_scroll_console = console_ui.menu("Console")

		with imgui_ctx.begin_menu("View", True) as menu:
			if menu:
				opened_import_window = imgui.menu_item("Imports", None, opened_import_window)[1]
				opened_category_window = imgui.menu_item("Categories", None, opened_category_window)[1]
				opened_analysis_config_window = imgui.menu_item("Analysis Config", None, opened_analysis_config_window)[1]
				opened_analysis_categorical_window = imgui.menu_item("Categorical Analysis", None, opened_analysis_categorical_window)[1]
				opened_analysis_status_window = imgui.menu_item("Status Analysis", None, opened_analysis_status_window)[1]
				opened_console_window = imgui.menu_item("Console", None, opened_console_window)[1]

	imgui.dock_space_over_viewport()

	if opened_import_window:
		changed_selected_import, selected_import = import_ui.draw("Imports")
	if opened_category_window:
		changed_categories, selected_categories = category_ui.draw("Categories")
	if opened_analysis_config_window:
		changed_config = analysis_ui.draw_config("Config", categories=selected_categories)

	if (changed_selected_import or changed_categories or changed_config) and analysis_ui.can_analyse(selected_import, selected_categories):
		analysis_reports = analysis_ui.analyse(selected_import, selected_categories)
		console.log("default", "main", f"Analysed : {len(analysis_reports)} reports")
		if changed_selected_import:
			console.log("default", "main", f"Analysis reason : changed_selected_import")
		if changed_categories:
			console.log("default", "main", f"Analysis reason : changed_categories")
		if changed_config:
			console.log("default", "main", f"Analysis reason : changed_config")

	if opened_analysis_categorical_window:
		analysis_ui.draw_categorical("Analysis", analysis_reports, selected_categories)
	if opened_analysis_status_window:
		analysis_ui.draw_status("Evolution", analysis_reports)
	if opened_console_window:
		console_ui.draw_console("Console", force_scroll_console)
	app.render()

implot.destroy_context()
app.shutdown()
