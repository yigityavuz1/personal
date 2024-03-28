import streamlit as st


def show_questions(response):
    st.subheader("Exam Questions")
    for question in response["Content"]:
        if question["Type"] == "Multiple Choice":
            text = question["Text"] + "\n"
            for i, option in enumerate(question["Options"]):
                text += f"{i + 1}. {option}\n"
            text = text.replace("\n", "  \n")
        else:
            text = question["Text"].replace("\n", "  \n")
        st.write(question["Number"] + " - " + question["Subject"] + " - " + question["Type"] + " - " + question[
            "Difficulty"] + " - " + question["Duration"])
        st.write(text)
        st.divider()

    st.subheader("Answers")
    for question in response["Content"]:
        if question["Type"] == "Multiple Choice":
            text = question["Answer"] + " - " + ", ".join(question["Options"])
            text.replace("\n", "  \n")
        else:
            text = question["Answer"].replace("\n", "  \n")
        st.write("Question: " + question["Number"])
        st.write(text)
        st.divider()