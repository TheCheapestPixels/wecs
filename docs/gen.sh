cp ../README.md manual/readme.md
for f in manual/*.md ; do pandoc $f -o $(echo $f|sed -e ''s/.md$/.rst/); done
sphinx-apidoc -Mo api ../wecs --separate -t _templates/apidoc
make html
