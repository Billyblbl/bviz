from functools import total_ordering
import json
from os import path
from typing import Any, Callable
from console import LogEntry as Log, log

#* Version IDentifier
@total_ordering
class VID:

	def __init__(self, major : int, minor : int, patch : int):
		self.major : int = major
		self.minor : int = minor
		self.patch : int = patch

	def __str__(self):
		return f"{self.major}.{self.minor}.{self.patch}"

	@staticmethod
	def from_string(s : str):
		return VID(*map(int, s.split('.')))

	def __eq__(self, other):
		return self.major == other.major and self.minor == other.minor and self.patch == other.patch

	def __lt__(self, other):
		if self.major != other.major:
			return self.major < other.major
		if self.minor != other.minor:
			return self.minor < other.minor
		return self.patch < other.patch

	def valid_upgrade(self, old_version) -> bool:
		return self.major == old_version.major and self >= old_version

class Format:
	def __init__(self, id : str, version : VID, parser : Callable[[Any, VID, str], Any], serialiser : Callable[[Any, str], Any]):
		self.id = id
		self.version = version
		self.parser = parser
		self.serialiser = serialiser

FormatMap : dict[str, Format] = {}

def save(filename : str, fmt : Format | str, content : Any):
	try:
		if fmt is str:
			fmt = FormatMap[fmt]
		with open(filename, 'w') as out:
			json.dump({
				'format' : fmt.id,
				'version' : str(fmt.version),
				'content' : fmt.serialiser(content, filename)
			}, out)
	except Exception as e:
		log("default", "VJF", f"failed to save {filename} : {e}", Log.Level.ERR)

def load(filename : str, expected_fmt : Format | str | None = None) -> tuple[Any, Format, VID] | None:
	try:
		with open(filename, "r") as inp:
			if inp is None:
				raise Exception("File not found")
			data = json.load(inp)
			version = VID.from_string(data['version'])
			fmt = FormatMap[data['format']]

			if expected_fmt is not None:
				if expected_fmt is str:
					expected_fmt = FormatMap[expected_fmt]
				assert fmt == expected_fmt, f"Protocol mismatch: {fmt.id} != {expected_fmt.id}"
			assert fmt.version.valid_upgrade(version), f"Load upgrade impossible, incompatible version {version}, current is {fmt.version} (will only upgrade when major version match)"

			content = fmt.parser(data['content'], version, path.abspath(filename))
			return content, fmt, version
	except Exception as e:
		log("default", "VJF", f"failed to load {filename} : {e}", Log.Level.ERR)
	return None

class FileSlot:

	def __init__(self, path : str = None, format_id : str = None, content : Any = None):
		self.path = path
		self.format_id = format_id
		self.content = content
		self.dirty = True

	def save(self, path_override : str = None, format_override : str = None, content_override : dict = None):
		if path_override:
			self.path = path_override
		if content_override:
			self.content = content_override
		if format_override:
			self.format_id = format_override
		assert(self.path is not None)
		assert(self.format_id is not None)
		save(self.path, FormatMap[self.format_id], self.content)
		self.dirty = False

	def load(self, path_override : str = None, format_override : str = None) -> Any:
		if path_override:
			self.path = path_override
		if format_override:
			self.format_id = format_override
		assert(self.path is not None)
		res = load(self.path, expected_fmt=FormatMap[self.format_id] if self.format_id else None)
		if res is None:
			return None
		content, fmt, version = res
		if self.format_id is None:
			self.format_id = fmt.id
		self.dirty = version < fmt.version
		self.content = content
		return content

	@staticmethod
	def from_file(path : str, format_id : str = None):
		new = FileSlot(path, format_id)
		res = new.load()
		return new if res is not None else None
