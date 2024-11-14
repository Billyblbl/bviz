from copy import copy
from enum import Enum
import json
from typing import Any
from imports import amount
import re
from imgui_bundle import portable_file_dialogs as pfd #type: ignore
from imgui_bundle import imgui, imgui_ctx

class Category:
	def __init__(self, name, predicate = lambda _: False, sub = []):
		self.name = name
		self.predicate = predicate
		self.sub = sub
		if self.sub:
			self.sub.append(Category(name + ".other"))
		self.active = True

def categorise(parent_category : str, entries: list[dict], categories : list[Category] = []) -> dict:
	analysis = dict()
	unused_entries = entries.copy()
	for cat in categories:
		sub_entries = [e for e in entries if cat.predicate(e)]
		analysis |= { cat.name : sum(amount(e) for e in sub_entries) } | categorise(cat.name, sub_entries, cat.sub)
		unused_entries = [e for e in unused_entries if e not in sub_entries]
	if parent_category != "" and categories: #* last category is always "*.other" if has parent & not empty
		analysis[categories[-1].name] = sum(amount(e) for e in unused_entries) if unused_entries else 0
	return analysis

class CategoryBlueprint:

	class Filter(Enum):
		Regex = 0
		Comparison = 1
		MovementTarget = 2
		Custom = 3
		# TODO: implement
		# QuerySQL = 4
		# Multiple = 5

	FilterConfig = str | tuple[str, str] | tuple[str, float] | None

	def __init__(self, name : str = "unnamed", filter_ : Filter = Filter.Regex, config : FilterConfig = ("", ""), sub : list = []) -> None:
		self.name : str = copy(name)
		self.filter : CategoryBlueprint.Filter = filter_
		self.config : CategoryBlueprint.FilterConfig = copy(config)
		self.sub : list[CategoryBlueprint] = copy(sub)

	def to_dict(self) -> dict:
		return {
			"name" : self.name,
			"filter" : self.filter.name,
			"config" : self.config,
			"sub" : [sub.to_dict() for sub in self.sub],
		}

	@staticmethod
	def from_dict(dct : dict):
		return CategoryBlueprint(
			dct["name"],
			CategoryBlueprint.Filter[dct["filter"]],
			dct["config"],
			[CategoryBlueprint.from_dict(sub) for sub in dct["sub"]]
		)

def build_category_tree(blueprint : CategoryBlueprint) -> Category:
	predicate = lambda _: False
	match blueprint.filter:
		case CategoryBlueprint.Filter.Regex:
			predicate = lambda e: re.search(blueprint.config[0], e[blueprint.config[1]]) != None # config is tuple[str, str]
		case CategoryBlueprint.Filter.Comparison:
			match blueprint.config[0]:
				case "==":
					predicate = lambda e: amount(e) == blueprint.config[1] # config is numerical
				case "!=":
					predicate = lambda e: amount(e) != blueprint.config[1] # config is numerical
				case ">=":
					predicate = lambda e: amount(e) >= blueprint.config[1] # config is numerical
				case "<=":
					predicate = lambda e: amount(e) <= blueprint.config[1] # config is numerical
				case ">":
					predicate = lambda e: amount(e) > blueprint.config[1] # config is numerical
				case "<":
					predicate = lambda e: amount(e) < blueprint.config[1] # config is numerical
		case CategoryBlueprint.Filter.MovementTarget:
			predicate = lambda e: re.search(blueprint.config, e["label_in"]) != None or re.search(blueprint.config, e["label_out"]) != None # config is str
		case CategoryBlueprint.Filter.Custom:
			res = None
			try:
				res = eval("lambda entry: " + blueprint.config)
			except:
				pass
			if res:
				predicate = res
			else:
				print("invalid custom predicate for {blueprint.name}: lambda entry: ".format(blueprint=blueprint), blueprint.config)
				predicate = lambda _: False
	subs = [build_category_tree(sub) for sub in blueprint.sub]
	return Category(blueprint.name, predicate, subs)

def table_push_column(id):
	imgui.table_next_column()
	return imgui_ctx.push_id(id)


class UI:
	def __init__(self):
		self.blueprints : list[CategoryBlueprint] = []
		self.categories : list[Category] = []
		self.file_op = None
		self.file_op_target = None
		self.selection_blueprints = None

	class FileOp(Enum):
		LOAD = 0
		SAVE = 1

	def load_category(self, destination) -> CategoryBlueprint:
		self.file_op = (UI.FileOp.LOAD, pfd.open_file("Select category file", filters=["*.json"]))
		self.file_op_target = destination

	def save_category(self, blueprints : list[CategoryBlueprint]) -> None:
		self.file_op = (UI.FileOp.SAVE, pfd.save_file("Save category", "-".join([cat.name for cat in blueprints]) + ".json", filters=["*.json"]))
		self.file_op_target = blueprints

	def draw(self, title : str = "Categories") -> tuple[bool, list[Category]]:
		changed_used_categories = False
		with imgui_ctx.begin(title) as window:
			if window:
				if self.file_op:
					match self.file_op[0]:
						case UI.FileOp.LOAD:
							if self.file_op[1].ready():
								filepaths = self.file_op[1].result()
								for filepath in filepaths:
									try:
										with open(filepath, "r") as source:
											if source is None:
												raise Exception("File not found")
											for d in json.load(source):
												self.file_op_target.append(CategoryBlueprint.from_dict(d))
												self.selection_blueprints = self.file_op_target[-1]
									except Exception as e:
										print("failed to load {} : {}".format(filepath, e))
								self.file_op = None
								self.file_op_target = None
						case UI.FileOp.SAVE:
							if self.file_op[1].ready():
								filepath = self.file_op[1].result()
								if (filepath):
									with open(filepath, "w") as out:
										json.dump([cat.to_dict() for cat in self.file_op_target], out)
								self.file_op = None
								self.file_op_target = None

				with imgui_ctx.begin_table("##category_sets", 3, flags=imgui.TableFlags_.resizable):

					with table_push_column("##Used categories column"):
						if imgui.button("Reset"):
							self.categories = []
							changed_used_categories = True
						with imgui_ctx.begin_list_box("##blueprints", imgui.get_content_region_avail()):
							with imgui_ctx.begin_table("##blueprints content", 2, flags=imgui.TableFlags_.resizable):
								for category in self.categories:
									imgui.table_next_row()
									with imgui_ctx.push_id(category.name):
										imgui.table_next_column()
										imgui.text(category.name)
										imgui.table_next_column()
										if imgui.button("X"):
											self.categories.remove(category)
											changed_used_categories

					with table_push_column("##category blueprint hierarchy column"):
						if imgui.button("Load"):
							self.load_category(destination=self.blueprints)
						imgui.same_line()
						if imgui.button("Save"):
							self.save_category(self.blueprints)
						imgui.same_line()
						if imgui.button("Use all"):
							self.categories = [build_category_tree(blueprint) for blueprint in self.blueprints]
							changed_used_categories = True
						imgui.same_line()
						if imgui.button("Reset"):
							self.blueprints = []
						with imgui_ctx.begin_list_box("##hierachy", imgui.get_content_region_avail()):
							with imgui_ctx.begin_table("##hierarchy content", 2, flags=imgui.TableFlags_.resizable | imgui.TableFlags_.borders_inner):
								def recursive_blueprints_edit(blueprints : list[CategoryBlueprint]) -> bool:
									changed_rec = False
									for blueprint, index in zip(blueprints, range(len(blueprints))):
										with imgui_ctx.push_id(index):
											imgui.table_next_row()
											imgui.table_next_column()
											_, selected = imgui.selectable(blueprint.name, p_selected=self.selection_blueprints == blueprint)
											if selected:
												self.selection_blueprints = blueprint
											imgui.table_next_column()

											if imgui.button("+"):
												blueprint.sub.append(CategoryBlueprint())
												self.selection_blueprints = blueprint.sub[-1]
											imgui.same_line()
											if imgui.button("Load"):
												self.load_category(blueprint.sub)
											imgui.same_line()
											if imgui.button("Use"):
												self.categories.append(build_category_tree(blueprint))
												changed_rec = True
											imgui.same_line()
											if imgui.button("Save"):
												self.save_category([blueprint])
											imgui.same_line()
											if imgui.button("X"):
												blueprints.remove(blueprint)
												if self.selection_blueprints == blueprint:
													self.selection_blueprints = None
											imgui.indent()
											changed_rec |= recursive_blueprints_edit(blueprint.sub)
											imgui.unindent()
									return changed_rec
								changed_used_categories |= recursive_blueprints_edit(self.blueprints)
								imgui.table_next_row()
								imgui.table_next_column()
								if imgui.button("+"):
									self.blueprints.append(CategoryBlueprint())
									self.selection_blueprints = self.blueprints[-1]
								imgui.same_line()
								if imgui.button("Load"):
									self.load_category(self.blueprints)

					with table_push_column("##category blueprint details column"):
						if self.selection_blueprints:
							_, self.selection_blueprints.name = imgui.input_text("Name", self.selection_blueprints.name)
							changed_filter, idx = imgui.combo("Filter", self.selection_blueprints.filter.value, [f.name for f in list(CategoryBlueprint.Filter)])
							self.selection_blueprints.filter = CategoryBlueprint.Filter(idx)
							imgui.text("Filter Config")
							match self.selection_blueprints.filter:
								case CategoryBlueprint.Filter.Regex:
									if changed_filter:
										self.selection_blueprints.config = ("", "")
									_, reg = imgui.input_text("Regex", self.selection_blueprints.config[0])
									_, col = imgui.input_text("Column", self.selection_blueprints.config[1])
									self.selection_blueprints.config = (reg, col)
								case CategoryBlueprint.Filter.Comparison:
									if changed_filter:
										self.selection_blueprints.config = ("==", 0)
									comparators = ["==", "!=", ">", "<", ">=", "<="]
									_, comp_idx = imgui.combo("Comparison", comparators.index(self.selection_blueprints.config[0]), comparators)
									_, comp_operand = imgui.input_float("Operand", self.selection_blueprints.config[1])
									self.selection_blueprints.config = (comparators[comp_idx], comp_operand)
								case CategoryBlueprint.Filter.MovementTarget:
									if changed_filter:
										self.selection_blueprints.config = ""
									_, self.selection_blueprints.config = imgui.input_text("Regex", self.selection_blueprints.config)
								case CategoryBlueprint.Filter.Custom:
									if changed_filter:
										self.selection_blueprints.config = "False"
									_, self.selection_blueprints.config = imgui.input_text("Predicate", self.selection_blueprints.config)
						else:
							imgui.begin_disabled()
							imgui.input_text("Name", "------------")
							imgui.combo("Filter", 0, list(f.name for f in CategoryBlueprint.Filter))
							imgui.input_text("Config", "")
							imgui.end_disabled()

		return changed_used_categories, self.categories
