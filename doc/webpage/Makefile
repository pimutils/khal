
PELICAN=pelican
PELICANOPTS=-t pycarddav_theme

BASEDIR=$(PWD)
INPUTDIR=$(BASEDIR)/src
OUTPUTDIR=$(BASEDIR)/output
CONFFILE=$(BASEDIR)/pelican.conf.py

SSH_HOST=lostpackets.de
SSH_USER=geier
SSH_TARGET_DIR=lostpackets.de/khal/


help:
	@echo 'Makefile for a pelican Web site                                       '
	@echo '                                                                      '
	@echo 'Usage:                                                                '
	@echo '   make html                        (re)generate the web site         '
	@echo '   make clean                       remove the generated files        '
	@echo '   ftp_upload                       upload the web site using FTP     '
	@echo '   ssh_upload                       upload the web site using SSH     '
	@echo '   dropbox_upload                   upload the web site using Dropbox '
	@echo '                                                                      '

assemble: ../parts/about.rst ../parts/license.rst ../parts/usage.rst ../parts/misc.rst
	rm -f src/pages/usage.rst src/pages/about.rst
	echo 'Usage\n=====\n' > src/pages/usage.rst
	cat ../parts/usage.rst >> src/pages/usage.rst
	cat ../parts/about.rst ../parts/license.rst > src/pages/about.rst
	cat ../parts/faq.rst > src/pages/faq.rst

test: html
	cd output && python -mSimpleHTTPServer

html: clean assemble $(OUTPUTDIR)/index.html
	@echo 'Done'

$(OUTPUTDIR)/%.html:
	$(PELICAN) $(INPUTDIR) -o $(OUTPUTDIR) -s $(CONFFILE) $(PELICANOPTS)

clean:
	rm -fr $(OUTPUTDIR)
	mkdir $(OUTPUTDIR)


rsync_upload: banner
	rsync -rvz -e ssh $(OUTPUTDIR)/* $(SSH_USER)@$(SSH_HOST):$(SSH_TARGET_DIR)

#ssh_upload: $(OUTPUTDIR)/index.html
#	scp -r $(OUTPUTDIR)/* $(SSH_USER)@$(SSH_HOST):$(SSH_TARGET_DIR)


github: $(OUTPUTDIR)/index.html
	ghp-import $(OUTPUTDIR)
	git push origin gh-pages

banner: html
	find output -type f -exec sed -i 's#<strong>New</strong>#<span class=\"label label-success\">New</span>#g' {} \;
	find output -type f -exec sed -i 's#<strong>Warning</strong>#<span class=\"label label-important\">Warning</span>#g' {} \;
	find output -type f -exec sed -i 's#<strong>Attention</strong>#<span class=\"label label-warning\">Attention</span>#g' {} \;

.PHONY: html help clean ssh_upload github test
