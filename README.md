Tools for extracting run information from SuperCDMS DMC jobs using CATS as a supporting library 

run notebook on Fir 
enter apptainer (vscode terminal in remote fir connection)
module load scdms
apptainer-shell
jupyter notebook --no-browser --port=8888

in vscode gui:
select kernel (top right if notebook file is currently in editor)
select existing jupyter server
copy url in terminal output from launching jupyter notebook
`<enter>` on localhost

