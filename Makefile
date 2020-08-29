rom ?= roms/Chip8 Picture.ch8
run:
	env/bin/python ./main.py "$(rom)"

setup-env:
	python3 -m venv env --prompt chip8

pip:
	env/bin/pip install -r requirements.txt

.PHONY: setup
setup: setup-env pip
