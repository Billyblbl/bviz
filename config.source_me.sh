if [ -d .venv ]; then
	source .venv/Scripts/activate
else
	python -m venv .venv
	source .venv/Scripts/activate
	pip install -r requirements.txt
fi
