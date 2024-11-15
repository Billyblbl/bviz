import csv
from datetime import datetime
from enum import Enum
from os import path
from schedule import Timespan, Granularity, input_date
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx
from console import log, LogEntry as Log
from vjf import VID, FormatMap, Format, FileSlot

bank_statement_fields = ["date", "amount", "type", "account", "label_out", "label_in", "tbd", "note"]
def read_bank_statement(filename) -> list[dict]:
	with open(filename, encoding="utf-8-sig") as file:
		reader = csv.DictReader(file, fieldnames=bank_statement_fields, delimiter=';')
		return [row for row in reader]

def load_entries(files : list[str], flt : Timespan | None = None) -> list[dict]:
	entries = []
	for f in files:
		entries.extend(read_bank_statement(f))
	if flt is not None:
		entries = [e for e in entries if datetime.strptime(e['date'], "%d/%m/%Y") >= flt.begin and datetime.strptime(e['date'], "%d/%m/%Y") <= flt.end]
	return entries

class Import:

	def __init__(self, begin : datetime = None, end : datetime = None, files : list[str] = [], entries : list[dict] = []):
		self.begin : datetime = begin
		self.end : datetime = end
		self.files: list[str] = files
		self.entries : list[dict] = entries

	def to_dict(self, pwd : str, datetime_fmt = "%Y/%m/%d"):
		if self.begin is None or self.end is None:
			raise Exception("Timespan not set")
		return {
			'begin' : self.begin.strftime(datetime_fmt),
			'end' : self.end.strftime(datetime_fmt),
			'files' : [path.relpath(f, pwd) for f in self.files],
		}

	@staticmethod
	def from_dict(data : dict, pwd : str, datetime_fmt = "%Y/%m/%d"):
		files = [pwd + '/' + f for f in data['files']]
		return Import(
			begin=datetime.strptime(data['begin'], datetime_fmt),
			end=datetime.strptime(data['end'], datetime_fmt),
			files=files,
			entries=load_entries(files=files, flt=Timespan(
				datetime.strptime(data['begin'], datetime_fmt).replace(hour=0, minute=0, second=0),
				datetime.strptime(data['end'], datetime_fmt).replace(hour=23, minute=59, second=59),
			))
		)

	def valid(self) -> bool:
		return self.begin is not None and self.end is not None

	def load_entries(self):
		self.entries = load_entries(files=self.files, flt=Timespan(self.begin, self.end) if self.begin and self.end else None)

	def section(self, timespan : Timespan):
		return filter(lambda e: e['date'] >= timespan.begin and e['date'] <= timespan.end, self.entries())

	def select_dates_from_contents(self):
		entries = load_entries(self.files)
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

FormatMap["bankviz-import"] = Format(
	id="bankviz-import",
	version=VID(0, 1, 0),
	parser=lambda data, _, filepath: Import.from_dict(data, path.dirname(filepath)),
	serialiser=lambda imp, filepath: imp.to_dict(path.dirname(filepath))
)

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
		self.file_op_target : FileSlot = None
		self.imported : list[FileSlot] = []
		self.selected_import : FileSlot = None
		self.selected_source_file : str = None
		self.auto_select_import_dates : bool = False
		self.changed_selected : bool = False

	def load_imports(self) -> bool:
		self.file_dialog = (UI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))

	def save_import(self, imp : FileSlot) -> bool:
		self.file_dialog = (UI.FileOperation.SAVE_IMPORTS, pfd.save_file("Save as", imp.path, filters=["*.json"]))
		self.file_op_target = imp

	def try_select_sources(self) -> bool:
		if self.selected_import:
			self.file_dialog = (UI.FileOperation.SECLECT_SOURCES, pfd.open_file("Select source files", filters=["*.csv"], options=pfd.opt.multiselect))
		else:
			log("default", "imports", "No import selected", Log.Level.WARN)

	def save_button(self, imp : FileSlot) -> bool:
		pressed = False
		if not imp or not imp.content.valid():
			imgui.begin_disabled()
		if imgui.button("Save"):
			pressed = True
			self.save_import(imp)
		if not imp or not imp.content.valid():
			imgui.end_disabled()
		return pressed

	def reload_button(self, imp : FileSlot) -> bool:
		pressed = False
		if not imp or not imp.content.valid():
			imgui.begin_disabled()
		if imgui.button("Reload"):
			pressed = True
			imp.load()
		if not imp or not imp.content.valid():
			imgui.end_disabled()
		return pressed

	def load_button(self) -> bool:
		pressed = False
		if imgui.button("Load"):
			self.load_imports()
		return pressed

	def remove_button(self, imp : FileSlot) -> bool:
		pressed = False
		if not imp:
			imgui.begin_disabled()
		if imgui.button("X"):
			pressed = True
			if self.selected_import == imp:
				self.selected_import = None
				self.changed_selected = True
			self.imported.remove(imp)
		if not imp:
			imgui.end_disabled()
		return pressed

	def file_op_ready(self, operation) -> bool:
		return self.file_dialog[0] == operation and self.file_dialog[1].ready()

	def get_selection(self) -> Import | None:
		return self.selected_import.content if self.selected_import else None

	def menu(self, title : str):
		self.changed_selected = False
		with imgui_ctx.begin_menu(title, True) as menu:
			if menu:
				if imgui.menu_item("New", None, None)[0]:
					self.imported.append(FileSlot(path="unsaved.json", format_id="bankviz-import", content=Import()))
					self.selected_import = self.imported[-1]
					self.changed_selected = True
				if imgui.menu_item("Load", None, None)[0]:
					self.load_imports()
				if imgui.menu_item("Reload", None, None)[0]:
					for imp in self.imported:
						imp.load()
				if not self.selected_import:
					imgui.begin_disabled()
				if imgui.menu_item("Save", None, None)[0]:
					self.save_import(self.selected_import)
				if not self.selected_import:
					imgui.end_disabled()

	def draw(self, title : str = "Imports") -> tuple[bool, Import]:
		with imgui_ctx.begin(title) as window:
			if window:
				with imgui_ctx.begin_table("##imports table", 3, flags=imgui.TableFlags_.resizable):
					#region imports list column
					imgui.table_next_column()
					if imgui.button("New"):
						self.imported.append(FileSlot(path="unsaved.json", format_id="bankviz-import", content=Import()))
						self.selected_import = self.imported[-1]
						self.changed_selected = True
					imgui.same_line()
					self.save_button(self.selected_import)
					if self.file_op_ready(UI.FileOperation.SAVE_IMPORTS):
						filepath = self.file_dialog[1].result()
						if filepath:
							self.selected_import.save(path_override=filepath)
							self.changed_selected = True
						self.file_dialog = UI.FileOperation.make_noop()
						self.file_op_target = None
					imgui.same_line()
					self.load_button()
					if self.file_op_ready(UI.FileOperation.LOAD_IMPORTS):
						for filepath in self.file_dialog[1].result():
							self.imported.append(FileSlot.from_file(filepath, format_id="bankviz-import"))
						self.selected_import = self.imported[-1] if len(self.imported) > 0 else None
						self.changed_selected = True
						self.file_dialog = UI.FileOperation.make_noop()
					imgui.same_line()
					self.reload_button(self.selected_import)
					imgui.same_line()
					self.remove_button(self.selected_import)

					with imgui_ctx.begin_list_box("##imports", imgui.get_content_region_avail()):
						with imgui_ctx.begin_table('##import entry', 2, flags=imgui.TableFlags_.resizable):
							for import_data, idx in zip(self.imported, range(len(self.imported))):
								with imgui_ctx.push_id(idx):
									imgui.table_next_row()
									imgui.table_next_column()
									just, selected = imgui.selectable(path.basename(import_data.path), self.selected_import.path == import_data.path if self.selected_import else False, imgui.SelectableFlags_.allow_double_click)
									if selected:
										self.selected_import = import_data
										if just:
											self.changed_selected = True
									imgui.table_next_column()
									self.save_button(import_data)
									imgui.same_line()
									self.reload_button(import_data)
									imgui.same_line()
									self.remove_button(import_data)
						if imgui.button("+"):
							self.imported.append(FileSlot(path="unsaved.json", format_id="bankviz-import", content=Import()))
							self.selected_import = self.imported[-1]
							self.changed_selected = True
						imgui.same_line()
						if imgui.button("Load"):
							self.file_dialog = (UI.FileOperation.LOAD_IMPORTS, pfd.open_file("Select report file", filters=["*.json"], options=pfd.opt.multiselect))
					#endregion imports list column

					#region import config column
					imgui.table_next_column()
					if (self.selected_import):
						if len(self.get_selection().files) == 0:
							imgui.begin_disabled()
						if imgui.button("Select dates from contents"):
							self.get_selection().select_dates_from_contents()
						if len(self.get_selection().files) == 0:
							imgui.end_disabled()
						imgui.same_line()
						_, self.auto_select_import_dates = imgui.checkbox("Auto", self.auto_select_import_dates)

						if self.auto_select_import_dates and len(self.get_selection().files) > 0:
							self.get_selection().select_dates_from_contents()
							imgui.begin_disabled()
						changed, self.get_selection().begin = input_date("Begin", self.get_selection().begin)
						changed, self.get_selection().end = input_date("End", self.get_selection().end)
						if changed and self.get_selection().valid():
							self.get_selection().load_entries()
							self.changed_selected = True
						if self.auto_select_import_dates and len(self.get_selection().files) > 0:
							imgui.end_disabled()

					with imgui_ctx.begin_list_box("##imports files box", imgui.get_content_region_avail()):
						if self.selected_import:
							with imgui_ctx.begin_table("##import files entry table", 2, flags=imgui.TableFlags_.resizable):
								for file in self.get_selection().files:
									with imgui_ctx.push_id(file):
										imgui.table_next_row()
										imgui.table_next_column()
										_, selected = imgui.selectable(path.basename(file), self.selected_source_file == file, imgui.SelectableFlags_.allow_double_click)
										if selected:
											self.selected_source_file = file
										imgui.table_next_column()
										if imgui.button("X"):
											self.get_selection().files.remove(file)
											self.get_selection().load_entries()
											self.changed_selected = True
											self.selected_source_file = None
							if (imgui.button("+")):
								self.try_select_sources()
							if self.file_op_ready(UI.FileOperation.SECLECT_SOURCES):
								for filepath in self.file_dialog[1].result():
									self.get_selection().files.append(filepath)
								self.get_selection().load_entries()
								self.changed_selected = True
								self.file_dialog = UI.FileOperation.make_noop()
					#endregion import config column

					#region import contents column
					imgui.table_next_column()
					with imgui_ctx.begin_list_box("##imports contents box", imgui.get_content_region_avail()):
						if self.selected_import and self.get_selection().entries:
							columns = self.get_selection().entries[0].keys()
							with imgui_ctx.begin_table("##import contents table", len(columns), flags=imgui.TableFlags_.resizable):
								for c in columns:
									imgui.table_setup_column(c)
								imgui.table_headers_row()
								for entry in self.get_selection().entries:
									imgui.table_next_row()
									for c in columns:
										imgui.table_next_column()
										imgui.text(entry[c])
					#endregion import contents column
		return self.changed_selected, self.get_selection()

# endregion ui
