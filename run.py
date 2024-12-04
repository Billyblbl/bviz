from app import App
from imgui_bundle import imgui, imgui_ctx, implot
import imports
import analysis
import category
import console
from console import LogEntry as Log
from os import path
from vjf import load, FormatMap, FileSlot

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
	changed_selected_import : bool = False
	changed_categories : bool = False
	changed_config : bool = False

	force_focus = None
	for pending_cat, pending_imp, pending_src in app.pending_file_drops:
		# load pending categories
		for slot in pending_cat:
			category_ui.add_blueprints(slot.content)
			force_focus = category_ui
			opened_category_window = True
		if len(pending_cat) == 1 and len(category_ui.blueprints) == 0:
			category_ui.slot = pending_cat[0]
		# load pending imports
		if len(pending_imp) > 0:
			import_ui.add_imports(pending_imp)
			force_focus = import_ui
			opened_import_window = True
		# load pending sources
		if len(pending_src) > 0:
			force_focus = import_ui
			opened_import_window = True
			if import_ui.selected_import is None:
				import_ui.create_import()
			import_ui.add_sources(pending_src)
	app.pending_file_drops.clear()

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("App", True) as menu:
			if menu:
				if imgui.menu_item("Exit", None, None)[0]:
					app.close_next_update()

		import_ui.menu("Imports")
		category_ui.menu("Categories")
		if analysis_ui.menu("Analysis", analysis_reports, analysis_ui.can_analyse(import_ui.get_selection(), category_ui.categories)):
			analysis_reports = analysis_ui.analyse(import_ui.get_selection(), category_ui.categories)
			console.log("default", "main", f"Analysed : {len(analysis_reports)} reports", Log.Level.DEBUG)
			console.log("default", "main", f"Analysis reason : manual", Log.Level.DEBUG)
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
		if force_focus == import_ui:
			imgui.set_next_window_focus()
		changed_selected_import, selected_import = import_ui.draw("Imports")
	if opened_category_window:
		if force_focus == category_ui:
			imgui.set_next_window_focus()
		changed_categories, selected_categories = category_ui.draw("Categories")
	if opened_analysis_config_window:
		changed_config = analysis_ui.draw_config("Config", categories=selected_categories)

	if (changed_selected_import or changed_categories or changed_config) and analysis_ui.can_analyse(selected_import, selected_categories):
		analysis_reports = analysis_ui.analyse(selected_import, selected_categories)
		console.log("default", "main", f"Analysed : {len(analysis_reports)} reports", Log.Level.INFO)
		if changed_selected_import:
			console.log("default", "main", f"Analysis reason : changed_selected_import", Log.Level.DEBUG)
		if changed_categories:
			console.log("default", "main", f"Analysis reason : changed_categories", Log.Level.DEBUG)
		if changed_config:
			console.log("default", "main", f"Analysis reason : changed_config", Log.Level.DEBUG)

	if opened_analysis_categorical_window:
		analysis_ui.draw_categorical("Analysis", analysis_reports, selected_categories)
	if opened_analysis_status_window:
		analysis_ui.draw_status("Evolution", analysis_reports)
	if opened_console_window:
		console_ui.draw_console("Console", force_scroll_console)
	app.render()

implot.destroy_context()
app.shutdown()
