import streamlit as st
import csv
import tomllib
from datetime import datetime
import pytz
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Replace with your service account key file
SPREADSHEET_ID = '1OYqCY_-XSg05wrgwYJvgTnZACA1Qm8qZOWiordeViZc'  # Replace with your Google Sheet ID

# Set Chicago timezone
CHICAGO_TZ = pytz.timezone('America/Chicago')

# Authenticate Google Sheets API
def get_google_sheets_service():
    creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def get_active_sheet_name(frequency="daily"):
    now = datetime.now(CHICAGO_TZ)
    if frequency == "daily":
        return now.strftime('%Y-%m-%d')
    elif frequency == "weekly":
        return f"Week-{now.strftime('%U')}-{now.year}"
    elif frequency == "monthly":
        return now.strftime('%Y-%m')
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

active_sheet_name = get_active_sheet_name(frequency="monthly")
ensure_active_sheet_exists(active_sheet_name)  # Ensure the sheet exists

def append_to_google_sheet(teacher_name, check_in=None, check_out=None, time_difference=None):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    now = datetime.now(CHICAGO_TZ)
    data = [[
        now.strftime('%Y-%m-%d'),
        teacher_name,
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

def update_google_sheet_checkout(teacher_name):
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
            if len(row) >= 4 and row[1] == teacher_name and row[3] == "-":
                check_in_time = CHICAGO_TZ.localize(datetime.strptime(row[2], '%H:%M'))
                check_out_time = datetime.now(CHICAGO_TZ)
                time_difference = check_out_time - check_in_time
                
                # Calculate duration correctly
                hours = time_difference.total_seconds() // 3600
                minutes = (time_difference.total_seconds() % 3600) // 60
                duration = f"{int(hours)}h {int(minutes)}m"
                
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
            st.error(f"No check-in record found for {teacher_name}.")
        return updated

    except Exception as e:
        st.error(f"Error updating Google Sheet: {e}")
        return False

def is_already_checked_in_google(teacher_name):
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=f"{active_sheet_name}!A:E").execute()
        values = result.get('values', [])
        
        for row in values:
            if len(row) >= 4 and row[1] == teacher_name and row[3] == "-":
                return True
        return False

    except Exception as e:
        st.error(f"Error reading Google Sheet: {e}")
        return False

def fetch_teacher_names_from_google_sheet():
    service = get_google_sheets_service()
    sheet = service.spreadsheets()
    try:
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="TEACHER_NAMES!A:A").execute()
        values = result.get('values', [])
        return [row[0] for row in values if row]
    except Exception as e:
        st.error(f"Error fetching teacher names from Google Sheet: {e}")
        return []

# def fetch_teacher_names_from_file():
#     try:
#         with open("teachers.txt", "r") as file:
#             return [line.strip() for line in file.readlines()]
#     except FileNotFoundError:
#         st.warning("teachers.txt file not found. Please create the file with teacher names.")
#         return []

# Streamlit UI
st.title("Blooming Buds Teacher Check In")

# Fetch teacher names from both Google Sheets and teachers.txt
# teachers_from_file = fetch_teacher_names_from_file()
teachers_from_google_sheet = fetch_teacher_names_from_google_sheet()
teachers = list(set(teachers_from_google_sheet))  # Combine and remove duplicates

if teachers:
    teachers.insert(0, "Choose an option")  # Add placeholder option
    teachers = list(set(teachers_from_google_sheet))  # Combine and remove duplicates
    teachers = sorted(teachers)  # Sort names alphabetically
    teachers.insert(0, "Choose an option")  # Add placeholder option
    teacher_name = st.selectbox("Select a Teacher", teachers, index=0)  # Set default index to placeholder


    if teacher_name == "Choose an option":
        st.warning("Please select a valid teacher.")
    else:
        action = st.radio("Action", ["Check In", "Check Out"])

        if st.button("Submit"):
            if action == "Check In":
                if is_already_checked_in_google(teacher_name):
                    st.error(f"{teacher_name} is already checked in. Please check out first.")
                else:
                    check_in_time = datetime.now(CHICAGO_TZ).strftime('%H:%M')
                    append_to_google_sheet(teacher_name, check_in=check_in_time, check_out="-", time_difference="-")
                    st.success(f"{teacher_name} checked in at {check_in_time}.")
            elif action == "Check Out":
                if update_google_sheet_checkout(teacher_name):
                    st.success(f"{teacher_name} checked out.")
else:
    st.error("No teachers found. Please add teachers to Google Sheets.")
