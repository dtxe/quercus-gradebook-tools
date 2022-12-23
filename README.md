# Scripts to help with uploading grades to Quercus (Canvas at the University of Toronto)

## Installation
These scripts were tested primarily in Windows using miniconda, but should work across all OSes.
``` bash
$ git clone https://github.com/dtxe/quercus-gradebook-tools
$ cd quercus-gradebook-tools
$ pip install -r requirements.txt
$ mkdir score_exports outputs
```

## Usage
1. Download an export of the Quercus gradebook for the course, with the relevant assignments included. Save to QuercusGradebook.csv
1. (for MATLAB Grader only) Download the UT Advanced Groups Tool course roster. Save to Roster.csv
1. Download the CSV or Excel assignment export from MATLAB grader or Quercus and save it into score_exports/
1. Execute the conversion script `python grades_to_quercus.py`, select the source file and the destination assignment
1. Import the newly created output/[assignment name].csv file into the Quercus gradebook

## grades_to_quercus.py
From MATLAB Grader Assignment reports, compute the sum of each student's grade across all problems. Or get total grade from Gradescope export.  
Then join the total grade with the UT Advanced Groups Tool student list on email, then join grades with the 
required information from the Quercus Gradebook import template.


## build_matlab_quiz_rosters.ipynb
Join Quercus Gradebook export (containing section info) with UTAGT exports (containing emails) and with a CSV of
practical time slots to generate a list of Grader courses and student emails that should be invited.
- Students are divided into courses based on their practical time slot
- Allows for different visible and due dates for each time slot
- Students in different sections occuring at the same time are in the same Grader course
