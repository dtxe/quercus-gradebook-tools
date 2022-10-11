'''
Easily upload MATLAB Grader scores to Quercus
Simeon Wong
'''

import pandas as pd
import os
import argparse
import datetime

parser = argparse.ArgumentParser(description='Merge Quercus Gradebook Templates, UTAGT Groups Roster, and Matlab Grader Reports to generate CSV files understood by Quercus')
parser.add_argument('grader_report', help='Matlab Grader Report Excel File')
parser.add_argument('assignmentID', help='Quercus Assignment ID')
parser.add_argument('--quercus_gradebook', default='GradebookTemplate.csv', help='Quercus Gradebook Excel File')
parser.add_argument('--utagt_roster', default='Roster.csv', help='UTAGT Groups Roster CSV')

if 'ipykernel' in sys.argv[0]:  # running in ipython terminal. use test parameters.
    args = parser.parse_args(
    ['Grades.csv', 'Roster.csv', 'Project 1 - Lab Exercise 1.xlsx', '945966'])
else:                           # otherwise, use command line arguments
    args = parser.parse_args()

# Import all input files
gradebook = pd.read_csv(args.quercus_gradebook)
roster = pd.read_csv(args.utagt_roster)
matlab = pd.read_excel(args.grader_report)

# Merge Quercus Gradebook and UTAGT Groups Roster
gradebook = gradebook.merge(roster[['UTORid', 'Email']], left_on='SIS User ID', right_on='UTORid', how='left')

# Compute MATLAB Grader grades
matlab = matlab[['Student Email', 'Correct', 'Problem ID']]
matlab.index = pd.MultiIndex.from_frame(matlab[['Student Email', 'Problem ID']])
matlab_score = matlab[['Correct']].unstack().fillna(0)
matlab_score['Total'] = matlab_score.sum(axis=1) / matlab_score.shape[1]

# which assignment to write scores to
aid = gradebook.columns[gradebook.columns.str.find(args.assignmentID) > 0][0]

# Merge MATLAB Grader grades with Quercus Gradebook
gradebook.loc[2:,aid] = gradebook['Email'].iloc[2:].map(matlab_score['Total'])

# Excerpt columns we need, then write to CSV
gradebook = gradebook[['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', aid]]
gradebook.to_csv(os.path.join('outputs', datetime.datetime.now().strftime('%Y%m%dT%H%M%S_') + aid + '.csv'), index=False)
