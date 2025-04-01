import sqlite3
import streamlit as st
import time
import io
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
from math import ceil

def layout():
    st.set_page_config(page_title="OAI", layout="wide")

    st.markdown("""
        <style>
        #MainMenu {visibility:hidden;}
        footer {visibility:hidden;}
        
        div.block-container {padding-top:0rem;}
        button[title="View fullscreen"]{
    visibility: hidden;}
    
    .block-container {padding-top:0rem ;padding-bottom:0rem;}
    /* Remove blank space at the center canvas */ 
           .st-emotion-cache-z5fcl4 {
               position: relative;
               top: -62px;
               }
        
           
           
        </style>
    """, unsafe_allow_html=True)

@st.dialog("Error")
def error_message(message):
    st.write(message)


def handle_restart():
    st.session_state['user_type'] = None
    st.session_state['purpose'] = None
    st.session_state['supplies_form'] = None
    st.session_state['logged_in'] = False
    st.rerun()

def create_table():
    connection = sqlite3.connect('sign_in.db')
    cursor = connection.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS "users"  (
	"ucnetid"	TEXT,
	"firstname"	TEXT,
	"lastname"	TEXT,
	"gender"	TEXT,
	"first_generation_student"	TEXT,
	"transfer_student"	TEXT,
	"major"	TEXT,
	"year"	TEXT,
	"enabled_user"	INTEGER,
	PRIMARY KEY("ucnetid")
);''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS "supplies" (
    "supply_id" INTEGER,
    "printing_paper" INTEGER,
    "printing_3d" INTEGER,
    "testing_supplies" INTEGER,
    "coffee" INTEGER,
    "snacks" INTEGER,
    "other" TEXT,
    PRIMARY KEY("supply_id" AUTOINCREMENT)
);''')
    
    cursor.execute('''INSERT INTO supplies (printing_paper, printing_3d, testing_supplies, coffee, snacks, other)
SELECT 0, 0, 0, 0, 0, 0
WHERE NOT EXISTS (SELECT 1 FROM supplies WHERE supply_id = 1);
''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS "transaction_log"  (
	"visit_id"	INTEGER,
	"ucnetid"	TEXT,
	"timestamp"	NUMERIC DEFAULT CURRENT_TIMESTAMP,
	"supply_id"	INTEGER,
	"advice"	INTEGER,
	"tutor"	INTEGER,
	"wellness_corner"	INTEGER,
	"hangout"	INTEGER,
	"study_center"	INTEGER,
	FOREIGN KEY("ucnetid") REFERENCES "users"("ucnetid"),
	PRIMARY KEY("visit_id" AUTOINCREMENT)
);''')
    
    connection.commit()
    connection.close()

def check_user(ucnetid,student_id):
    connection = sqlite3.connect('sign_in.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM users WHERE (ucnetid = ? AND enabled_user = 1) OR (student_id = ? AND enabled_user = 1)', (ucnetid,student_id))
    user = cursor.fetchone()
    connection.close()
    return user

def check_supplies(supplies):
    paper = 1 if "Printer" in supplies else 0
    printing3d = 1 if "3D printer" in supplies else 0
    testing = 1 if "Test materials" in supplies else 0
    coffee = 1 if "Coffee" in supplies else 0
    snacks = 1 if "Snacks" in supplies else 0
    other = 1 if "Other" in supplies else 0

    connection = sqlite3.connect('sign_in.db')
    cursor = connection.cursor()

    cursor.execute('''SELECT supply_id 
                      FROM supplies 
                      WHERE printing_paper = ? 
                        AND printing_3d = ? 
                        AND testing_supplies = ? 
                        AND coffee = ? 
                        AND snacks = ? 
                        AND other = ?''', 
                   (paper, printing3d, testing, coffee, snacks, other))

    supply_id = cursor.fetchone()

    if supply_id:
        connection.close()
        return supply_id[0]
    else:   
        cursor.execute('''INSERT INTO supplies (printing_paper, printing_3d, testing_supplies, coffee, snacks, other) 
                            VALUES (?, ?, ?, ?, ?, ?)''', 
                        (paper, printing3d, testing, coffee, snacks, other))
            
        connection.commit()
            
        cursor.execute('''SELECT supply_id 
                            FROM supplies 
                            WHERE printing_paper = ? 
                                AND printing_3d = ? 
                                AND testing_supplies = ? 
                                AND coffee = ? 
                                AND snacks = ? 
                                AND other = ?''', 
                        (paper, printing3d, testing, coffee, snacks, other))

        new_supply_id = cursor.fetchone()
        connection.close()
        return new_supply_id[0]


def add_new_user(ucnetid, firstname, lastname, gender, first_gen, transfer_student, major, year,other_major,student_id):
    try:
        connection = sqlite3.connect('sign_in.db')
        cursor = connection.cursor()
        cursor.execute('''INSERT INTO users (ucnetid, firstname, lastname, gender, first_generation_student, transfer_student, major, year, enabled_user, other_major,student_id) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)''', 
                          (ucnetid, firstname, lastname, gender, first_gen, transfer_student, major, year, 1,other_major,student_id))
        connection.commit()
        connection.close()
        return True
    except sqlite3.IntegrityError:
        return False

def record_transaction(ucnetid, purpose, supply_id):
    connection = sqlite3.connect('sign_in.db')
    cursor = connection.cursor()
    
    advice = 1 if "Meet/request advice from OAI staff" in purpose else 0
    tutor = 1 if "Use the OAI tutoring services" in purpose else 0
    study_center = 1 if "Use the study center" in purpose else 0
    wellness_corner = 1 if "Spend time in the OAI Wellness Corner" in purpose else 0
    hangout = 1 if "Hang out with friends" in purpose else 0
    
    cursor.execute('''INSERT INTO transaction_log (ucnetid, supply_id, advice, tutor, wellness_corner, hangout, study_center) 
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                   (ucnetid, supply_id, advice, tutor, wellness_corner, hangout, study_center))
    
    connection.commit()
    connection.close()

@st.dialog("Supplies")
def supplies_form(ucnetid, purpose):
    with st.form('Supplies Form'):
        supplies = st.multiselect("Select supplies you are here for:", ["Printer", "3D printer", "Coffee", "Snacks", "Test materials", "Other"])
        other = st.text_input("Other supplies you're using.")
        submit_button = st.form_submit_button("Submit")
        
        if submit_button:
            if not supplies:
                st.error("Please select at least one supply.")
            else:
                supply_id = check_supplies(supplies)
                record_transaction(ucnetid, purpose, supply_id)
                st.toast('Submitted, thanks')
                time.sleep(1)
                handle_restart()

#@st.dialog(title='New user',width='large')    
def new_user_form():
    with st.form('new_user'):
        ucnetid = st.text_input("Enter your UCI email")
        ucnetid = ucnetid.lower()
        student_id = '...................'
        st.session_state['ucnetid'] = ucnetid
        firstname = st.text_input("Enter your first name")
        lastname = st.text_input("Enter your last name")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=None,placeholder="Gender")
        first_gen = st.selectbox("Are you a first-generation student?", ["Yes", "No"], index=None,placeholder="First Generation")
        transfer_student = st.selectbox("Are you a transfer student?", ["Yes", "No"], index=None,placeholder="Transfer")
        major = st.selectbox("Select your major", [
            "Mechanical Engineering", "Electrical Engineering", "Computer Science", 
            "Civil Engineering", "Bioengineering", "Chemical Engineering", 
            "Materials Science", "Aerospace Engineering", "Software Engineering", 
            "Environmental Engineering", "Engineering Physics", "Other"
        ], index=None,placeholder="Major")
        other_major = st.text_input("Enter other major not in Engineering")
        year = st.selectbox("Select your year", ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"], index=None,placeholder="Year")

        purpose = st.multiselect("What is the purpose of your visit?", 
                                 ["Meet/request advice from OAI staff", "Use the OAI tutoring services", "Spend time in the OAI Wellness Corner", "Hang out with friends", "Use OAI resources", "Use the study center"]
)
        st.session_state['purpose'] = purpose
        submit_button = st.form_submit_button("Submit")
    
        if submit_button:
            if not ucnetid or not firstname or not lastname or not major or not purpose:
                time.sleep(1)
                st.error("All fields are required.")
                error_message("All fields are required.")
                st.toast("All fields are required.")
            else:
                user = check_user(ucnetid,student_id)
                success = add_new_user(ucnetid, firstname, lastname, gender, first_gen, transfer_student, major, year,other_major,student_id)
                if not success or user:
                    st.error(f"UCNetID {ucnetid} is already registered. Please go to returning user form.")
                    st.toast(f"UCNetID {ucnetid} is already registered. Please go to returning user form.")
                    time.sleep(5)
                    handle_restart()
                else:
                        st.write(f'New user {firstname} {lastname} added successfully')
                        if "Use OAI resources" in purpose:
                            st.toast("Please enter your chosen supplies")
                            st.session_state['supplies_form'] = True
                        else:
                            st.session_state['supplies_form'] = False
                            record_transaction(ucnetid, purpose, 1)
                            time.sleep(1)
                            handle_restart()

#@st.dialog(title='Returning user',width='large')                        
def returning_user_form():
    with st.form('returning user'):
        ucnetid = st.text_input("Enter your ucnetid email(Example: sahr3824@uci.edu). Don't use your student id")
        
        st.session_state['ucnetid'] = ucnetid
        purpose = st.multiselect("What is the purpose of your visit? (CHECK ALL THAT APPLY)", 
                                 ["Meet/request advice from OAI staff", "Use the OAI tutoring services", "Spend time in the OAI Wellness Corner", "Hang out with friends", "Use OAI resources", "Use the study center"])
        st.session_state['purpose'] = purpose
        submit_button = st.form_submit_button("Submit")
        
        if submit_button:
            if not purpose or not ucnetid:
                st.error("All fields are required.")
                st.toast("All fields are required.")
            else:
                user = check_user(ucnetid,ucnetid)
                st.session_state['purpose'] = purpose
                if user and user[-1] == 0:  
                    st.error(f"Your account (UCNetID: {ucnetid}) is disabled. Please contact support.")
                    st.toast(f"Your account (UCNetID: {ucnetid}) is disabled. Please contact support.")
                    time.sleep(3)
                    handle_restart()
                elif not user:
                    st.error("We don't recognize you. Please go to 'checkin home' to the new user form or contact support.")
                    st.toast("We don't recognize you. Please go to 'checkin home' to the new user form or contact support.")
                    time.sleep(3)
                    handle_restart()

                else:
                    st.success(f"Welcome back {user[1]} {user[2]}, please proceed.")
                    if "Use OAI resources" not in purpose:
                        st.session_state['supplies_form'] = False
                        record_transaction(ucnetid, purpose, 1)
                        time.sleep(1)
                        handle_restart()
                    else:
                        st.session_state['supplies_form'] = True

def new_user_click():
    st.session_state['user_type'] = 'new_user'

def returning_user_click():
    st.session_state['user_type'] = 'returning_user'

def dashboard_click():
    st.session_state['user_type'] = 'dashboard'

def read_image(filename):
    with sqlite3.connect('sign_in.db') as conn:
        cur = conn.cursor()
        cur.execute(f'select data from binary_data where filename = "{filename}"')
        data = cur.fetchone()
        tempstore = io.BytesIO(data[0])
    return tempstore


if 'user_type' not in st.session_state:
    st.session_state['user_type'] = None
    st.session_state['purpose'] = None
    st.session_state['supplies_form'] = None

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def dashboard():
    tab1, tab2, tab3 = st.tabs(["Dashboard", "User Management", "Date Range"])

    now = datetime.now()
    with tab1:
        with sqlite3.connect('sign_in.db') as conn:
            cursor = conn.cursor()
            st.subheader("General Statistics")
            col1, col2 = st.columns(2)

            with col1:
                cursor.execute('''SELECT COUNT(*) FROM users WHERE enabled_user = 1''')
                user_count = cursor.fetchone()[0]
                st.write(f"There are {user_count} users.")

                
                cursor.execute(''' 
                    SELECT major, COUNT(major) as count
                    FROM users
                    WHERE enabled_user = 1
                    GROUP BY major
                    ORDER BY count DESC
                    LIMIT 1

                ''')
                popular_major = cursor.fetchone()
                if popular_major:
                    st.write(f"The most popular major is {popular_major[0]} with {popular_major[1]} students.")

                cursor.execute(''' 
                    SELECT year, COUNT(year) as count
                    FROM users
                    WHERE enabled_user = 1           
                    GROUP BY year
                    ORDER BY count DESC
                    LIMIT 1
                ''')
                popular_major = cursor.fetchone()
                if popular_major:
                    st.write(f"The most popular year is {popular_major[0]} with {popular_major[1]} students.")

                cursor.execute(''' 
        SELECT first_generation_student, COUNT(first_generation_student) as count
        FROM users
        WHERE enabled_user = 1
        GROUP BY first_generation_student
        ORDER BY count DESC
    ''')
                first_gen_data = cursor.fetchall()
                first_gen_dict = {row[0]: row[1] for row in first_gen_data}
                yes_first_gen = first_gen_dict.get("Yes", 0)
                no_first_gen = first_gen_dict.get("No", 0)
                
                st.write(f"{no_first_gen} students are not first-generation students. {yes_first_gen} students are first-generation students.")

                cursor.execute(''' 
        SELECT transfer_student, COUNT(transfer_student) as count
        FROM users
        WHERE enabled_user = 1
        GROUP BY transfer_student
        ORDER BY count DESC
    ''')
                transfer_data = cursor.fetchall()

                transfer_dict = {row[0]: row[1] for row in transfer_data}
                yes_transfer = transfer_dict.get("Yes", 0)
                no_transfer = transfer_dict.get("No", 0)
                
                st.write(f"{yes_transfer} students are transfer students. {no_transfer} students are not transfer students.")

                cursor.execute(''' 
                    SELECT gender, COUNT(gender) as count
                    FROM users
                    WHERE enabled_user = 1
                    GROUP BY gender
                    ORDER BY count DESC
                ''')
                popular_major = cursor.fetchall()
                
                

            with col2:
                st.write("### Past hour")
                past_1_hour = now - timedelta(hours=1)
                cursor.execute(''' 
                    SELECT users.firstname, users.lastname, transaction_log.ucnetid 
                    FROM transaction_log
                    JOIN users ON transaction_log.ucnetid = users.ucnetid
                    WHERE users.enabled_user = 1 AND timestamp >= datetime('now','-1 hour')
                    group by users.ucnetid
                ''')
                data_1h = cursor.fetchall()

                if data_1h:
                    df_1h = pd.DataFrame(data_1h, columns=["First Name", "Last Name", "UCNetID"])
                    df_1h["Email"] = df_1h["UCNetID"] 
                    st.table(df_1h[["First Name", "Last Name", "Email"]])
                else:
                    st.write("No data available for the past hour.")

                st.write("### Past 5 hours")
                past_5_hours = now - timedelta(hours=5)
                cursor.execute(''' 
                    SELECT users.firstname, users.lastname, transaction_log.ucnetid 
                    FROM transaction_log
                    JOIN users ON transaction_log.ucnetid = users.ucnetid
                    WHERE users.enabled_user = 1 AND timestamp >= datetime('now','-5 hour')
                    group by users.ucnetid
                ''')
                data_5h = cursor.fetchall()

                if data_5h:
                    df_5h = pd.DataFrame(data_5h, columns=["First Name", "Last Name", "UCNetID"])
                    df_5h["Email"] = df_5h["UCNetID"] 
                    st.table(df_5h[["First Name", "Last Name", "Email"]])
                else:
                    st.write("No data available for the past 5 hours.")
            
                time_periods = {
                    "Past week": timedelta(weeks=1),
                    "Past month": timedelta(days=30),
                    "All Time": None  
                }

                for period, delta in sorted(time_periods.items(), key=lambda x: x[1] if x[1] else timedelta.max):
                    with st.expander(period):
                        
                        if delta:
                            past_time = now - delta
                            cursor.execute(''' 
                                SELECT users.firstname, users.lastname, transaction_log.ucnetid 
                                FROM transaction_log
                                JOIN users ON transaction_log.ucnetid = users.ucnetid
                                WHERE users.enabled_user = 1 AND timestamp >= datetime('now','-24 hour')
                                group by users.ucnetid''')
                        else:
                            cursor.execute(''' 
                                SELECT users.firstname, users.lastname, transaction_log.ucnetid 
                                FROM transaction_log
                                JOIN users ON transaction_log.ucnetid = users.ucnetid
                            ''')

                        data = cursor.fetchall()

                        if data:
                            df = pd.DataFrame(data, columns=["First Name", "Last Name", "UCNetID"])
                            df["Email"] = df["UCNetID"] 
                            

                            st.table(df[["First Name", "Last Name", "Email"]])
                        else:
                            st.write("No data available for this period.")


                st.write("### Services Usage:")
                cursor.execute('''
                    SELECT 
                        SUM(advice) AS advice_count,
                        SUM(tutor) AS tutor_count,
                        SUM(wellness_corner) AS wellness_corner_count,
                        SUM(hangout) AS hangout_count,
                        SUM(study_center) AS study_center_count
                    FROM transaction_log
                    join users on transaction_log.ucnetid = users.ucnetid
                    where users.enabled_user = 1

                ''')
                service_counts = cursor.fetchone()

                service_dict = {
                    "Advice": service_counts[0],
                    "Tutoring": service_counts[1],
                    "Wellness Corner": service_counts[2],
                    "Hangout": service_counts[3],
                    "Study center": service_counts[4]
                }
                cursor.execute('''
                    SELECT count(*) FROM transaction_log
    JOIN supplies ON transaction_log.supply_id = supplies.supply_id
    WHERE supplies.supply_id != 1;

                ''')
                count_of_total_supplies = cursor.fetchone()

                service_dict["Supplies"] = count_of_total_supplies[0]
                cursor.execute('''
                    SELECT 
                        SUM(printing_3d) AS printing_3d_count,
                        SUM(printing_paper) AS printing_paper_count,
                        SUM(testing_supplies) AS testing_supplies_count,
                        SUM(coffee) AS coffee_count,
                        SUM(snacks) AS snacks_count,
						SUM(other) as other_count
                    FROM transaction_log
                    join supplies on transaction_log.supply_id = supplies.supply_id
                ''')
                supplies_counts = cursor.fetchone()

                service_df = pd.DataFrame(list(service_dict.items()), columns=['Service', 'Count'])
                service_df = service_df.sort_values(by='Count', ascending=False)
                st.bar_chart(service_df.set_index('Service'))

                st.write("### Most Used Supplies:")
                supplies_dict = {
                    "3D": supplies_counts[0],
                    "Printing": supplies_counts[1],
                    "Coffee": supplies_counts[2],
                    "Snacks": supplies_counts[3],
                    "Testing supplies": supplies_counts[4],
                    "Other": supplies_counts[5]
                }

                supplies_df = pd.DataFrame(list(supplies_dict.items()), columns=['Supply', 'Count'])
                supplies_df = supplies_df.sort_values(by='Count', ascending=False)
                st.bar_chart(supplies_df.set_index('Supply'))

        with tab2:
            st.subheader("Manage Users")
            cursor.execute("SELECT ucnetid, firstname, lastname FROM users WHERE enabled_user = 1")
            users_data = cursor.fetchall()

            if users_data:
                df_users = pd.DataFrame(users_data, columns=["UCNetID", "First Name", "Last Name"])
                
                df_users['Full Info'] = df_users['First Name'] + " " + df_users['Last Name'] + ", " + df_users['UCNetID']
                
                selected_user = st.selectbox("Select a user to disable", df_users['Full Info'])
                
                selected_user_ucnetid = df_users.loc[df_users['Full Info'] == selected_user, 'UCNetID'].values[0]
                
                if st.button("Disable User"):
                    cursor.execute("UPDATE users SET enabled_user = 0 WHERE ucnetid = ?", (selected_user_ucnetid,))
                    conn.commit()
                    st.success(f"User {selected_user_ucnetid} has been disabled.")
                    
                    cursor.execute("SELECT ucnetid, firstname, lastname FROM users WHERE enabled_user = 1")
                    users_data = cursor.fetchall()
                    df_users = pd.DataFrame(users_data, columns=["UCNetID", "First Name", "Last Name"])
                    st.table(df_users)

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", min_value=datetime(2020, 1, 1), value=datetime(2024, 9, 27))
            with col2:
                end_date = st.date_input("End Date", min_value=start_date)

            if start_date > end_date:
                st.error("Start Date cannot be later than End Date. Please select valid dates.")
            else:
                with sqlite3.connect('sign_in.db') as conn:
                    cursor = conn.cursor()

                    cursor.execute(''' 
                        SELECT transaction_log.timestamp, 
                            transaction_log.ucnetid, 
                            users.firstname, 
                            users.lastname,
                            transaction_log.advice,
                            transaction_log.tutor,
                            transaction_log.wellness_corner,
                            transaction_log.hangout,
                            transaction_log.study_center,
                            transaction_log.supply_id,
                            supplies.printing_3d,
                            supplies.printing_paper,
                            supplies.coffee,
                            supplies.testing_supplies,
                            supplies.other
                        FROM transaction_log
                        JOIN users ON transaction_log.ucnetid = users.ucnetid
                        JOIN supplies ON supplies.supply_id = transaction_log.supply_id
                        WHERE users.enabled_user = 1 
                        AND timestamp BETWEEN ? AND ?
                    ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                    
                    data = cursor.fetchall()

                    if data:
                        processed_data = []
                        
                        for row in data:
                            timestamp, ucnetid, firstname, lastname, advice, tutor, wellness, hangout, study_center, supply_id, printing_3d, printing_paper, coffee, testing_supplies, other = row
                            formatted_timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%y %I:%M %p')

                            selected_services = []
                            
                            if advice == 1:
                                selected_services.append('Advice')
                            if tutor == 1:
                                selected_services.append('Tutoring')
                            if wellness == 1:
                                selected_services.append('Wellness Corner')
                            if hangout == 1:
                                selected_services.append('Hangout')
                            if study_center == 1:
                                selected_services.append('Study Center')

                            selected_supplies = []
                            if printing_3d == 1:
                                selected_supplies.append('3D Printing')
                            if printing_paper == 1:
                                selected_supplies.append('Printing Paper')
                            if coffee == 1:
                                selected_supplies.append('Coffee')
                            if testing_supplies == 1:
                                selected_supplies.append('Testing Supplies')
                            if other == 1:
                                selected_supplies.append('Other Supplies')

                            all_selected = selected_services + selected_supplies
                            supplies_column = ', '.join(all_selected) if all_selected else 'No services or supplies selected'

                            processed_data.append([formatted_timestamp, ucnetid, firstname, lastname, supplies_column])

                        df = pd.DataFrame(processed_data, columns=["Timestamp", "Email", "First Name", "Last Name", "Purpose"])

                        st.table(df)
                    else:
                        st.write("No data available for the selected date range.")




create_table()
layout()

if st.session_state.get('user_type') is None:
    with st.container():
        st.image(read_image('banner.png'), width=450) 

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=2, height= 320):
            st.button("New Student", on_click=new_user_click, type="primary")
            st.image(read_image('new.png'), width=190)  
    with col2:
        with st.container(border=2, height= 320):
            st.button("Returning Student", on_click=returning_user_click, type="primary")
            st.image(read_image('return.png'), width=190) 

    st.button("Dashboard", on_click=dashboard_click)

elif st.session_state.get('user_type') == 'new_user':
    with st.container(border= 1):
        st.header("New Student Check-in")
        st.image(read_image('new.png'), width=100)
        st.button("CHECKIN HOME", on_click=handle_restart)
    new_user_form()

elif st.session_state.get('user_type') == 'returning_user':
    with st.container(border= 1):
        st.header("Returning Student Check-in")
        st.image(read_image('return.png'), width=100)
        st.button("CHECKIN HOME", on_click=handle_restart)
    returning_user_form()

elif st.session_state.get('user_type') == 'dashboard':
    st.markdown("""
        <style>
        #MainMenu {visibility:hidden;}
        footer {visibility:hidden;}
        
        div.block-container {padding-top:0rem;}
        button[title="View fullscreen"]{
    visibility: hidden;}
    
    .block-container {padding-top:3rem ;padding-bottom:0rem;}
    /* Remove blank space at the center canvas */ 
           .st-emotion-cache-z5fcl4 {
               position: relative;
               top: -65px;
               }
        
           
           
        </style>
    """, unsafe_allow_html=True)
    if not st.session_state.get('logged_in', False):  
        st.write("")
        st.write("")
        with st.form("login_form"):
            password = st.text_input("Enter the password", type='password')  
            submit_button = st.form_submit_button("Submit", type="primary")
            
            if submit_button and password == '1234':  
                st.session_state['logged_in'] = True
                st.session_state['user_type'] = 'dashboard' 
                st.rerun() 
            elif submit_button:
                st.error("Incorrect password. Please try again.")
    else: 
        st.write("")
        st.write("")
        st.header("Dashboard")
        st.button("CHECKIN HOME", on_click=handle_restart)
        
        dashboard()  
if st.session_state.get('supplies_form') == True:
    supplies_form(st.session_state.get('ucnetid'), st.session_state.get('purpose'))
