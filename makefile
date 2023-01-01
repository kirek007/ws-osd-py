include Makefile.venv
Makefile.venv:
	curl \
		-o Makefile.fetched \
		-L "https://github.com/sio/Makefile.venv/raw/v2022.07.20/Makefile.venv"
	echo "147b164f0cbbbe4a2740dcca6c9adb6e9d8d15b895be3998697aa6a821a277d8 *Makefile.fetched" \
		&& mv Makefile.fetched Makefile.venv

.PHONY: release
release: venv
	$(VENV)/pyinstaller --onefile .\main.py -n ws_osd_gen

.PHONY: run
run: venv
	$(VENV)/python main.py

