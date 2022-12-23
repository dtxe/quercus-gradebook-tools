'''
Easily upload MATLAB Grader and Gradescope scores to Quercus
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

parser = argparse.ArgumentParser(
    description=
    'Merge Quercus Gradebook Templates, UTAGT Groups Roster, and Matlab Grader or Gradescope Reports to generate CSV files understood by Quercus'
)
parser.add_argument('--grader_report',
                    help='Matlab Grader Report Excel File',
                    default=None)
parser.add_argument('--assignmentID',
                    help='Quercus Assignment ID',
                    default=None)
parser.add_argument('--quercus_gradebook',
                    default='QuercusGradebook.csv',
                    help='Quercus Gradebook Excel File')
parser.add_argument('--utagt_roster',
                    default='Roster.csv',
                    help='UTAGT Groups Roster CSV')

if 'ipykernel' in sys.argv[
        0]:  # running in ipython terminal. use test parameters.
    args = parser.parse_args([
        '--grader_report', r'.\score_exports\Project 2 - Lab Exercise 1.xlsx',
        '--assignmentID', '945984'
    ])
else:  # otherwise, use command line arguments
    args = parser.parse_args()

# Load Quercus gradebook to get list of assignment IDs
gradebook = pd.read_csv(args.quercus_gradebook)

# show list of reports and assignment IDs if not already provided
if args.grader_report is None:
    files = glob.glob('score_exports/*.xlsx') + glob.glob('score_exports/*.csv')
    files.sort()
    grader_report, _ = pick.pick(files, 'Select source MATLAB Grader or Gradescope file:')

else:
    grader_report = args.grader_report

if args.assignmentID is None:
    assignments = list(
        filter(lambda x: re.match('.*\([0-9]{6}\)', x), gradebook.columns))
    assignments.sort()
    assignmentID, _ = pick.pick(assignments,
                                'Select destination Gradebook entry:')

    assignmentID = re.search('\(([0-9]{6})\)', assignmentID)
    assignmentID = assignmentID.group(0)

else:
    assignmentID = args.assignmentID

# which assignment to write scores to
aid = gradebook.columns[gradebook.columns.str.find(assignmentID) > 0][0]

# Load scores and determine type
if os.path.splitext(grader_report)[1] == '.xlsx':
    scores = pd.read_excel(grader_report)
else:
    scores = pd.read_csv(grader_report)


if 'Problem ID' in scores.columns:
    # MATLAB grader export
    matlab = scores
    
    # Import UTAGT roster
    roster = pd.read_csv(args.utagt_roster)

    # Merge Quercus Gradebook and UTAGT Groups Roster
    gradebook = gradebook.merge(roster[['UTORid', 'Email']],
                            left_on='SIS User ID',
                            right_on='UTORid',
                            how='left')
    
    matlab = matlab[['Student Email', '% Score', 'Problem ID']]
    matlab['Score'] = matlab['% Score'].str.replace(
        '[^0-9]', '', regex=True).apply(lambda x: int(x) / 100)  # parse score

    # sum score over individual problems
    matlab.index = pd.MultiIndex.from_frame(matlab[['Student Email',
                                                    'Problem ID']])
    matlab_score = matlab[['Score']].unstack().fillna(0)
    matlab_score['Total'] = matlab_score.sum(axis=1) / matlab_score.shape[1]

    # Merge MATLAB Grader grades with Quercus Gradebook
    gradebook.loc[2:, aid] = gradebook['Email'].iloc[2:].map(matlab_score['Total'])

elif 'SID' in scores.columns:
    # Gradescope export
    gradescope = scores
    
    gradescope = gradescope.loc[gradescope['UTORid'].notna(), :]
    gradescope['Score'] = gradescope['Total Score'] / gradescope['Max Points']
    gradescope = gradescope.set_index('UTORid')['Score']
    gradescope.clip(0, 1, inplace=True)  # keep score within 0% to 100%

    gradebook.loc[2:, aid] = gradebook['SIS User ID'].iloc[2:].map(gradescope)  # Merge using utorid

else:
    raise('Unknown file type')


# Convert from fraction to number of points
gradebook.loc[2:, aid] = gradebook.loc[2:, aid] * float(gradebook.loc[1, aid])

# Excerpt columns we need, then write to CSV
gradebook = gradebook[[
    'Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', aid
]]
savepath = os.path.join(
    'outputs',
    datetime.datetime.now().strftime('%Y%m%dT%H%M%S_') + aid + '.csv')
gradebook.to_csv(savepath, index=False)

print('=' * 25)
print('Source file: {}'.format(grader_report))
print('Assignment ID: {}'.format(assignmentID))
print('Output file: {}'.format(savepath))
print('=' * 25)
