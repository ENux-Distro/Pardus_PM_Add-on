check:
	@command -v whiptail >/dev/null || echo "whiptail not installed | whiptail sisteminizde kurulu değil"
	@command -v wget >/dev/null || echo "wget not installed | wget sisteminizde kurulu değil"

.PHONY: menuconfig install uninstall clean bedrock help

SCRIPTS = Kconfig.sh install.sh helpers/bedrock.sh

install:
	chmod +x $(SCRIPTS)
	./Kconfig.sh

bedrock:
	chmod +x $(SCRIPTS)
	./helpers/bedrock.sh

help:
	chmod +x $(SCRIPTS)
	./helpers/help.sh

fullinstall:
	chmod +x $(SCRIPTS)
	./install.sh

uninstall:
	chmod +x $(SCRIPTS)
	./uninstall.sh

clean:
	rm -f .config

