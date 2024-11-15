from copy import copy
from enum import Enum
import random
import string
from imgui_bundle import ImVec4, imgui, imgui_ctx
from datetime import datetime

class LogEntry:

	class Level(Enum):
		DEBUG = ImVec4(0, 1, 0, 1)
		INFO = ImVec4(1, 1, 1, 1)
		WARN = ImVec4(1, 1, 0, 1)
		ERR = ImVec4(1, 0, 0, 1)

	def __init__(self, timestamp : datetime, level : Level, origin : str, message : str):
		self.timestamp : datetime = timestamp
		self.level : LogEntry.Level = level
		self.origin : str = origin
		self.message : str = message

class Channel:
	def __init__(self, size : int, min_level : LogEntry.Level = LogEntry.Level.INFO, max_level : LogEntry.Level = LogEntry.Level.ERR):
		self.entries : list[LogEntry] = copy([])
		self.min_level : LogEntry.Level = min_level
		self.max_level : LogEntry.Level = max_level
		self.size : int = size

	def log(self, entry : LogEntry):
		idx_min = list(LogEntry.Level).index(self.min_level)
		idx_max = list(LogEntry.Level).index(self.max_level)
		idx_entry = list(LogEntry.Level).index(entry.level)
		if idx_entry < idx_min or idx_entry > idx_max:
			return
		self.entries.append(entry)
		if len(self.entries) > self.size:
			self.entries = self.entries[-self.size:]

channels : dict[str, Channel] = {
	"default" : Channel(1000, min_level=LogEntry.Level.DEBUG, max_level=LogEntry.Level.ERR)
}

def log(channel : str, origin : str, message : str, level : LogEntry.Level = LogEntry.Level.INFO):
	if channel not in channels:
		channels[channel] = Channel(1000)
	channels[channel].log(LogEntry(datetime.now(), level, origin, message))

class UI:

	def __init__(self):
		self.selected_tab : str = "default"
		self.auto_scroll_on_add : bool = True
		self.last_timestamp : datetime = datetime.now()
		self.displayed_log_level : list[LogEntry.Level] = list(LogEntry.Level)

	def menu(self, title : str) -> bool:
		force_scroll = False
		with imgui_ctx.begin_menu(title, True) as menu:
			if menu:
				if imgui.menu_item("Clear", None, None)[0]:
					force_scroll = True
					channels[self.selected_tab].entries = []
				if imgui.menu_item("Clear All", None, None)[0]:
					force_scroll = True
					for channel in channels.values():
						channel.entries = []
				self.auto_scroll_on_add = imgui.menu_item("Auto Scroll", None, self.auto_scroll_on_add)[1]
				for level in LogEntry.Level:
					if imgui.menu_item(f"{level}", None, level in self.displayed_log_level)[0]:
						force_scroll = True
						if level in self.displayed_log_level:
							self.displayed_log_level.remove(level)
						else:
							self.displayed_log_level.append(level)
		return force_scroll

	def draw_console(self, title : str, force_scroll : bool = False) -> str:
		with imgui_ctx.begin(title) as window:
			if window:
				# if imgui.button("Random log"):
				# 	log("default", "random", ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(1, 100))), random.choice(list(LogEntry.Level)))
				with imgui_ctx.tree_node("Log levels") as tree:
					if tree:
						for level in LogEntry.Level:
							if imgui.checkbox(f"{level}", level in self.displayed_log_level)[0]:
								force_scroll = True
								if level in self.displayed_log_level:
									self.displayed_log_level.remove(level)
								else:
									self.displayed_log_level.append(level)
				with imgui_ctx.begin_tab_bar("##log tabs"):
					for tab in channels.keys():
						with imgui_ctx.begin_tab_item(tab) as tab_item:
							if tab_item:
								# force_scroll = True
								self.selected_tab = tab
				with imgui_ctx.begin_list_box("##log", imgui.get_content_region_avail()):
					with imgui_ctx.begin_table('##log entry', column=3, flags=imgui.TableFlags_.sizing_fixed_fit | imgui.TableFlags_.borders_inner):
						imgui.table_setup_column("##timestamps", imgui.TableColumnFlags_.width_fixed)
						imgui.table_setup_column("##origin", imgui.TableColumnFlags_.width_fixed)
						imgui.table_setup_column("##message", imgui.TableColumnFlags_.width_stretch)
						for entry in channels[self.selected_tab].entries:
							if entry.level not in self.displayed_log_level:
								continue
							imgui.table_next_row()
							with imgui_ctx.push_style_color(imgui.Col_.text, entry.level.value):
								imgui.table_next_column()
								imgui.text(entry.timestamp.strftime("[%Y/%m/%d-%H:%M:%S]"))
								imgui.table_next_column()
								imgui.text_unformatted(entry.origin)
								imgui.table_next_column()
								imgui.text_wrapped(entry.message)
						if force_scroll or (self.auto_scroll_on_add and channels[self.selected_tab].entries[-1].timestamp > self.last_timestamp):
							imgui.set_scroll_here_y(1.0)
							self.last_timestamp = channels[self.selected_tab].entries[-1].timestamp if len(channels[self.selected_tab].entries) > 0 else self.last_timestamp
		return self.selected_tab
