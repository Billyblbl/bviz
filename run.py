from app import App
from imgui_bundle import imgui, imgui_ctx, implot
import imports
import analysis
from imports import amount, from_specific
from analysis import Category

app = App()

categories = [
]

implot.create_context()

import_ui = imports.UI()
analysis_ui = analysis.UI(categories)

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

	import_ui.draw()
	analysis_ui.draw(import_ui.selected_import)

	app.render()

app.shutdown()
