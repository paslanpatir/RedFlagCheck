# %%
HOME = "C:\\Users\\Pelin\\Documents\\RedFlagListStudy\\"

# %%
import os
os.chdir(HOME)

# %%
import streamlit as st

import pandas as pd
import numpy as np
import uuid  # To generate unique IDs


# %% [markdown]
# # data

# %%
def load_data(file_path):
    cat = pd.read_excel(file_path, sheet_name="Categories")
    dt = pd.read_excel(file_path, sheet_name="RedFlags")
    return cat,dt

# %%
def toxic_score_sofar(file_name='user_responses.csv'):
    dt = pd.read_csv(file_name)
    return dt['Toxic Score'].mean()

# %%
def generate_survey(data):
    answers = {}
    tot_score = 0
    abs_tot_score = 0
    for index, row in data.iterrows():
        question = row['Question'].strip()  # Assuming 'Question' is the column header for questions
        st.markdown(f"**{index + 1}.** **{question}**")
        answer = st.slider(f"Please select a score:", min_value=0, max_value=10, key=index)
        answers[f"Q{index + 1}"] = answer
        st.divider()
        ## scoring
        weight = row['Weight']
        tot_score       = tot_score + weight*answer
        abs_tot_score   = abs_tot_score + weight*np.where(weight<0, 0,10) # negatif weigtli bir şeyde toksik olmak 0 puan almak demektir.

    toxic_score = 1.0*tot_score/abs_tot_score
    return answers,toxic_score

# %%
def save_answers(answers, file_name='survey_answers.csv'):
    df = pd.DataFrame(list(answers.items()), columns=['Question', 'Answer'])
    df.to_csv(file_name, index=False)

# %%
# Function to save user info and answers to a CSV file
def save_user_data(user_id, name, email, answers,toxic_score, file_name='user_responses.csv'):
    # Create a dictionary to store user data and answers
    user_data = {
        'User ID': user_id,
        'Name': name,
        'Email': email,
        'Toxic Score': toxic_score,
        **answers  # Unpack the answers dictionary
    }
    
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame([user_data])
    
    # Append the data to the CSV file (or create a new file if it doesn't exist)
    try:
        existing_data = pd.read_csv(file_name)
        updated_data = pd.concat([existing_data, df], ignore_index=True)
    except FileNotFoundError:
        updated_data = df
    
    # Save the updated data to the CSV file
    updated_data.to_csv(file_name, index=False)

# %%
def welcome(name):
    st.markdown(f"Hello :blue[**{name}**]! :sunglasses:")
    st.markdown(f"It is so nice to see you here. This survey is designed to help you to see how :red[toxic] your boyfriend is :bomb:")
    st.markdown("Please feel free to answer all the questions so that we can analyze the results obtained from all girls and use them to better point the toxic guys.")
    

# %% [markdown]
# # dashboard

# %%
def main():
    st.title("RedFlag List")

    # Initialize session state for user details
    if "user_details" not in st.session_state:
        st.session_state.user_details = {"name": None, "email": None}

    # Ask the user for their name and email using a form
    if not st.session_state.user_details["name"] or not st.session_state.user_details["email"]:
        st.write("Please enter your details:")
        with st.form("user_details_form"):
            name = st.text_input("Name", key="name_input")
            email = st.text_input("Email", key="email_input")
            if st.form_submit_button("Submit"):
                if name and email:  # Ensure name and email are provided
                    st.session_state.user_details = {"name": name, "email": email}
                    st.rerun()
                else:
                    st.error("Please enter both your name and email.")
            
    else:
        name = st.session_state.user_details["name"]
        email= st.session_state.user_details["email"]
        # Generate a unique ID for the user
        user_id = str(uuid.uuid4())  # Creates a unique identifier

    
        # Load the Excel file
        file_path = "RedFlagQuestions_Scores.xlsx"
        cat,dt = load_data(file_path)

        # Generate the survey
        welcome(name)

        st.subheader("Please answer the following questions :tulip:", divider=True)
        answers, toxic_score = generate_survey(dt)

        # Save the user data and answers
        if st.button('Submit'):
            if name and email:  # Ensure name and email are provided
                save_user_data(user_id, name, email, answers,toxic_score)
                st.success(f"Thank you for completing the survey! Your boyfriend's toxic score is: **{toxic_score}**")

                # Optional: Add additional feedback based on the toxic score
                avg_toxic = toxic_score_sofar(file_name='user_responses.csv')
                if toxic_score < avg_toxic:
                    st.warning("Your boyfriend seems to be better than the half of the guys. Good for him!")
                else:
                    st.error("Your score indicates a high level of toxicity. Please take action to address this.")
            else:
                st.error("Please enter your name and email before submitting.")

# %%
# Run the application
if __name__ == "__main__":
    main()


