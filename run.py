from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx, implot
from analysis import AnalysisUI
from app import App

from lcl import Category, Import, amount, from_specific

app = App()

categories = [
]

implot.create_context()

imported = []
import_file_dialog = None
import_selected = None

analysis_ui = AnalysisUI(categories)

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:
				clicked_import, _ = imgui.menu_item("Import", None, None)
				if clicked_import:
					import_file_dialog = pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect)

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

	analysis_ui.draw(import_selected)

	app.render()

app.shutdown()
