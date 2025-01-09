import streamlit as st
import csv
from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Replace with your service account key file
SPREADSHEET_ID = '1SzhjrM9pixwbfuW7PHB0q6vWIdI-6UH6zNmGB07XxbA'  # Replace with your Google Sheet ID

def get_google_sheets_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

# Timezone setup
CHICAGO_TZ = pytz.timezone("America/Chicago")

def get_current_time():
    return datetime.now(pytz.utc).astimezone(CHICAGO_TZ)

def get_current_sheet_name(frequency):
    today = get_current_time().date()
    if frequency == "daily":
        return today.strftime("%Y-%m-%d")
    elif frequency == "weekly":
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return f"Week {start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}"
    elif frequency == "monthly":
        return today.strftime("%Y-%m")

def ensure_sheet_exists(service, spreadsheet_id, sheet_name):
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        sheet_titles = [sheet['properties']['title'] for sheet in sheets]

        if sheet_name not in sheet_titles:
            body = {
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
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
    except Exception as e:
        st.error(f"Error ensuring sheet exists: {e}")

def append_to_google_sheet(student_name, check_in=None, check_out=None, time_difference=None, frequency="daily"):
    service = get_google_sheets_service()
    sheet_name = get_current_sheet_name(frequency)
    ensure_sheet_exists(service, SPREADSHEET_ID, sheet_name)
    data = [[
        get_current_time().strftime('%Y-%m-%d'),
        student_name,
        check_in,
        check_out,
        time_difference
    ]]
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A:E",
            valueInputOption="USER_ENTERED",
            body={"values": data}
        ).execute()
    except Exception as e:
        st.error(f"Error writing to Google Sheet: {e}")

def update_google_sheet_checkout(student_name, frequency="daily"):
    service = get_google_sheets_service()
    sheet_name = get_current_sheet_name(frequency)
    ensure_sheet_exists(service, SPREADSHEET_ID, sheet_name)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A:E"
        ).execute()
        values = result.get('values', [])

        if not values:
            st.error("No data found in the sheet.")
            return False

        updated = False
        for i, row in enumerate(values):
            if len(row) >= 4 and row[1] == student_name and row[3] == "-":
                check_in_time = datetime.strptime(row[2], '%H:%M').replace(tzinfo=CHICAGO_TZ)
                check_out_time = get_current_time()
                time_difference = check_out_time - check_in_time
                duration = f"{time_difference.seconds // 3600}h {time_difference.seconds % 3600 // 60}m"

                row[3] = check_out_time.strftime('%H:%M')
                row[4] = duration

                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"{sheet_name}!A{i+1}:E{i+1}",
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

def is_already_checked_in_google(student_name, frequency="daily"):
    service = get_google_sheets_service()
    sheet_name = get_current_sheet_name(frequency)
    ensure_sheet_exists(service, SPREADSHEET_ID, sheet_name)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!A:E"
        ).execute()
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
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!H:H").execute()
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
st.title("Attendance Tracker")

# Frequency for creating new sheets
frequency = st.selectbox("Select Frequency", ["daily", "weekly", "monthly"])

# Fetch student names from both Google Sheets and students.txt
students_from_file = fetch_student_names_from_file()
students_from_google_sheet = fetch_student_names_from_google_sheet()
students = list(set(students_from_file + students_from_google_sheet))  # Combine and remove duplicates

if students:
    student_name = st.selectbox("Select a Student", students)
    action = st.radio("Action", ["Check In", "Check Out"])

    if st.button("Submit"):
        if action == "Check In":
            if is_already_checked_in_google(student_name, frequency):
                st.error(f"{student_name} is already checked in. Please check out first.")
            else:
                check_in_time = get_current_time().strftime('%H:%M')
                append_to_google_sheet(student_name, check_in=check_in_time, check_out="-", time_difference="-", frequency=frequency)
                st.success(f"{student_name} checked in at {check_in_time}.")
        elif action == "Check Out":
            if update_google_sheet_checkout(student_name, frequency):
                st.success(f"{student_name} checked out.")
            else:
                st.error(f"No check-in record found for {student_name}.")
else:
    st.error("No students found. Please add students to 'students.txt' or Google Sheets.")
