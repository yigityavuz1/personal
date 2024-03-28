import json
import streamlit as st
import requests

from functions import show_questions

url = f"http://20.71.70.168"

st.title("Koç Holding Pre-Assessment Demo")
request_type = st.sidebar.radio(
    label="Request Type",
    options=["Job Description", "Applicant"])

if request_type == "Job Description":
    form = st.form(key="job-description-form")

    job_name = form.text_input(label="Job Name ")
    job_description_name = form.text_input(label="Job Description")
    qualification_title = form.text_input(label="Qualification Title")
    qualifications = form.text_area(label="Qualifications")

    jd_submit = form.form_submit_button(label="Submit")

    if jd_submit:
        endpoint = "/from_job_description"
        full_url = url + endpoint
        data = {
            "JobName": job_name,
            "JobDescription": job_description_name,
            "QualificationName": qualification_title,
            "Qualifications": qualifications}

        response = requests.post(full_url, json=data)
        response = response.json()
        show_questions(response)

elif request_type == "Applicant":

    form = st.form(key="applicant-form")

    skills = form.text_area(label="Skills")
    certifications = form.text_area(label="Certifications")
    cv_description = form.text_input(label="CV Description")

    apl_submit = form.form_submit_button(label="Submit")

    if apl_submit:
        endpoint = "/from_applicant"
        full_url = url + endpoint
        data = {
            "Skills": skills,
            "Certifications": certifications,
            "CVDescription": cv_description}

        response = requests.post(full_url, json=data)
        response = response.json()
        show_questions(response)

