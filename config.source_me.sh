if [ -d .venv ]; then
	echo "activating"
	source .venv/Scripts/activate
else
	echo "creating venv"
	python -m venv .venv
	echo "activating"
	source .venv/Scripts/activate
	echo "installing dependencies"
	pip install -r requirements.txt
fi
