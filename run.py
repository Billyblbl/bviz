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

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:

				clicked_import, _ = imgui.menu_item("Import", None, None)
				if clicked_import:
					import_ui.load_imports()

				clicked_exit, _ = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

	imgui.dock_space_over_viewport()

	changed_selected_import, selected_import = import_ui.draw("Imports")
	changed_categories, selected_categories = category_ui.draw("Categories")
	changed_config = analysis_ui.draw_config("Config", categories=selected_categories)

	if (changed_selected_import or changed_categories or changed_config) and selected_import is not None and selected_categories is not None:
		analysis_reports = analysis_ui.analyse(selected_import, selected_categories)

	analysis_ui.draw_categorical("Analysis", analysis_reports, selected_categories)
	analysis_ui.draw_status("Evolution", analysis_reports)

	app.render()

app.shutdown()
