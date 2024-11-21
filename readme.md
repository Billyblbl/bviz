# BlblBankViz Project

BlblBankViz is a personal finance analysis tool designed to help users visualize and understand their banking data. The project aims to provide a user-friendly interface for importing, categorizing, and analyzing bank statements.

## About

This project was originally a simple python script using matplotlib that i clobbered together when i saw that my bank had an option to export to CSV. I've since upgraded it into a full application using [DearImGUI bundle](https://github.com/pthom/imgui_bundle) as a side project, but its still in essence a little scrappy thing, that i am making public for people that find it useful and as a portfolio piece.

## Features

* Import bank statements in csv format
* Categorize transactions using customizable filters
* Analyze spending patterns and trends
* Visualize data using interactive plots and charts
* Export analysis reports for further review

## Getting Started

1. Clone the repository: `git clone https://github.com/billyblbl/bviz.git`
2. Install dependencies:
	1. localy `source config.source_me.sh`
	2. globaly `pip install -r requirements.txt`
3. Run the application: `python run.py`

## Contributing

Contributions are welcome! If you'd like to report a bug or suggest a feature, please open an issue on the GitHub repository. For code contributions, please submit a pull request with a clear description of the changes. Do keep in mind however that due to the side-project nature of it I may not have the time to properly maintain this software. This includes managing contributions.
For priority features refer to [the todo list](todo.md)

## License

BlblBankViz is licensed under the MIT License. See [LICENSE.txt](LICENSE.TXT) for details.
