import csv
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

from lcl import column

plt.ion()
plt.style.use('dark_background')

def bar_side_by_side(data, fields : list[str], **kwargs):
	timespans = column(data, "timespan")
	bar_width = 1/len(fields)
	plt.grid(visible=True, axis='both', which='both')
	for field_idx, field in enumerate(fields):
		date_x = [date_idx + field_idx * bar_width for date_idx, _ in enumerate(timespans)]
		plt.bar(x=date_x, width=bar_width, height=[float(row) for row in column(data, field)], label=field, align='edge', alpha=0.75, **kwargs)

def evolution(data, fields : list[str], start_offset = 0, **kwargs):
	timespans = [row + start_offset for row, _ in enumerate(column(data, "timespan"))]
	for field in fields:
		plt.plot(timespans, [float(row) for row in column(data, field)], label=field, **kwargs)

def vizualize(filename : str):
	with open(filename) as inp:
		reader = csv.DictReader(inp, delimiter=',')
		rows = [row for row in reader] 
		bar_side_by_side(rows, ["in"])
		bar_side_by_side(rows, ["out"])

		evolution(rows, ["movements"], 1, color='purple', lw=3, path_effects=[pe.Stroke(linewidth=4, foreground='black'), pe.Normal()])
		evolution(rows, ["status"], 1, color='white', lw=3, path_effects=[pe.Stroke(linewidth=4, foreground='black'), pe.Normal()])

		timespans = [t.split('-')[0] for t in column(rows, "timespan")] + [rows[-1].get("timespan").split('-')[1]]
		plt.legend(loc='best')
		plt.xticks(ticks=range(len(timespans)), labels=timespans)
		plt.show(block=True)
