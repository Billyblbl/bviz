import csv
import sys
import lcl
import tmp_plot

input_f = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: calc.py <input report json> [<output csv>]")
output_f = sys.argv[2] if len(sys.argv) > 2 else "default_report_output.csv"

categories = [
]

with open(output_f, 'w', newline='') as output:
	reports = [lcl.report(section, categories) for section in lcl.Import(input_f).sectionned(lcl.Import.Granularity.Month)]
	rows = [r.to_dict() for r in reports]
	writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=',')
	writer.writeheader()
	writer.writerows(rows)
tmp_plot.vizualize(output_f)
