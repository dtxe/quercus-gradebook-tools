'''
Easily upload MATLAB Grader scores to Quercus
Simeon Wong
'''

import pandas as pd
import os
import argparse
import datetime
import sys

parser = argparse.ArgumentParser(
    description=
    'Merge Quercus Gradebook, UTAGT Groups Roster, and Gradescope CSV to write Gradescope grades to Quercus Gradebook'
)
parser.add_argument('gradescope', help='Gradescope Assignment CSV')
parser.add_argument('assignmentID', help='Quercus Assignment ID')
parser.add_argument('--quercus_gradebook',
                    default='QuercusGradebook.csv',
                    help='Quercus Gradebook Export')

if 'ipykernel' in sys.argv[0]:  # running in ipython terminal. use test parameters.
    args = parser.parse_args(
    ['Grades.csv', 'Roster.csv', 'Project 1 - Lab Exercise 1.xlsx', '945966'])
else:                           # otherwise, use command line arguments
    args = parser.parse_args()


# Import all input files
gradebook = pd.read_csv(args.quercus_gradebook)
gradescope = pd.read_csv(args.gradescope)

# which assignment to write scores to
aid = gradebook.columns[gradebook.columns.str.find(args.assignmentID) > 0][0]

# Merge Quercus and Gradescope using utorid
gradescope = gradescope.loc[gradescope['UTORid'].notna(), :]
gradescope['Score'] = gradescope['Total Score'] / gradescope['Max Points']
gradescope = gradescope.set_index('UTORid')['Score']
gradescope.clip(0, 1, inplace=True)  # keep score within 0% to 100%

gradebook.loc[2:, aid] = gradebook['SIS User ID'].iloc[2:].map(gradescope)

# Convert from fraction to number of points
gradebook.loc[2:, aid] = gradebook.loc[2:, aid] * float(gradebook.loc[1, aid])

# Excerpt columns we need, then write to CSV
gradebook = gradebook[[
    'Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', aid
]]
gradebook.to_csv(os.path.join(
    'outputs',
    datetime.datetime.now().strftime('%Y%m%dT%H%M%S_') + aid + '.csv'),
                 index=False)
