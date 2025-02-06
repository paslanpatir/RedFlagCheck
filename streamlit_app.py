# %%
import streamlit as st
import pandas as pd
import numpy as np
import uuid
import re
from collections import defaultdict

# %% [markdown]
# # Functions

# %%
def is_valid_email(email):
    """
    Validate the email format using a simple regex.
    """
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

def load_data(file_path):
    """
    Load data from the Excel file.
    """
    cat = pd.read_excel(file_path, sheet_name="Categories")
    dt = pd.read_excel(file_path, sheet_name="RedFlags")
    filters = pd.read_excel(file_path, sheet_name="Filters")
    return cat, dt, filters

def toxic_score_sofar(file_name='user_responses.csv'):
    """
    Calculate the average toxic score from the saved responses.
    """
    try:
        dt = pd.read_csv(file_name)
        if not dt.empty:
            return dt['Toxic Score'].mean()
        else:
            return 0  # Default value if the file is empty
    except FileNotFoundError:
        return 0  # Default value if the file does not exist

def select_random_questions(data, K):
    """
    Select K random questions, ensuring proportional representation from each category.
    """
    # Group questions by category
    category_questions = defaultdict(list)
    for _, row in data.iterrows():
        category_questions[row['Category_ID']].append(row)

    # Calculate the number of questions to select from each category
    total_questions = len(data)
    selected_questions = []
    for category_id, questions in category_questions.items():
        category_n = int(np.round((len(questions) / total_questions) * K))
        if category_n > len(questions):
            category_n = len(questions)  # Ensure we don't select more questions than available
        
        # Randomly select questions from the current category
        selected_indices = np.random.choice(len(questions), size=category_n, replace=False)
        selected_questions.extend([questions[i] for i in selected_indices])

    # If the total number of selected questions is less than K, add more questions randomly
    if len(selected_questions) < K:
        remaining_questions = [q for q in data.to_dict('records') if q not in selected_questions]
        selected_questions.extend(np.random.choice(remaining_questions, size=K - len(selected_questions), replace=False))

    return selected_questions

def select_random_filters(filters, M):
    """
    Select M random filter questions.
    """
    if M > len(filters):
        M = len(filters)  # Ensure we don't select more filters than available
    return filters.sample(n=M).to_dict('records')

def ask_filter_questions(filters, language):
    """
    Ask the filter questions and collect integer responses.
    """
    st.subheader("Additional Questions / Ek Sorular", divider=True)
    responses = {}
    filter_violations = 0
    for index, row in enumerate(filters):
        question = row[f"Filter_Question_{language}"]  # Get the question in the selected language
        upper_limit = row["Upper_Limit"]  # Get the upper limit for the response
        response = st.number_input(
            f"{question}", 
            min_value=0, 
            max_value=5, 
            key=f"filter_{index}"
        )
        responses[f"filter_{row['Filter_ID']}"] =  response

        if response > upper_limit:
            filter_violations += 1

    return responses, filter_violations

def generate_survey(selected_questions, language):
    """
    Generate the survey questions based on the selected questions.
    """
    answers = {}
    tot_score = 0
    abs_tot_score = 0
    for index, row in enumerate(selected_questions):
        question = row[f'Question_{language}'].strip()  # Get the question in the selected language
        st.markdown(f"**{index + 1}.** **{question}**")
        answer = st.slider(f"Please select a score:", min_value=0, max_value=10, key=f"slider_{index}")
        answers[f"Q{row['ID']}"] = answer 
        st.divider()
        ## Scoring
        weight = row['Weight']
        tot_score = tot_score + weight * answer
        abs_tot_score = abs_tot_score + weight * np.where(weight < 0, 0, 10)  # Negative weights are treated as 0 for max score.

    toxic_score = 1.0 * tot_score / abs_tot_score
    return answers, toxic_score

def save_user_data(user_id, name, email, language, answers, toxic_score, filter_responses, filter_violations, file_name='user_responses.csv'):
    """
    Save user data, survey answers, and filter responses to a CSV file.
    Ensure all possible questions and filters are included as columns.
    """
    # Load all questions and filters to get the full list of columns
    file_path = 'https://github.com/paslanpatir/RedFlagCheck/blob/main/RedFlagQuestions_Scores.xlsx' #"RedFlagQuestions_Scores.xlsx"
    _, dt, filters = load_data(file_path)

    # Create a dictionary with all possible columns initialized to NaN
    user_data = {
        'User ID': user_id,
        'Name': name,
        'Email': email,
        'Language': language,
        'Toxic Score': toxic_score,
        'Filter Violations': filter_violations,
    }

    # Add all possible question columns (Q1, Q2, etc.)
    for q_id in dt['ID']:
        user_data[f"Q{q_id}"] = np.nan  # Initialize to NaN

    # Add all possible filter columns (filter_1, filter_2, etc.)
    for f_id in filters['Filter_ID']:
        user_data[f"filter_{f_id}"] = np.nan  # Initialize to NaN

    # Update the dictionary with the user's answers and filter responses
    user_data.update(answers)  # Add the user's answers
    user_data.update(filter_responses)  # Add the user's filter responses

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

def welcome(name, language):
    """
    Display a welcome message based on the selected language.
    """
    if language == "EN":
        st.markdown(f"Hello :blue[**{name}**]! :sunglasses:")
        st.markdown(f"It is so nice to see you here. This survey is designed to help you to see how :red[toxic] your boyfriend is :bomb:")
        st.markdown("Please feel free to answer all the questions so that we can analyze the results obtained from all girls and use them to better point the toxic guys.")
    elif language == "TR":
        st.markdown(f"Merhaba {name}!")
        st.markdown(f"Burada seni görmek çok güzel. Bu anket, erkek arkadaşının ne kadar :red[toksik] olduğunu görmene yardımcı olmak için tasarlandı :bomb:")
        st.markdown("Lütfen tüm soruları cevaplamaktan çekinme, böylece tüm kızlardan elde edilen sonuçları analiz edebilir ve toksik erkekleri daha iyi tespit edebiliriz.")


# %% [markdown]
# # Dashboard

# %%
def main():
    st.title("RedFlag List")
            # Load the Excel file

    

    # Initialize session state for user details
    if "user_details" not in st.session_state:
        #st.session_state.user_details = {"name": None, "email": None, "language": None}
        st.session_state.user_details = {"name": 'pelin_deneme', "email": 'pelin@deneme.com', "language": 'TR'}
    if "filter_responses" not in st.session_state:
        st.session_state.filter_responses = None
        st.session_state.filter_violations = 0  # Initialize filter violations
    if "selected_questions" not in st.session_state:
        st.session_state.selected_questions = None  # Store selected questions
    if "selected_filters" not in st.session_state:
        st.session_state.selected_filters = None  # Store selected filters

    # Ask the user for their preferred language
    if not st.session_state.user_details["language"]:
        st.write("Please select your preferred language / Lütfen tercih ettiğiniz dili seçin:")
        language = st.selectbox("Language / Dil", options=["EN", "TR"], key="language_select")
        if st.button("Submit / Gönder"):
            st.session_state.user_details["language"] = language
            st.rerun()
    # Ask the user for their name and email using a form
    elif not st.session_state.user_details["name"] or not st.session_state.user_details["email"]:
        language = st.session_state.user_details["language"]
        if language == "EN":
            st.write("Please enter your details:")
        elif language == "TR":
            st.write("Lütfen bilgilerinizi girin:")

        with st.form("user_details_form"):
            name = st.text_input("Name / İsim", key="name_input")
            email = st.text_input("Email / E-posta", key="email_input")
            if st.form_submit_button("Submit / Gönder"):
                if name and email:  # Ensure name and email are provided
                    if is_valid_email(email):  # Validate email format
                        st.session_state.user_details = {"name": name, "email": email, "language": language}
                        st.rerun()
                    else:
                        if language == "EN":
                            st.error("Please enter a valid email address (e.g., example@domain.com).")
                        elif language == "TR":
                            st.error("Lütfen geçerli bir e-posta adresi girin (örneğin, ornek@alanadi.com).")
                else:
                    if language == "EN":
                        st.error("Please enter both your name and email.")
                    elif language == "TR":
                        st.error("Lütfen hem adınızı hem de e-posta adresinizi girin.")
    else:
        name = st.session_state.user_details["name"]
        email = st.session_state.user_details["email"]
        language = st.session_state.user_details["language"]
        # Generate a unique ID for the user
        user_id = str(uuid.uuid4())  # Creates a unique identifier

        file_path = "RedFlagQuestions_Scores.xlsx"
        cat, dt, filters = load_data(file_path)

        if st.session_state.selected_questions is None or st.session_state.selected_filters is None:
            K = 10  # Total number of questions to ask
            M = 3  # Total number of filter questions to ask
            st.session_state.selected_questions = select_random_questions(dt, K)
            st.session_state.selected_filters = select_random_filters(filters, M)


        # Generate the survey
        welcome(name, language)

        if st.session_state.filter_responses is None:
            st.write("Please answer the following filter questions:")
            filter_responses, filter_violations = ask_filter_questions(st.session_state.selected_filters, language)
            if st.button("Submit Filter Responses / Filtre Cevaplarını Gönder"):
                st.session_state.filter_responses = filter_responses
                st.session_state.filter_violations = filter_violations
        else:
            if language == "EN":
                st.subheader("Please answer the following questions :tulip:", divider=True)
            elif language == "TR":
                st.subheader("Lütfen aşağıdaki soruları cevaplayın :tulip:", divider=True)
                
            answers, toxic_score = generate_survey(st.session_state.selected_questions, language)

            # Save the user data and answers
            if st.button('Submit / Gönder'):
                if name and email:  # Ensure name and email are provided
                    avg_toxic = toxic_score_sofar(file_name='user_responses.csv')
                    save_user_data(user_id, name, email, language, answers, toxic_score, st.session_state.filter_responses, st.session_state.filter_violations)

                    if language == "EN":
                        st.success(f"Thank you for completing the survey! Your boyfriend's toxic score is: **{toxic_score:.2f}**")
                        if st.session_state.filter_violations > 0:
                            st.warning("However, unfortunately he failed the filters. This should be a critical warning for you :( !")
                        else:
                            if toxic_score < avg_toxic:
                                st.warning("Your boyfriend seems to have lower toxicity compared to many guys. Good for him!")
                            else:
                                st.error("Your score indicates a high level of toxicity. Please take action to address this.")
                    elif language == "TR":
                        st.success(f"Anketi tamamladığınız için teşekkürler! Erkek arkadaşınızın toksiklik puanı: **{toxic_score:.2f}**")
                        if st.session_state.filter_violations > 0:
                            st.warning("Ama, ne yazık ki filtrelerde sınıfta kaldı. Bu senin için ciddi bir uyarı anlamına gelmeli :( !")
                        else:
                            if toxic_score < avg_toxic:
                                st.warning("Erkek arkadaşınız ortalamaya göre daha düşük toksiklik seviyesinde. Bu onun için iyi!")
                            else:
                                st.error("Skorunuz yüksek bir toksiklik seviyesini gösteriyor. Lütfen bu konuda harekete geçin.")
                else:
                    if language == "EN":
                        st.error("Please enter your name and email before submitting.")
                    elif language == "TR":
                        st.error("Göndermeden önce lütfen adınızı ve e-posta adresinizi girin.")

# Run the application
if __name__ == "__main__":
    main()


