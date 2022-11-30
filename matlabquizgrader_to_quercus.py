'''
Easily upload MATLAB Grader scores to Quercus
Simeon Wong
'''

import pandas as pd
import os
import os.path
import argparse
import datetime
import sys
import glob
import seaborn as sns
import traceback
import json

#######################################################################################
# Valid last digit of student number for each Grader Export
ver_lookup = {
    '1': (0, 1, 2, 3),
    '2': (4, 5, 6),
    '3': (7, 8, 9),
}

# question names
common_q_names = pd.Series(['Functions', 'Conditional', 'Debugging', 'Loops', 'Indexing', 'Plotting'])

# get current runtime
datestr = datetime.datetime.now().strftime('%Y%m%dT%H%M%S_')

#######################################################################################
parser = argparse.ArgumentParser(description='Compile MATLAB Grader reports from the quiz and format for import to Quercus')
parser.add_argument('assignmentID', help='Quercus Assignment ID')
parser.add_argument('--quercus_gradebook', default='QuercusGradebook.csv', help='Quercus Gradebook Excel File')
parser.add_argument('--utagt_roster', default='Roster.csv', help='UTAGT Groups Roster CSV')
parser.add_argument('--nodrop_attendance', dest='mark_attendance', action='store_false', help='Do not drop students who are not in attendance')
parser.add_argument('--nodrop_quizver', dest='mark_quizver', action='store_false', help='Do not drop students who did the wrong quiz version')
parser.add_argument('--deadline_grace', type=float, default=0, help='Number of seconds to add to the deadline as a grace period')

if 'ipykernel' in sys.argv[0]:  # running in ipython terminal. use test parameters.
    args = parser.parse_args(
    ['--nodrop_quizver', '945979', '--deadline_grace', '300'])
else:                           # otherwise, use command line arguments
    args = parser.parse_args()

print('===== PARAMETERS =====')
jsparams = json.dumps(vars(args), indent=4) # pretty print parameters
print(jsparams)
print('======================')

# Import all input files
gradebook = pd.read_csv(args.quercus_gradebook)
roster = pd.read_csv(args.utagt_roster)
attendance = pd.read_excel(os.path.expanduser(r'~\University of Toronto\Camelia Karimian Pour - Practicals\Fall 2022\General\QuizAttendanceList.xlsx'), sheet_name=None)

# concatenate all attendance sheets into one dataframe
attendance = pd.concat(attendance.values(), ignore_index=True)
attendance['Present?'] = attendance['Present?'].apply(lambda x: x == 1 or x == True or (isinstance(x, str) and x.lower()[0] == 'y'))
attendance.set_index('Email', drop=True, inplace=True)

# Merge Quercus Gradebook and UTAGT Groups Roster
gradebook = gradebook.merge(roster[['UTORid', 'Email']], left_on='SIS User ID', right_on='UTORid', how='left')

allsubs = None
totals = None
allscores = None
dropped = None

# loop through list of quiz exports and compile into one dataframe
for grader_report_path in glob.glob('quiz_exports/*.xlsx'):
    print('Processing {}'.format(grader_report_path))

    try:
        matlab = pd.read_excel(grader_report_path)

        csubs = matlab['Student Email'].to_frame()
        csubs['Path'] = grader_report_path
        allsubs = pd.concat((allsubs, csubs), ignore_index=False)

        # parse score
        matlab['Score'] = matlab['% Score'].str.replace('[^0-9]', '', regex=True).apply(lambda x: int(x) / 100)

        # parse naming convention
        #  2.10.1.xlsx -> tuesday @ 10am for student numbers ending in 0-3
        dow, hour, ver, *_ = os.path.split(grader_report_path)[1].split('.')

        dow = int(dow)
        if dow == 1:
            dow = 8  # week shift due to Thanksgiving
        hour = int(hour)

        start_time = datetime.datetime(2022, 10, 9, 0, 0, 0) + datetime.timedelta(days=dow, hours=hour)
        deadline_time = start_time + datetime.timedelta(hours=1)

        # Join with attendance sheet
        matlab = matlab.merge(attendance[['Present?', 'Time out', 'StudentNum']], how='left', left_on='Student Email', right_index=True)
        matlab['Time out'] = matlab['Time out'].apply(lambda x: datetime.datetime.combine(start_time.date(), x) if not pd.isna(x) else deadline_time)
        matlab['Time out'] = matlab['Time out'] + datetime.timedelta(seconds=args.deadline_grace) # add grace period

        matlab['Submitted Time'] = matlab['Submitted Time'].apply(lambda x: datetime.datetime.strptime(x[:-4], '%Y-%m-%d %H:%M:%S'))

        # Drop submissions after last acceptable time (either Time Out or end of practical)
        to_keep = matlab['Submitted Time'] <= matlab['Time out']
        rows_dropped = matlab[~to_keep]
        matlab = matlab[to_keep]
        rows_dropped['Reason'] = 'Submit after deadline'
        dropped = pd.concat((dropped, rows_dropped), ignore_index=True)

        # Drop submissions that are not present
        rows_dropped = matlab[matlab['Present?'] != True]
        if args.mark_attendance:
            matlab = matlab[matlab['Present?'] == True]
        rows_dropped['Reason'] = 'Attendance' + (' (ignored)' if not args.mark_attendance else '') # mark attendance as ignored if not dropping
        dropped = pd.concat((dropped, rows_dropped), ignore_index=True)

        # Drop submissions that don't correspond to the correct student number
        to_keep = matlab['StudentNum'].apply(lambda x: x % 10 in ver_lookup[ver])
        rows_dropped = matlab[~to_keep]
        if args.mark_quizver:
            matlab = matlab[to_keep]
        rows_dropped['Reason'] = 'Quiz version mismatch' + (' (ignored)' if not args.mark_quizver else '') # mark quiz version as ignored if not dropping
        dropped = pd.concat((dropped, rows_dropped), ignore_index=True)

        # Compute overall grade
        title_lookup = matlab[['Problem ID', 'Problem Title']].drop_duplicates('Problem ID').set_index('Problem ID', drop=True)['Problem Title'].apply(lambda x: common_q_names.iloc[[y.lower() in x.lower() for y in common_q_names]].values[0])  # find common question name
        matlab = matlab[['Student Email', 'Score', 'Problem ID']]

        # Drop all except for the best valid submission for all students, within each problem
        matlab = matlab.sort_values('Score', ascending=False).drop_duplicates(['Student Email', 'Problem ID'])

        # Sum grades for each problem to get assignment total
        matlab.index = pd.MultiIndex.from_frame(matlab[['Student Email', 'Problem ID']])
        matlab_score = matlab[['Score']].unstack().fillna(0)
        matlab_score['Total'] = matlab_score.sum(axis=1) / matlab_score.shape[1]

        # Grades for the merging
        totals = pd.concat((totals, matlab_score['Total']))

        # Normalize question names and concat together (for analytics)
        matlab_score.columns = pd.Index([title_lookup[x[1]] for x in matlab_score.columns[:-1]] + ['Total'])
        matlab_score['File'] = grader_report_path
        matlab_score['Student Number'] = matlab_score.index.map(lambda x: roster[roster['Email'] == x]['Student Number'].values[0])
        allscores = pd.concat((allscores, matlab_score))

    except Exception as ex:
        print('Error processing {}: {}'.format(grader_report_path, ex))
        traceback.print_exc()

# Get a list of students who didn't submit anything at all
nosub = gradebook[~gradebook['Email'].isin(allsubs['Student Email'])]['Email'].drop_duplicates(
).reset_index(drop=True).dropna().to_frame()
nosub.rename({'Email': 'Student Email'}, axis=1, inplace=True)

# which assignment to write scores to
aid = gradebook.columns[gradebook.columns.str.find(args.assignmentID) > 0][0]

with open(os.path.join('outputs', 'params_' + datestr + aid + '.json'), 'w') as f:
    f.write(jsparams)

# remove duplicates in total score, keep highest score
totals = totals.groupby(level=0).max()

# Merge MATLAB Grader grades with Quercus Gradebook
gradebook.loc[2:,aid] = gradebook['Email'].iloc[2:].map(totals)

# Convert from fraction to number of points
gradebook.loc[2:,aid] = gradebook.loc[2:,aid] * float(gradebook.loc[1,aid])

# Excerpt columns we need, then write to CSV
gradebook[['Student', 'ID', 'SIS User ID', 'SIS Login ID', 'Section', aid]].to_csv(os.path.join('outputs', datestr + aid + '.csv'), index=False)

# Get a list of students who submitted something, but did not get scored
# and lookup some information to make things easier
graded_emails = gradebook.dropna(subset=[aid], inplace=False)['Email']
ungraded = allsubs[~allsubs['Student Email'].isin(graded_emails)].drop_duplicates().reset_index(drop=True)
ungraded['Reasons'] = ''
for ri, rr in ungraded.iterrows():
    rr['Reasons'] = dropped[dropped['Student Email'] == rr['Student Email']]['Reason'].drop_duplicates().str.cat(sep=', ')

    if rr['Reasons'] == '':
        rr['Reasons'] = 'Not in gradebook'

nosub['Reasons'] = 'No submission'
ungraded = pd.concat((ungraded, nosub), ignore_index=True)

# Get a list of questions that were not graded
dropped = dropped[['Student Name', 'Student Email', 'StudentNum', 'Reason', 'Submitted Time', '% Score', 'Problem Title', 'Assignment Title', 'Present?', 'Time out']]
dropped['StudentNum'] = dropped['StudentNum'].apply(lambda x: '{:.0f}'.format(x))
dropped.loc[:, 'Seconds past due'] = (
    dropped['Submitted Time'] - dropped['Time out']
).dt.total_seconds()  # add column for how many seconds past due
dropped.loc[dropped['Seconds past due'] <= 0, 'Seconds past due'] = pd.NA  # set negative values to NA

# Filter the list of questions for students who weren't graded
students_all_dropped = dropped[dropped['Student Email'].isin(ungraded['Student Email'])]

with pd.ExcelWriter(os.path.join('outputs', 'dropped_' + datestr + aid + '.xlsx')) as xlsw:
    ungraded.to_excel(xlsw, sheet_name='Ungraded', index=False)
    dropped.to_excel(xlsw, sheet_name='Dropped', index=False)
    students_all_dropped.to_excel(xlsw, sheet_name='Dropped - student not graded', index=False)

# Generate reports
allscores.to_excel(os.path.join('outputs', 'scores_' + datestr + aid + '.xlsx'), index=True)

hax = sns.histplot(allscores['Total'], bins=15)
hax.figure.savefig(os.path.join('outputs', 'hist_' + datestr + aid + '.png'), dpi=500)
