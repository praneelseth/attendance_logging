import streamlit as st
import csv
import tomllib
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# SERVICE_ACCOUNT_FILE = 'secrets.toml'  # Replace with your service account key file
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Replace with your service account key file
SPREADSHEET_ID = '1SzhjrM9pixwbfuW7PHB0q6vWIdI-6UH6zNmGB07XxbA'  # Replace with your Google Sheet ID

# Authenticate Google Sheets API
def get_google_sheets_service():
    creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
    # creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def get_active_sheet_name(frequency="daily"):
    if frequency == "daily":
        return datetime.now().strftime('%Y-%m-%d')
    elif frequency == "weekly":
        return f"Week-{datetime.now().strftime('%U')}-{datetime.now().year}"
    elif frequency == "monthly":
        return datetime.now().strftime('%Y-%m')
    else:
        raise ValueError("Invalid frequency. Choose 'daily', 'weekly', or 'monthly'.")

def ensure_active_sheet_exists(sheet_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        # Fetch all sheet names
        spreadsheet = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

        if sheet_name not in existing_sheets:
            request_body = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name
                            }
                        }
                    }
                ]
            }
            sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=request_body).execute()
            # Add headers to the new sheet
            headers = [["Date", "Name", "Check In Time", "Check Out Time", "Time Spent"]]
            sheet.values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A1:E1",
                valueInputOption="USER_ENTERED",
                body={"values": headers}
            ).execute()
            st.success(f"Sheet '{sheet_name}' created successfully.")
    except Exception as e:
        st.error(f"Error ensuring sheet exists: {e}")

active_sheet_name = get_active_sheet_name(frequency="daily")
ensure_active_sheet_exists(active_sheet_name)  # Ensure the sheet exists

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
            range=f"{active_sheet_name}!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": data}
        ).execute()
    except Exception as e:
        st.error(f"Error writing to Google Sheet: {e}")

def update_google_sheet_checkout(student_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        # Read data from the active sheet
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f"{active_sheet_name}!A:E").execute()
        values = result.get('values', [])

        if not values:
            st.error("No data found in the sheet.")
            return False

        updated = False
        for i, row in enumerate(values):
            if len(row) >= 4 and row[1] == student_name and row[3] == "-":
                check_in_time = datetime.strptime(row[2], '%H:%M')
                check_out_time = datetime.now()
                time_difference = check_out_time - check_in_time

                duration = f"{time_difference.seconds // 3600}h {time_difference.seconds % 3600 // 60}m"
                row[3] = check_out_time.strftime('%H:%M')
                row[4] = duration

                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"{active_sheet_name}!A{i+1}:E{i+1}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [row]}
                ).execute()

                updated = True
                break

        if not updated:
            st.error(f"No check-in record found for {student_name}.")
        return updated

    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")
        return False

def is_already_checked_in_google(student_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f"{active_sheet_name}!A:E").execute()
        values = result.get('values', [])
        
        for row in values:
            if len(row) >= 4 and row[1] == student_name and row[3] == "-":
                return True
        return False

    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
        return False

def fetch_student_names_from_google_sheet():
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="STUDENT_NAMES!A:A").execute()
        values = result.get('values', [])
        return [row[0] for row in values if row]
    except Exception as e:
        st.error(f"Error fetching student names from Google Sheet: {e}")
        return []

def fetch_student_names_from_file():
    try:
        with open("students.txt", "r") as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        st.warning("students.txt file not found. Please create the file with student names.")
        return []

# Streamlit UI
st.title("Blooming Buds Daily Attendance Tracker")

# Fetch student names from both Google Sheets and students.txt
students_from_file = fetch_student_names_from_file()
students_from_google_sheet = fetch_student_names_from_google_sheet()
students = list(set(students_from_file + students_from_google_sheet))  # Combine and remove duplicates

if students:
    students.insert(0, "Choose an option")  # Add placeholder option
    student_name = st.selectbox("Select a Student", students)

    if student_name == "Choose an option":
        st.warning("Please select a valid student.")
    else:
        action = st.radio("Action", ["Check In", "Check Out"])

        if st.button("Submit"):
            if action == "Check In":
                if is_already_checked_in_google(student_name):
                    st.error(f"{student_name} is already checked in. Please check out first.")
                else:
                    check_in_time = datetime.now().strftime('%H:%M')
                    append_to_google_sheet(student_name, check_in=check_in_time, check_out="-", time_difference="-")
                    st.success(f"{student_name} checked in at {check_in_time}.")
            elif action == "Check Out":
                if update_google_sheet_checkout(student_name):
                    st.success(f"{student_name} checked out.")
else:
    st.error("No students found. Please add students to 'students.txt' or Google Sheets.")
