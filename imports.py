
import csv
from datetime import datetime
from enum import Enum
import json
from os import path
from schedule import Timespan, Granularity, input_date
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx

bank_statement_fields = ["date", "amount", "type", "account", "label_out", "label_in", "tbd", "note"]
def read_bank_statement(filename) -> list[dict]:
	with open(filename, encoding="utf-8-sig") as file:
		reader = csv.DictReader(file, fieldnames=bank_statement_fields, delimiter=';')
		return [row for row in reader]

class Import:

	def __init__(self, filename : str = None):
		self.filename : str = filename if filename else "unsaved.json"
		self.begin : datetime = None
		self.end : datetime = None
		self.files: list[str] = []
		self.entries : list[dict] = []
		self.version_id = 0
		if filename:
			self.load(filename)

	@staticmethod
	def from_file(filename, datetime_fmt = "%Y/%m/%d") -> "Import":
		new = Import()
		new.load(filename, datetime_fmt=datetime_fmt)
		return new

	def to_dict(self, datetime_fmt = "%d/%m/%Y"):
		if self.begin is None or self.end is None:
			raise Exception("Timespan not set")
		return {
			'begin' : self.begin.strftime(datetime_fmt),
			'end' : self.end.strftime(datetime_fmt),
			'files' : [path.relpath(f, path.dirname(self.filename)) for f in self.files],
		}

	def valid(self) -> bool:
		return self.begin is not None and self.end is not None

	def save(self, filename: str = None, datetime_fmt : str = "%Y/%m/%d"):
		try:
			if filename:
				self.filename = filename
			with open(self.filename, 'w') as out:
				json.dump(self.to_dict(datetime_fmt=datetime_fmt), out)
		except Exception as e:
			print(e)

	def load(self, filename = None, datetime_fmt = "%Y/%m/%d"):
		try:
			if filename:
				self.filename = filename
			with open(self.filename) as inp:
				if inp is None:
					raise Exception("File not found")
				data = json.load(inp)
				self.begin = datetime.strptime(data['begin'], datetime_fmt)
				self.end = datetime.strptime(data['end'], datetime_fmt)
				self.files = [path.dirname(self.filename) + '/' + f for f in data['files']]
				self.load_entries()
		except Exception as e:
			print('failed to load {} : {}'.format(self.filename, e))

	def read_entries(self, apply_filter = True):
		entries = []
		[entries := entries + read_bank_statement(f) for f in self.files]
		if apply_filter and self.valid():
			entries = [e for e in entries if datetime.strptime(e['date'], "%d/%m/%Y") >= self.begin and datetime.strptime(e['date'], "%d/%m/%Y") <= self.end]
		return entries

	def load_entries(self):
		print("loading entries")
		self.entries = self.read_entries()
		self.version_id += 1

	def section(self, timespan : Timespan):
		return filter(lambda e: e['date'] >= timespan.begin and e['date'] <= timespan.end, self.entries())

	def select_dates_from_contents(self):
		entries = self.read_entries(apply_filter=False)
		self.begin = min(datetime.strptime(e['date'], "%d/%m/%Y") for e in entries)
		self.end = max(datetime.strptime(e['date'], "%d/%m/%Y") for e in entries)

	class Section:
		def __init__(self, timespan : Timespan, entries = []):
			self.timespan = timespan
			self.entries = entries

	def sectionned(self, granularity : Granularity, count : int = 1) -> list[Section]:
		#* Create sections (thats a whole lot of discarded parsing, easy perf gain here @OPTI)
		if self.entries is None or len(self.entries) == 0:
			return []
		total_timespan = Timespan(
			min(datetime.strptime(e['date'], "%d/%m/%Y") for e in self.entries).replace(hour=0, minute=0, second=0),
			max(datetime.strptime(e['date'], "%d/%m/%Y") for e in self.entries).replace(hour=23, minute=59, second=59)
		)
		sections = [Import.Section(t, []) for t in total_timespan.sectionned(granularity, count)]
		#* Distribute entries in sections
		for e in self.entries:
			date = datetime.strptime(e['date'], "%d/%m/%Y")
			next((s for s in sections if date >= s.timespan.begin and date <= s.timespan.end)).entries.append(e)
		return sections

def column(data : list[dict], field : str):
	return [row[field] for row in data]

#* Extract the amount of money change in a bank entry as a float (french bank uses ',' instead of '.')
def amount(entry : dict) -> float:
	return float(entry['amount'].replace(',', '.'))

def from_specific(entry : dict, person : str) -> bool:
	return person in entry['label_in'] or person in entry['label_out']

# region UI
class UI:

	class FileOperation(Enum):
		NOOP = 0
		LOAD_IMPORTS = 1
		SAVE_IMPORTS = 2
		SECLECT_SOURCES = 3

		def make_noop():
			return (UI.FileOperation.NOOP, None)

	def __init__(self):
		self.file_dialog : tuple[UI.FileOperation, pfd.open_file | pfd.save_file] = UI.FileOperation.make_noop()
		self.file_op_target : Import = None
		self.imported : list[Import] = []
		self.selected_import : Import = None
		self.selected_source_file : str = None
		self.auto_select_import_dates : bool = False

	def load_imports(self) -> bool:
		self.file_dialog = (UI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))

	def save_import(self, imp : Import) -> bool:
		self.file_dialog = (UI.FileOperation.SAVE_IMPORTS, pfd.save_file("Save as", imp.filename, filters=["*.json"]))
		self.file_op_target = imp

	def try_select_sources(self) -> bool:
		if self.selected_import:
			self.file_dialog = (UI.FileOperation.SECLECT_SOURCES, pfd.open_file("Select source files", filters=["*.csv"], options=pfd.opt.multiselect))
		else:
			print("No import selected")

	def save_button(self, imp : Import) -> bool:
		pressed = False
		if not imp or not imp.valid():
			imgui.begin_disabled()
		if imgui.button("Save"):
			pressed = True
			self.save_import(imp)
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
			self.load_imports()
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
				if self.file_op_ready(UI.FileOperation.SAVE_IMPORTS):
					filepath = self.file_dialog[1].result()
					if filepath:
						print(filepath)
						self.selected_import.save(filename=filepath)
					self.file_dialog = UI.FileOperation.make_noop()
					self.file_op_target = None
				imgui.same_line()
				self.load_button()
				if self.file_op_ready(UI.FileOperation.LOAD_IMPORTS):
					for filepath in self.file_dialog[1].result():
						print(filepath)
						self.imported.append(Import.from_file(filepath))
					self.selected_import = self.imported[-1]
					self.file_dialog = UI.FileOperation.make_noop()
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
								_, selected = imgui.selectable(path.basename(import_data.filename), self.selected_import.filename == import_data.filename if self.selected_import else False, imgui.SelectableFlags_.allow_double_click)
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
						self.file_dialog = (UI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))
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
									_, selected = imgui.selectable(path.basename(file), self.selected_source_file == file, imgui.SelectableFlags_.allow_double_click)
									if selected:
										self.selected_source_file = file
									imgui.table_next_column()
									if imgui.button("X"):
										self.selected_import.files.remove(file)
										self.selected_import.load_entries()
										self.selected_source_file = None
						if (imgui.button("+")):
							self.try_select_sources()
						if self.file_op_ready(UI.FileOperation.SECLECT_SOURCES):
							for filepath in self.file_dialog[1].result():
								self.selected_import.files.append(filepath)
							self.selected_import.load_entries()
							self.file_dialog = UI.FileOperation.make_noop()
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
# endregion ui
