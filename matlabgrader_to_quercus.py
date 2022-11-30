'''
Easily upload MATLAB Grader scores to Quercus
Simeon Wong
'''

import pandas as pd
import os
import argparse
import datetime
import sys
import pick
import glob
import re

parser = argparse.ArgumentParser(description='Merge Quercus Gradebook Templates, UTAGT Groups Roster, and Matlab Grader Reports to generate CSV files understood by Quercus')
parser.add_argument('--grader_report', help='Matlab Grader Report Excel File', default=None)
parser.add_argument('--assignmentID', help='Quercus Assignment ID', default=None)
parser.add_argument('--quercus_gradebook',
                    default='QuercusGradebook.csv',
                    help='Quercus Gradebook Excel File')
parser.add_argument('--utagt_roster', default='Roster.csv', help='UTAGT Groups Roster CSV')

if 'ipykernel' in sys.argv[0]:  # running in ipython terminal. use test parameters.
    args = parser.parse_args(
    ['--grader_report', r'.\score_exports\Project 2 - Lab Exercise 1.xlsx', '--assignmentID', '945984'])
else:                           # otherwise, use command line arguments
    args = parser.parse_args()

gradebook = pd.read_csv(args.quercus_gradebook)

# show list of reports and assignment IDs if not already provided
if args.grader_report is None:
    files = glob.glob('score_exports/*.xlsx')
    grader_report, _ = pick.pick(files, 'Select source MATLAB grader file:')
    
else:
    grader_report = args.grader_report

if args.assignmentID is None:
    assignments = list(filter(lambda x: re.match('.*\([0-9]{6}\)', x), gradebook.columns))
    assignmentID, _ = pick.pick(assignments, 'Select destination Gradebook entry:')

    assignmentID = re.search('\(([0-9]{6})\)', assignmentID)
    assignmentID = assignmentID.group(0)

else:
    assignmentID = args.assignmentID

print('Source file: {}'.format(grader_report))
print('Assignment ID: {}'.format(assignmentID))

# Import all input files
roster = pd.read_csv(args.utagt_roster)
matlab = pd.read_excel(grader_report)

# Merge Quercus Gradebook and UTAGT Groups Roster
gradebook = gradebook.merge(roster[['UTORid', 'Email']], left_on='SIS User ID', right_on='UTORid', how='left')

# Compute MATLAB Grader grades
matlab = matlab[['Student Email', '% Score', 'Problem ID']]
matlab['Score'] = matlab['% Score'].str.replace('[^0-9]', '', regex=True).apply(lambda x: int(x) / 100) # parse score

# sum score over individual problems
matlab.index = pd.MultiIndex.from_frame(matlab[['Student Email', 'Problem ID']])
matlab_score = matlab[['Score']].unstack().fillna(0)
matlab_score['Total'] = matlab_score.sum(axis=1) / matlab_score.shape[1]

# which assignment to write scores to
aid = gradebook.columns[gradebook.columns.str.find(assignmentID) > 0][0]

# Merge MATLAB Grader grades with Quercus Gradebook
gradebook.loc[2:,aid] = gradebook['Email'].iloc[2:].map(matlab_score['Total'])

# Convert from fraction to number of points
gradebook.loc[2:, aid] = gradebook.loc[2:, aid] * float(gradebook.loc[1, aid])

# Excerpt columns we need, then write to CSV
gradebook = gradebook[['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', aid]]
gradebook.to_csv(os.path.join('outputs', datetime.datetime.now().strftime('%Y%m%dT%H%M%S_') + aid + '.csv'), index=False)
