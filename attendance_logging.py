import streamlit as st
import csv
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Replace with your service account key file
SPREADSHEET_ID = '1SzhjrM9pixwbfuW7PHB0q6vWIdI-6UH6zNmGB07XxbA'  # Replace with your Google Sheet ID

# Authenticate Google Sheets API
def get_google_sheets_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def append_to_google_sheet(student_name, check_in=None, check_out=None, time_difference=None):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    data = [[
        datetime.now().strftime('%Y-%m-%d'),
        student_name,
        check_in,
        check_out,
        time_difference
    ]]
    try:
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": data}
        ).execute()
    except Exception as e:
        st.error(f"Error writing to Google Sheet: {e}")

def update_google_sheet_checkout(student_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        # Read all data from the sheet
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:E").execute()
        values = result.get('values', [])

        if not values:
            return False

        updated = False
        for i, row in enumerate(values):
            if len(row) >= 5 and row[1] == student_name and row[3] == '':
                check_in_time = datetime.strptime(row[2], '%H:%M:%S')
                check_out_time = datetime.now()
                row[3] = check_out_time.strftime('%H:%M:%S')
                duration = check_out_time - check_in_time
                row[4] = f"{duration.seconds // 3600}h {duration.seconds % 3600 // 60}m"

                # Update the row in Google Sheets
                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"Sheet1!A{i+1}:E{i+1}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [row]}
                ).execute()
                updated = True
                break

        return updated

    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")
        return False

def is_already_checked_in_google(student_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:E").execute()
        values = result.get('values', [])
        
        for row in values:
            if len(row) >= 4 and row[1] == student_name and row[3] == '':
                return True
        return False

    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
        return False

# Streamlit UI
st.title("Attendance Tracker")
students = ["Student 1", "Student 2", "Student 3"]  # Replace with dynamic loading if needed

if students:
    student_name = st.selectbox("Select a Student", students)
    action = st.radio("Action", ["Check In", "Check Out"])

    if st.button("Submit"):
        if action == "Check In":
            if is_already_checked_in_google(student_name):
                st.error(f"{student_name} is already checked in. Please check out first.")
            else:
                check_in_time = datetime.now().strftime('%H:%M:%S')
                append_to_google_sheet(student_name, check_in=check_in_time)
                st.success(f"{student_name} checked in at {check_in_time}.")
        elif action == "Check Out":
            if update_google_sheet_checkout(student_name):
                st.success(f"{student_name} checked out.")
            else:
                st.error(f"No check-in record found for {student_name}.")
else:
    st.error("No students found.")