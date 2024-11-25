# -*- coding: utf-8 -*-
"""Another copy of Biods exploration - Cleaned

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1CjbV5jp4cuR_CoezGm7sgeUbNGImBdAk
"""

#Code to read csv file into Colaboratory:
!pip install -U -q PyDrive
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials
from google.colab import drive
drive.mount('/content/drive')

#Authenticate and create the PyDrive client.
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

import io
import os
import numpy as np
import pandas as pd
import re
import spacy
import matplotlib.pyplot as plt
import nltk
from ast import literal_eval

"""# Developing Patient Cohorts + Diagnoses"""

SI = 12113

# Define the path to the folder containing labevents.csv
folder_path = '/content/drive/My Drive/BIODS_295_Coding_Folder/mimic-iv-2.2/mimic3'
# List contents of the folder to ensure correct path
os.listdir(folder_path)

dicd_path = os.path.join(folder_path, 'D_ICD_DIAGNOSES.csv')
icd_dict = pd.read_csv(dicd_path)
diagnoses_path = os.path.join(folder_path, 'DIAGNOSES_ICD.csv')
diagnosis = pd.read_csv(diagnoses_path)
#print(diagnosis.head(5))
#print(icd_dict.head(5))

merged_df = pd.merge(diagnosis, icd_dict[['ICD9_CODE', 'LONG_TITLE']], on='ICD9_CODE', how='left')

# Drop rows with missing values in the 'LONG_TITLE' column
merged_df.dropna(subset=['LONG_TITLE'], inplace=True)

# Define the list of terms to search for
search_terms = ["sarcoma", "cancer", "lymphoma", "leukemia", "carcinoma", "malignant neoplasm"]

# Create a regex pattern to match any of the terms, ignoring case
pattern = '|'.join(search_terms)

# Filter the DataFrame for rows where the "long_title" column contains any of the terms
filtered_df = merged_df[merged_df['LONG_TITLE'].str.contains(pattern, case=False)].copy()  # Make a copy to avoid modifying the original DataFrame

# Add a new column indicating the terms found in each row
filtered_df.loc[:, 'found_terms'] = filtered_df['LONG_TITLE'].str.findall(pattern, flags=re.IGNORECASE)

# Convert all found terms to lowercase
filtered_df.loc[:, 'found_terms'] = filtered_df['found_terms'].apply(lambda x: [term.lower() for term in x])

# Display the filtered DataFrame
print(filtered_df)

# Save the filtered DataFrame to a CSV file
filtered_df.to_csv('filtered_notes.csv', index=False)

# Check the structure of the DataFrame
#print(filtered_df.head())

# Group by 'subject_id' and aggregate 'hadm_id' and 'found_terms'
new_df = filtered_df.groupby('SUBJECT_ID').agg({
    'HADM_ID': list,
    'found_terms': lambda x: list(set(term for sublist in x for term in sublist))
}).reset_index()

# Rename the aggregated columns
new_df.columns = ['SUBJECT_ID', 'HADM_IDS', 'found_terms']

#print(new_df)

subject_ids = new_df['SUBJECT_ID'].tolist() # This is the cohort
print(subject_ids)

patient_to_diagnoses = filtered_df.groupby('SUBJECT_ID')['LONG_TITLE'].apply(list).to_dict()

# Meaningful things from this section are:
# patient_to_diagnoses - subject_id: [list of diagnoses]
# subject_ids - [list of our patient cohort]

"""# Clinical Note Loading"""

folder_path = '/content/drive/My Drive/BIODS_295_Coding_Folder/mimic-iv-2.2/mimic3/'

# Define the path to labevents.csv
labevents_path = os.path.join(folder_path, 'NOTEEVENTS.csv')
def filter_chunks(chunk):
    return chunk[chunk['SUBJECT_ID'].isin(subject_ids)]

# Create an empty list to store filtered rows
filtered_rows = []

# Define dtype dictionary for columns with mixed types
dtype_dict = {'subject_id': int}  # Assuming subject_id is integer, adjust as needed

# Read the file in chunks and filter based on subject_ids
chunk_size = 100000  # Experiment with different chunk sizes depending on your memory constraints
rows_loaded = 0
for chunk in pd.read_csv(labevents_path, chunksize=chunk_size, dtype=dtype_dict):
    filtered_chunk = filter_chunks(chunk)
    filtered_rows.append(filtered_chunk)
    rows_loaded += len(filtered_chunk)
    if rows_loaded >= 100000:
        break

# Concatenate filtered rows into a single DataFrame
filtered_labevents = pd.concat(filtered_rows)

# Print the first few rows of the filtered DataFrame
print(filtered_labevents.head())

newnew_df = filtered_labevents[['SUBJECT_ID', 'HADM_ID', 'CHARTDATE', 'CATEGORY', 'TEXT']].copy()
# Display the new DataFrame
print(newnew_df.head())

nmerged_df = pd.merge(new_df, newnew_df, on='SUBJECT_ID', how='inner')

# Display the merged DataFrame
#display(nmerged_df)

nmerged_df['CATEGORY'] = nmerged_df['CATEGORY'].str.lower()
# Filter the DataFrame for rows where the 'CATEGORY' column is 'discharge summary'
nnnmerged_df = nmerged_df[nmerged_df['CATEGORY'] == 'discharge summary']

# Make an explicit copy of the DataFrame to avoid SettingWithCopyWarning
nnnmerged_df_copy = nnnmerged_df.copy()

# Convert the CHARTDATE column to datetime if it's not already
nnnmerged_df_copy['CHARTDATE'] = pd.to_datetime(nnnmerged_df_copy['CHARTDATE'])

# Group by SUBJECT_ID and get the index of the row with the largest CHARTDATE
idx = nnnmerged_df_copy.groupby('SUBJECT_ID')['CHARTDATE'].idxmax()

# Use the index to filter the DataFrame
nnnmerged_df_max_date = nnnmerged_df_copy.loc[idx]

# Display the filtered DataFrame
#print(nnnmerged_df_max_date)

onmerged_df = nnnmerged_df_max_date[nnnmerged_df_max_date['SUBJECT_ID'] ==  SI]
clinical_notes_dict = onmerged_df.groupby('SUBJECT_ID').apply(lambda x: x[['CHARTDATE', 'CATEGORY', 'TEXT']].values.tolist()).to_dict()

# Meaningful Information from this Section
# clinical_notes_dict: dictionary of {subject_id: list_of_events in the form of ['CHARTDATE', 'CATEGORY', 'TEXT']}
# print(len(clinical_notes_dict[11][0]))

"""# Lab Event Loading"""

# Define the path to the folder containing labevents.csv
folder_path = '/content/drive/My Drive/BIODS_295_Coding_Folder/mimic-iv-2.2/mimic3'
# List contents of the folder to ensure correct path
os.listdir(folder_path)

labe_path = os.path.join(folder_path, 'LABEVENTS.csv')
labe = pd.read_csv(labe_path)
dicte_path = os.path.join(folder_path, 'D_LABITEMS.csv')
dicte = pd.read_csv(dicte_path)
print(labe.head(5))
print(dicte.head(5))


nnmerged_df = pd.merge(labe, dicte, on='ITEMID', how='inner')

nfiltered_df = nnmerged_df[nnmerged_df['SUBJECT_ID'].isin(subject_ids)]

# Display the merged DataFrame
# print(nfiltered_df.head())

#display(nfiltered_df)

target_labels = ['Alpha-Fetoprotein', 'CA-125', 'Cancer Antigen 27.29', 'Carcinoembryonic Antigen (CEA)', 'Prostate Specific Antigen']
lab_filtered_df = nfiltered_df[nfiltered_df['LABEL'].isin(target_labels)]
ggrouped = lab_filtered_df[lab_filtered_df['SUBJECT_ID'] == SI]
grouped = ggrouped.groupby(['SUBJECT_ID', 'LABEL']).apply(lambda x: list(zip(x['VALUENUM'], x['CHARTTIME'], x['VALUEUOM']))).unstack()

subject_lab_dict = grouped.applymap(lambda x: x if isinstance(x, list) else []).to_dict(orient='index')

print(len(subject_lab_dict))

# Meaningful Information from this Section:
# subject_lab_dict - subject: {relevant lab: [value, chart, units]}

"""# Prescriptions

"""

#Path to prescriptions file
folder_path = '/content/drive/My Drive/BIODS_295_Coding_Folder/mimic-iv-2.2/mimic3'
os.listdir(folder_path)

#Load in prescription data
pres_path = os.path.join(folder_path, 'PRESCRIPTIONS.csv')
prescription = pd.read_csv(pres_path)

#Filter down to cancer patients
filtered_prescription = prescription[prescription['SUBJECT_ID'].isin(subject_ids)]
print(filtered_prescription.head(5))

#prescription info for specific subject
#prescriptionsubject = filtered_prescription[filtered_prescription['SUBJECT_ID'] == 31608]

prescriptionsubject = filtered_prescription[filtered_prescription['SUBJECT_ID'] == SI]

prescription_dict = {}

for _, row in prescriptionsubject.iterrows():
    subject_id = row['SUBJECT_ID']
    drug_name = row['DRUG_NAME_GENERIC']
    dose = f"{row['DOSE_VAL_RX']}{row['DOSE_UNIT_RX']}"
    start_date = row['STARTDATE']
    end_date = row['ENDDATE']

    if subject_id not in prescription_dict:
        prescription_dict[subject_id] = {}

    prescription_dict[subject_id][drug_name] = [dose, start_date, end_date]

#print(prescription_dict)

# {SUBJECT_ID: {DRUG_NAME_GENERIC:['DOSE_VAL_RX'+'DOSE_UNIT_RX', 'STARTDATE', 'ENDDATE']}}

display(filtered_prescription)

"""# Procedures"""

#Path to prescriptions file
folder_path = '/content/drive/My Drive/BIODS_295_Coding_Folder/mimic-iv-2.2/mimic3'
os.listdir(folder_path)

#Load in prescription data
proc_path = os.path.join(folder_path, 'PROCEDUREEVENTS_MV.csv')
procedures = pd.read_csv(proc_path)
procitems_path = os.path.join(folder_path, 'D_ITEMS.csv')
d_items = pd.read_csv(procitems_path)

#merge based on ITEMID
merged_procedure = procedures.merge(d_items[['ITEMID', 'LABEL']], on='ITEMID', how='left')

#Filter down to cancer patients
filtered_procedures = merged_procedure[merged_procedure['SUBJECT_ID'].isin(subject_ids)]
#print(filtered_procedures.head(500))

unique_subject_ids = filtered_procedures['SUBJECT_ID'].unique()

# Convert the numpy array to a list (optional)
unique_subject_ids_list = unique_subject_ids.tolist()

# Display the list of unique SUBJECT_IDs
unique_subject_ids_list

proceduressubject = filtered_procedures[filtered_procedures['SUBJECT_ID'] == SI]
#display(proceduressubject)

procedures_dict = {}

for _, row in proceduressubject.iterrows():
    subject_id = row['SUBJECT_ID']
    label = row['LABEL']
    start_time = row['STARTTIME']

    if subject_id not in procedures_dict:
        procedures_dict[subject_id] = {}

    procedures_dict[subject_id][label] = [start_time]

print(procedures_dict)

"""#Print data"""

# Print diagnosis
print(patient_to_diagnoses[SI])

# Print first discharge summary
print(clinical_notes_dict)

#Print labs
print(subject_lab_dict)

#Print prescriptions
print(prescription_dict)

#Print procedures
print(procedures_dict)

"""# Generative AI Pipeline"""

import pandas as pd
import os
import openai

# key saved as text file
with open("openai_api_key.txt") as f:
    key = f.readline()

from openai import OpenAI

client = OpenAI(
  api_key=key
    )

def summarize_text(text, model="gpt-3.5-turbo-instruct", max_tokens=150):
    response = client.completions.create(
        #model = "gpt-3.5",
        model = model,
        #engine=model,
        prompt=f"Summarize the following medical note:\n\n{text}\n\nSummary:",
        #max_tokens=max_tokens,
        #temperature=0.7,
        #top_p=1.0,
        #frequency_penalty=0.0,
        #presence_penalty=0.0,
        #stop=["\n"]
    )
    summary = response.choices[0].text.strip()
    return summary

df = pd.read_csv('Patient 11 EHR notes.csv')

if 'TEXT' not in df.columns:
    raise ValueError("The CSV file must contain a 'TEXT' column.")

df['cleaned_text'] = df['TEXT'].apply(lambda x: x.strip() if isinstance(x, str) else "")

df['summary'] = df['cleaned_text'].apply(lambda x: summarize_text(x) if x else "")

with open("summarized_texts.txt", "w") as file:
    file.write("\n".join(df['summary']))

"""# End of Current Code"""