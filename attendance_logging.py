import streamlit as st
import csv
from datetime import datetime

# File paths
STUDENT_FILE = "students.txt"
LOG_FILE = "attendance_log.csv"

# Load student names from file
def load_students():
    try:
        with open(STUDENT_FILE, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        st.error(f"{STUDENT_FILE} not found.")
        return []

# Write attendance entry to CSV file
def write_to_log(student_name, check_in=None, check_out=None, time_difference=None):
    try:
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(["Date", "Student Name", "Check In Time", "Check Out Time", "Duration"])

            writer.writerow([datetime.now().strftime('%Y-%m-%d'), student_name, check_in, check_out, time_difference])
    except Exception as e:
        st.error(f"Could not write to log file: {e}")

# Find an existing entry for check-out and update duration
def find_and_update_checkout(student_name):
    try:
        rows = []
        updated = False
        with open(LOG_FILE, 'r', newline='') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                if len(row) >= 5 and not updated and row[1] == student_name and row[3] == '':
                    check_in_time = datetime.strptime(row[2], '%H:%M:%S')
                    check_out_time = datetime.now()
                    row[3] = check_out_time.strftime('%H:%M:%S')
                    duration = check_out_time - check_in_time
                    row[4] = f"{duration.seconds // 3600}h {duration.seconds % 3600 // 60}m"
                    updated = True
                rows.append(row)

        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return updated
    except FileNotFoundError:
        st.error(f"{LOG_FILE} not found.")
        return False
    except Exception as e:
        st.error(f"Could not update log file: {e}")
        return False

# Check if a student is already checked in
def is_already_checked_in(student_name):
    try:
        with open(LOG_FILE, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) >= 4 and row[1] == student_name and row[3] == '':
                    return True
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        st.error(f"Could not read log file: {e}")
        return False

# Streamlit UI
st.title("Attendance Tracker")
students = load_students()

if students:
    student_name = st.selectbox("Select a Student", students)
    action = st.radio("Action", ["Check In", "Check Out"])

    if st.button("Submit"):
        if action == "Check In":
            if is_already_checked_in(student_name):
                st.error(f"{student_name} is already checked in. Please check out first.")
            else:
                check_in_time = datetime.now().strftime('%H:%M:%S')
                write_to_log(student_name, check_in=check_in_time)
                st.success(f"{student_name} checked in at {check_in_time}.")
        elif action == "Check Out":
            if find_and_update_checkout(student_name):
                st.success(f"{student_name} checked out.")
            else:
                st.error(f"No check-in record found for {student_name}.")
else:
    st.error("No students found.")
