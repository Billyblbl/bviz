import calendar
from datetime import datetime
from enum import Enum
import os
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx, implot
from analysis import AnalysisUI
from app import App

from lcl import Category, Import, amount, from_specific

app = App()

categories = [
]

implot.create_context()

def input_date(label : str, date : datetime) -> tuple[bool, datetime]:
	changed = False
	changed, num_dates = imgui.input_int3(label, [date.day if date else 1, date.month if date else 1, date.year if date else 1])
	d, m, y = num_dates
	m = max(1, min(12, m))
	d = max(1, min(calendar.monthrange(y, m)[1], d))
	if (changed and date):
		date = date.replace(day=d, month=m, year=y)
	elif changed:
		date = datetime(year=y, month=m, day=d)
	return changed, date

class ImportUI:

	class FileOperation(Enum):
		NOOP = 0
		LOAD_IMPORTS = 1
		SAVE_IMPORTS = 2
		SECLECT_SOURCES = 3

		def make_noop():
			return (ImportUI.FileOperation.NOOP, None)

	def __init__(self):
		self.file_dialog : tuple[ImportUI.FileOperation, pfd.open_file | pfd.save_file] = ImportUI.FileOperation.make_noop()
		self.file_op_target : Import = None
		self.imported : list[Import] = []
		self.selected_import : Import = None
		self.selected_source_file : str = None
		self.auto_select_import_dates : bool = False

	def save_button(self, imp : Import) -> bool:
		pressed = False
		if not imp or not imp.valid():
			imgui.begin_disabled()
		if imgui.button("Save"):
			pressed = True
			self.file_dialog = (ImportUI.FileOperation.SAVE_IMPORTS, pfd.save_file("Save as", imp.filename, filters=["*.json"]))
			self.file_op_target = imp
		if not imp or not imp.valid():
			imgui.end_disabled()
		return pressed

	def reload_button(self, imp : Import) -> bool:
		pressed = False
		if not imp or not imp.valid():
			imgui.begin_disabled()
		if imgui.button("Reload"):
			pressed = True
			imp.load()
		if not imp or not imp.valid():
			imgui.end_disabled()
		return pressed

	def load_button(self) -> bool:
		pressed = False
		if imgui.button("Load"):
			self.file_dialog = (ImportUI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))
		return pressed

	def remove_button(self, imp : Import) -> bool:
		pressed = False
		if not imp:
			imgui.begin_disabled()
		if imgui.button("X"):
			pressed = True
			if self.selected_import == imp:
				self.selected_import = None
			self.imported.remove(imp)
		if not imp:
			imgui.end_disabled()
		return pressed

	def file_op_ready(self, operation) -> bool:
		return self.file_dialog[0] == operation and self.file_dialog[1].ready()

	def draw(self) -> None:
		with imgui_ctx.begin("Imports"):

			with imgui_ctx.begin_table("##imports table", 3, flags=imgui.TableFlags_.resizable):
				#region imports list column
				imgui.table_next_column()
				if imgui.button("New"):
					self.imported.append(Import())
					self.selected_import = self.imported[-1]
				imgui.same_line()
				self.save_button(self.selected_import)
				if self.file_op_ready(ImportUI.FileOperation.SAVE_IMPORTS):
					filepath = self.file_dialog[1].result()
					if filepath:
						print(filepath)
						self.selected_import.save(filename=filepath)
					self.file_dialog = ImportUI.FileOperation.make_noop()
					self.file_op_target = None
				imgui.same_line()
				self.load_button()
				if self.file_op_ready(ImportUI.FileOperation.LOAD_IMPORTS):
					for filepath in self.file_dialog[1].result():
						print(filepath)
						self.imported.append(Import.from_file(filepath))
					self.selected_import = self.imported[-1]
					self.file_dialog = ImportUI.FileOperation.make_noop()
				imgui.same_line()
				self.reload_button(self.selected_import)
				imgui.same_line()
				self.remove_button(self.selected_import)

				with imgui_ctx.begin_list_box("##imports", imgui.get_content_region_avail()):
					with imgui_ctx.begin_table('##import entry', 2, flags=imgui.TableFlags_.resizable):
						for import_data in self.imported:
							with imgui_ctx.push_id(import_data.filename):
								imgui.table_next_row()
								imgui.table_next_column()
								_, selected = imgui.selectable(os.path.basename(import_data.filename), self.selected_import.filename == import_data.filename if self.selected_import else False, imgui.SelectableFlags_.allow_double_click)
								if selected:
									self.selected_import = import_data
								imgui.table_next_column()
								self.save_button(import_data)
								imgui.same_line()
								self.reload_button(import_data)
								imgui.same_line()
								self.remove_button(import_data)
					if imgui.button("+"):
						self.imported.append(Import())
						self.selected_import = self.imported[-1]
					imgui.same_line()
					if imgui.button("Load"):
						self.file_dialog = (ImportUI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))
				#endregion imports list column

				#region import config column
				imgui.table_next_column()
				if (self.selected_import):

					if len(self.selected_import.files) == 0:
						imgui.begin_disabled()
					if imgui.button("Select dates from contents"):
						self.selected_import.select_dates_from_contents()
					if len(self.selected_import.files) == 0:
						imgui.end_disabled()
					imgui.same_line()
					_, self.auto_select_import_dates = imgui.checkbox("Auto", self.auto_select_import_dates)

					if self.auto_select_import_dates and len(self.selected_import.files) > 0:
						self.selected_import.select_dates_from_contents()
						imgui.begin_disabled()
					changed, self.selected_import.begin = input_date("Begin", self.selected_import.begin)
					changed, self.selected_import.end = input_date("End", self.selected_import.end)
					if changed and self.selected_import.valid():
						self.selected_import.load_entries()
					if self.auto_select_import_dates and len(self.selected_import.files) > 0:
						imgui.end_disabled()

				with imgui_ctx.begin_list_box("##imports files box", imgui.get_content_region_avail()):
					if self.selected_import:
						with imgui_ctx.begin_table("##import files entry table", 2, flags=imgui.TableFlags_.resizable):
							for file in self.selected_import.files:
								with imgui_ctx.push_id(file):
									imgui.table_next_row()
									imgui.table_next_column()
									_, selected = imgui.selectable(os.path.basename(file), self.selected_source_file == file, imgui.SelectableFlags_.allow_double_click)
									if selected:
										self.selected_source_file = file
									imgui.table_next_column()
									if imgui.button("X"):
										self.selected_import.files.remove(file)
										self.selected_import.load_entries()
										self.selected_source_file = None
						if (imgui.button("+")):
							self.file_dialog = (ImportUI.FileOperation.SECLECT_SOURCES, pfd.open_file("Select source files", filters=["*.csv"], options=pfd.opt.multiselect))
						if self.file_op_ready(ImportUI.FileOperation.SECLECT_SOURCES):
							for filepath in self.file_dialog[1].result():
								self.selected_import.files.append(filepath)
							self.selected_import.load_entries()
							self.file_dialog = ImportUI.FileOperation.make_noop()
				#endregion import config column

				#region import contents column
				imgui.table_next_column()
				with imgui_ctx.begin_list_box("##imports contents box", imgui.get_content_region_avail()):
					if self.selected_import and self.selected_import.entries:
						columns = self.selected_import.entries[0].keys()
						with imgui_ctx.begin_table("##import contents table", len(columns), flags=imgui.TableFlags_.resizable):
							for c in columns:
								imgui.table_setup_column(c)
							imgui.table_headers_row()
							for entry in self.selected_import.entries:
								imgui.table_next_row()
								for c in columns:
									imgui.table_next_column()
									imgui.text(entry[c])
				#endregion import contents column

import_ui = ImportUI()
analysis_ui = AnalysisUI(categories)

while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:

				clicked_new, _ = imgui.menu_item("New", None, None)
				if clicked_new:
					pass

				clicked_import, _ = imgui.menu_item("Import", None, None)
				if clicked_import:
					import_file_dialog = pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect)

				clicked_exit, _ = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

	imgui.dock_space_over_viewport()

	import_ui.draw()
	analysis_ui.draw(import_ui.selected_import)

	app.render()

app.shutdown()
