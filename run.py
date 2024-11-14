import os
import sys
from app import App
from imgui_bundle import imgui, imgui_ctx, implot
import imports
import analysis
import category

app = App()

implot.create_context()

import_ui = imports.UI()
category_ui = category.UI()
analysis_ui = analysis.UI()
analysis_reports : list[analysis.Report] = []

opened_import_window : bool = True
opened_category_window : bool = True
opened_analysis_config_window : bool = True
opened_analysis_categorical_window : bool = True
opened_analysis_status_window : bool = True

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:
				clicked_new, _ = imgui.menu_item("New", None, None)
				if clicked_new:
					os.execv(sys.argv[0], sys.argv)

				clicked_restart, _ = imgui.menu_item("Restart", None, None)
				if clicked_restart:
					os.execv(sys.argv[0], sys.argv)
					app.close_next_update()

				clicked_exit, _ = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

		with imgui_ctx.begin_menu("Imports", True) as menu:
			if menu:
				clicked_load, _ = imgui.menu_item("Load", None, None)
				if clicked_load:
					import_ui.load_imports()
				clicked_reload, _ = imgui.menu_item("Reload", None, None)
				if clicked_reload:
					for imp in import_ui.imported:
						import_ui.imp.load()
				if not import_ui.selected_import:
					imgui.begin_disabled()
				clicked_save, _ = imgui.menu_item("Save", None, None)
				if not import_ui.selected_import:
					imgui.end_disabled()
				if clicked_save:
					import_ui.save_import(import_ui.selected_import)

		with imgui_ctx.begin_menu("Categories", True) as menu:
			if menu:
				clicked_load, _ = imgui.menu_item("Load", None, None)
				if clicked_load:
					category_ui.load_category()
				if not category_ui.categories:
					imgui.begin_disabled()
				clicked_save, _ = imgui.menu_item("Save", None, None)
				if not category_ui.categories:
					imgui.end_disabled()
				if clicked_save:
					category_ui.save_category(category_ui.categories)
				clicked_use_all, _ = imgui.menu_item("Use All", None, None)
				if clicked_use_all:
					category_ui.use_all_categories()
				clicked_reset_used, _ = imgui.menu_item("Reset Used", None, None)
				if clicked_reset_used:
					category_ui.reset_used()

		with imgui_ctx.begin_menu("Analysis", True) as menu:
			if menu:
				if not analysis.UI.can_analyse(import_ui.selected_import, category_ui.categories):
					imgui.begin_disabled()
				clicked_analyse, _ = imgui.menu_item("Run", None, None)
				if not analysis_ui.can_analyse(import_ui.selected_import, category_ui.categories):
					imgui.end_disabled()
				if clicked_analyse:
					analysis_reports = analysis_ui.analyse(import_ui.selected_import, category_ui.categories)
				clicked_dump, _ = imgui.menu_item("Dump", None, None)
				if clicked_dump:
					analysis_ui.dump(analysis_reports)

		with imgui_ctx.begin_menu("View", True) as view_menu:
			if view_menu:
				clicked_import, _ = imgui.menu_item("Imports", None, opened_import_window)
				if clicked_import:
					opened_import_window = not opened_import_window
				clicked_categories, _ = imgui.menu_item("Categories", None, opened_category_window)
				if clicked_categories:
					opened_category_window = not opened_category_window
				clicked_config, _ = imgui.menu_item("Analysis Config", None, opened_analysis_config_window)
				if clicked_config:
					opened_analysis_config_window = not opened_analysis_config_window
				clicked_categorical, _ = imgui.menu_item("Categorical Analysis", None, opened_analysis_categorical_window)
				if clicked_categorical:
					opened_analysis_categorical_window = not opened_analysis_categorical_window
				clicked_status, _ = imgui.menu_item("Status Analysis", None, opened_analysis_status_window)
				if clicked_status:
					opened_analysis_status_window = not opened_analysis_status_window

	imgui.dock_space_over_viewport()

	if opened_import_window:
		changed_selected_import, selected_import = import_ui.draw("Imports")
	if opened_category_window:
		changed_categories, selected_categories = category_ui.draw("Categories")
	if opened_analysis_config_window:
		changed_config = analysis_ui.draw_config("Config", categories=selected_categories)

	if (changed_selected_import or changed_categories or changed_config) and analysis_ui.can_analyse(selected_import, selected_categories):
		analysis_reports = analysis_ui.analyse(selected_import, selected_categories)

	if opened_analysis_categorical_window:
		analysis_ui.draw_categorical("Analysis", analysis_reports, selected_categories)
	if opened_analysis_status_window:
		analysis_ui.draw_status("Evolution", analysis_reports)

	app.render()

app.shutdown()
