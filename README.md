# Scripts to help with uploading grades to Quercus (Canvas at the University of Toronto)

## matlabgrader_to_quercus.py
From MATLAB Grader Assignment reports, compute the sum of each student's grade across all problems. Or get total grade from Gradescope export.  
Then join the total grade with the UT Advanced Groups Tool student list on email, then join grades with the 
required information from the Quercus Gradebook import template.


## build_matlab_quiz_rosters.ipynb
Join Quercus Gradebook export (containing section info) with UTAGT exports (containing emails) and with a CSV of
practical time slots to generate a list of Grader courses and student emails that should be invited.
- Students are divided into courses based on their practical time slot
- Allows for different visible and due dates for each time slot
- Students in different sections occuring at the same time are in the same Grader course
