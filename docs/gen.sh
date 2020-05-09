cp ../README.md manual/readme.md
sphinx-apidoc -Mo api ../wecs --separate -t _templates/apidoc
make html
