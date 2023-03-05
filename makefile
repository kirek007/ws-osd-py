include Makefile.venv
Makefile.venv:
	curl \
		-o Makefile.fetched \
		-L "https://github.com/sio/Makefile.venv/raw/v2022.07.20/Makefile.venv"
	echo "147b164f0cbbbe4a2740dcca6c9adb6e9d8d15b895be3998697aa6a821a277d8 *Makefile.fetched" \
		&& mv Makefile.fetched Makefile.venv

.PHONY: release
release: venv
    pip3 install pyinstaller
	$(VENV)/pyinstaller --onefile osd_gui.py -n ws_osd_gen

.PHONY: run
run: venv show-venv
	$(VENV)/python -c 'import sys; valid=(sys.version_info > (3,9) and sys.version_info < (3,11)); sys.exit(0) if valid else sys.exit(1)' || (echo "Python 3.10 is required"; exit 1)
	$(VENV)/python osd_gui.py

