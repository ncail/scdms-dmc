Tools for extracting run information from SuperCDMS DMC jobs using CATS as a supporting library 

Combine root files
hadd combined_test.root *.root

Run mac file
sbatch submit.slrm

Be sure to specify array in slrm file so that they are unique from other runs if intent on combining later so that eventid is unique 
