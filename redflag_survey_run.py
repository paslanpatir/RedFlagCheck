# %%
HOME = "C:\\Users\\Pelin\\Documents\\RedFlagListStudy\\"

# %%
import os
os.chdir(HOME)

# %%
import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import numpy as np
import uuid  # To generate unique IDs

import re 


from plotnine import ggplot, aes, geom_point, labs, theme_minimal, theme
import matplotlib.pyplot as plt



# %%
file_path = "RedFlagQuestions_Scores.xlsx"

# %%
class Language:
    def __init__(self, language):
        self.language = language
        self.texts = {
            "EN": {
                "welcome_message"       : "Hello :blue[**{name}**]! :sunglasses:",
                "welcome_description"   : "It is so nice to see you here. This survey is designed to help you to see how :red[toxic] your boyfriend is :bomb:",
                "welcome_instruction"   : "Please feel free to answer all the questions so that we can analyze the results obtained from all girls and use them to better point the toxic guys.",
                "goodbye_message"       : "Thank you for completing the survey and providing feedback **{name}**! :confetti_ball:",
                "survey_complete_msg"   : "Thank you for completing the survey! Your boyfriend's toxic score is: **{toxic_score:.2f}**",
                "filter_fail_msg"       : "However, unfortunately he failed the filters. This should be a critical warning for you :( ! :boom:",
                "filter_pass_msg"       : "Nice. He satisfies all the filters :) :blossom:",
                "red_flag_fail_msg"     : "Your boyfriend seems to have a high level of toxicity. :skull:",
                "red_flag_pass_msg"     : "Your boyfriend is less toxic than many others. Good for him! :herb:" ,
                "name_input"            : "Name",
                "email_input"           : "Email",
                "bf_name_input"         : "Boyfriend's Name",
                "filter_header"         : "Filter Questions" ,
                'redflag_header'        : "Redflag Questions"
            },
            "TR": {
                "welcome_message"       : "Merhaba :blue[**{name}**]! :sunglasses:",
                "welcome_description"   : "Burada seni görmek çok güzel. Bu anket, erkek arkadaşının ne kadar :red[toksik] olduğunu görmene yardımcı olmak için tasarlandı :bomb:",
                "welcome_instruction"   : "Lütfen tüm soruları cevaplamaktan çekinme, böylece tüm kızlardan elde edilen sonuçları analiz edebilir ve toksik erkekleri daha iyi tespit edebiliriz.",
                "goodbye_message"       : "Anketi tamamladığın ve geri bildirim verdiğin için teşekkürler **{name}**! :confetti_ball:",
                "survey_complete_msg"   : "Anketi tamamladığınız için teşekkürler! Erkek arkadaşınızın toksiklik skoru: **{toxic_score:.2f}**",
                "filter_fail_msg"       : "Ama, ne yazık ki filtrelerde sınıfta kaldı. Bu senin için ciddi bir uyarı anlamına gelmeli :( ! :boom:",
                "filter_pass_msg"       : "Güzel.. Erkek arkadaşın tüm filtrelerden geçti :) :blossom:",
                "red_flag_fail_msg"     : "Erkek arkadaşının toksiklik seviyesi biraz fazla yüksek. :skull:",
                "red_flag_pass_msg"     : "Erkek arkadaşının toksiklik seviyesi diğer erkeklere göre daha düşük. Aferin ona! :herb:",
                "name_input"            : "İsim",
                "email_input"           : "Eposta",
                "bf_name_input"         : "Erkek Arkadaşının İsmi",
                "filter_header"         : "Filtre Sorular",
                'redflag_header'        : "Redflag Soruları"
            }
        }

    def get_text(self, key, **kwargs):
        return self.texts[self.language][key].format(**kwargs)

# %% [markdown]
# # functions

# %%
# Sayfanın en üstüne kaydırma için JavaScript kodu
def scroll_to_top():
    components.html(
        """
        <script>
            window.scrollTo(0, 0);
        </script>
        """
    )

# %%
def is_valid_email(email):
    """
    Validate the email format using a simple regex.
    """
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

# %%
def load_data(file_path):
    cat         = pd.read_excel(file_path, sheet_name="Categories")
    dt          = pd.read_excel(file_path, sheet_name="RedFlags")
    filters     = pd.read_excel(file_path, sheet_name="Filters")
    
    # Rastgele sıralama işlemi sadece bir kez yapılacak
    if "randomized_dt" not in st.session_state:
        st.session_state.randomized_dt = dt.sample(frac=1).reset_index(drop=True)
    if "randomized_filters" not in st.session_state:
        st.session_state.randomized_filters = filters.sample(frac=1).reset_index(drop=True)
    
    return cat, st.session_state.randomized_dt, st.session_state.randomized_filters

# %%
def toxic_score_sofar(file_name='user_responses.csv'):
    try:
        dt = pd.read_csv(file_name)
        if not dt.empty:
            return dt['Toxic Score'].mean()
        else:
            return 0  # Default value if the file is empty
    except FileNotFoundError:
        return 0  # Default value if the file does not exist

# %%
def ask_filter_questions(filters, language):
    """
    Ask the filter questions and collect integer responses.
    """
    selected_language = Language(language)
    st.subheader(selected_language.get_text("filter_header"), divider=True)
    #filters = filters.sample(frac = 1).reset_index(drop=True)
    responses = {}
    filter_violations = 0
    for index, row in filters.iterrows():
        question = row[f"Filter_Question_{language}"]  # Get the question in the selected language
        upper_limit = row["Upper_Limit"]  # Get the upper limit for the response

        scoring_type = row['Scoring']
        if scoring_type == "Limit":
            response = st.number_input(
            f"{question}", 
            min_value=0, 
            max_value=5, 
            key=f"filter_{index}"
            )
        elif scoring_type == "YES/NO":
            opt = ["Yes", "No"] if language == 'EN' else ["Evet", "Hayır"]
            response_txt = st.radio(f"{question}", options=opt, key=f"radio_{index}")
            response = 1 if response_txt == "Yes" or response_txt == "Evet" else 0  # Convert "Yes" to yes_no_default_score and "No" to 0

        responses[row[f"F{row['Filter_ID']}"]] = response
        if response > upper_limit:
            filter_violations += 1

    return responses,filter_violations

# %%
def generate_survey(data, language):

    #data = data.sample(frac = 1).reset_index(drop=True)

    answers = {}
    tot_score = 0
    abs_tot_score = 0
    applicable_questions = 0  # Track the number of applicable questions
    yes_no_default_score = 7

    applicability_text = "Bu soru sizin için geçerli mi?" if language == 'TR' else 'Is this question applicable to you?'
    not_applicable_text = "Geçerli Değil" if language == 'TR' else "Not Applicable"

    range_question_text = "Lütfen 0-10 arasında değerlendirin:" if language == 'TR' else "Please select a score (0-10):"
    boolean_question_text = "Lütfen seçin:" if language == 'TR' else "Please select:"
    boolean_options =  ["Evet", "Hayır"] if language == 'TR' else ["Yes", "No"]

    for index, row in data.iterrows():
        question = row[f'Question_{language}'].strip()  # Assuming 'Question' is the column header for questions
        st.markdown(f"**{index + 1}.** **{question}**")

        # Initialize session state for visibility
        if f"not_applicable_{index}" not in st.session_state:
            st.session_state[f"not_applicable_{index}"] = False  # Default to Applicable

        # Create two columns for the checkbox and scoring options
        col1, col2 = st.columns([3, 1])  # Adjust the column widths as needed

        with col2:
            # Add a checkbox to mark the question as "Not Applicable"
            not_applicable = st.checkbox(
                not_applicable_text,
                key=f"not_applicable_checkbox_{index}",
                value=st.session_state[f"not_applicable_{index}"]
            )

            # Update session state immediately if the checkbox state changes
            if not_applicable != st.session_state[f"not_applicable_{index}"]:
                st.session_state[f"not_applicable_{index}"] = not_applicable
                st.rerun()  # Rerun the app to reflect the updated state

        with col1:
            if not st.session_state[f"not_applicable_{index}"]:
                # If "Applicable" is selected, show the scoring options
                scoring_type = row['Scoring']
                if scoring_type == "Range(0-10)":
                    answer = st.slider(range_question_text, min_value=0, max_value=10, key=f"slider_{index}")
                elif scoring_type == "YES/NO":
                    answer = st.radio(boolean_question_text, options=boolean_options, key=f"radio_{index}")
                    answer = yes_no_default_score if (answer== "Yes" or answer=="Evet") else 0  # Convert "Yes" to yes_no_default_score and "No" to 0
                else:
                    st.error(f"Unknown scoring type: {scoring_type}")
                    answer = 0  # Default to 0 if scoring type is unknown

                # Store the answer
                answers[f"Q{row['ID']}"] = answer

                # Calculate the total score and absolute total score
                weight = row['Weight']
                tot_score += weight * answer
                abs_tot_score += weight * (yes_no_default_score if scoring_type == "YES/NO" else 10) * (1 if weight > 0 else -1)  # Maximum score for applicable questions
                applicable_questions += 1  # Increment the count of applicable questions
            else:
                # If "Not Applicable" is selected, hide the scoring options
                answers[f"Q{row['ID']}"] = np.nan

        st.divider()

    # Calculate the toxic score only for applicable questions
    if applicable_questions > 0:
        toxic_score = 1.0 * tot_score / abs_tot_score
    else:
        toxic_score = 0  # Default score if no questions are applicable

    return answers, toxic_score

# %%
# Function to save user info and answers to a CSV file
def save_user_data(user_id, name, email,bf_name,language, answers, toxic_score, filter_responses, filter_violations,file_name='user_responses.csv'):
    # Create a dictionary to store user data and answers
    user_data = {
        'User ID'           : user_id,
        'Name'              : name,
        'Email'             : email,
        'Boyfriend Name'    : bf_name,
        'Language'          : language,
        'Toxic Score'       : toxic_score,
        **answers,  # Unpack the answers dictionary
        **filter_responses,  # Unpack the filter responses dictionary
        'Filter Violations' : filter_violations  # Add filter violations
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
def welcome(name, language):
    selected_language = Language(language)
    st.markdown(selected_language.get_text("welcome_message", name=name))
    st.markdown(selected_language.get_text("welcome_description"))
    st.markdown(selected_language.get_text("welcome_instruction"))

    #if language == "EN":
    #    st.markdown(f"Hello :blue[**{name}**]! :sunglasses:")
    #    st.markdown(f"It is so nice to see you here. This survey is designed to help you to see how :red[toxic] your boyfriend is :bomb:")
    #    st.markdown("Please feel free to answer all the questions so that we can analyze the results obtained from all girls and use them to better point the toxic guys.")
    #
    #elif language == "TR":
    #    st.markdown(f"Merhaba {name}!")
    #    st.markdown(f"Burada seni görmek çok güzel. Bu anket, erkek arkadaşının ne kadar :red[toksik] olduğunu görmene yardımcı olmak için tasarlandı :bomb:")
    #    st.markdown("Lütfen tüm soruları cevaplamaktan çekinme, böylece tüm kızlardan elde edilen sonuçları analiz edebilir ve toksik erkekleri daha iyi tespit edebiliriz.")

def goodbye(name, language):
    selected_language = Language(language)
    st.success(selected_language.get_text("goodbye_message", name=name))
    

# %%
def result_report(language,filter_violations,toxic_score,avg_toxic):
    selected_language = Language(language)
    st.success(selected_language.get_text("survey_complete_msg", toxic_score=toxic_score))
    if filter_violations > 0:
        st.warning(selected_language.get_text("filter_fail_msg"))
    else:
        st.success(selected_language.get_text("filter_pass_msg"))

    if toxic_score < avg_toxic:
        st.success(selected_language.get_text("red_flag_pass_msg"))
    else:
        st.error(selected_language.get_text("red_flag_fail_msg"))


# %%
def toxic_graph(language, file_name='user_responses.csv'):
    try:
        dt = pd.read_csv(file_name)
        if not dt.empty:
            # Prepare the data
            temp = dt.tail(1000)
            temp['FLAG'] = '0'
            temp.loc[temp.index[-1], 'FLAG'] = '1'
            temp = temp.sort_values('Toxic Score').reset_index(drop=True).reset_index()
            if language == 'EN':
                st.markdown(f"Number of guys in database: {temp.shape[0]}")
                st.markdown(f"blue dot is your guy! :large_blue_circle:")
            elif language =='TR':
                st.markdown(f"Veritabanındaki erkeklerin sayısı: {temp.shape[0]}")
                st.markdown(f"Mavi nokta seninki! :large_blue_circle:")
            # Create the plot
            p = (
                ggplot(temp, aes(x="index", y="Toxic Score", color = 'FLAG', size = 'FLAG'))
                + geom_point()  # Scatter plot with color based on frequency
                + labs(title="", x= ("indeks (skora göre sıralı)" if language == 'TR' else "Index (Sorted by Score)") , y=("Toksiklik" if language == 'TR' else 'Toxicity'))
                       
                + theme_minimal()
                + theme(legend_position="none") 
            )
            #print(p)

            # Convert the plotnine plot to a matplotlib figure
            fig = p.draw()

            return fig
        else:
            return None  # Default value if the file is empty
    except FileNotFoundError:
        return None  # Default value if the file does not exist

# %%
def generate_feedback(language):
    if language == "EN":
        st.write("Please rate your experience:")
    elif language == "TR":
        st.write("Lütfen deneyiminizi değerlendirin:")

    # Use st.feedback to collect user feedback
    selected = st.feedback("stars")

    # Handle the case where no feedback is selected
    if selected is None:
        if language == "EN":
            st.warning("Please provide a rating.")
        elif language == "TR":
            st.warning("Lütfen bir değerlendirme yapın.")
        return None  # Return None if no feedback is selected

    # Map the selected feedback to a sentiment
    sentiment_mapping = ["one", "two", "three", "four", "five"]
    if language == "EN":
        st.markdown(f"You selected {sentiment_mapping[selected]} star(s).")
    elif language == "TR":
        st.markdown(f"{sentiment_mapping[selected]} yıldız seçtin.")

    return selected + 1  # Return the rating (1-5)

def save_feedback(user_id, name, email, bf_name,language, rating,file_name='user_feedback.csv'):
    user_data = {
        'User ID'           : user_id,
        'Name'              : name,
        'Email'             : email,
        'Boyfriend Name'    : bf_name,
        'Language'          : language,
        'Rating'            : rating
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
def ask_toxicity_opinion(language):
    if language == "EN":
        txt =  "So, how toxic is your boyfriend?"
        opt = ['not at all', 'a little bit', 'toxic but not more than others', 'yeah, a little more', 'he is literally a toxic guy']
    elif language == "TR":
        txt = "Peki, sence erkek arkadaşın ne kadar toksik?:"
        opt = ['hiç değil', 'eh, birazcık', 'toksik ama herkes kadar', 'evet, biraz fazla toksik', 'gerçekten de toksik birisi']

    selected = st.select_slider(txt,options=opt, label_visibility = 'hidden' )
    # Handle the case where no feedback is selected
    if selected is None:
        if language == "EN":
            st.warning("Please provide a rating.")
        elif language == "TR":
            st.warning("Lütfen bir değerlendirme yapın.")
        return None  # Return None if no feedback is selected
    
    # Map the selected option to an integer value (1 to 5)
    toxicity_rating = opt.index(selected) + 1  # +1 because index starts from 0

    if language == "EN":
        st.markdown(f"You selected **{selected}**. This corresponds to a toxicity rating of **{toxicity_rating}**.")
    elif language == "TR":
        st.markdown(f"**{selected}** seçtin. Bu, **{toxicity_rating}** toksisite derecesine karşılık geliyor.")

    return toxicity_rating  


def save_toxicity_input(user_id, name, email,bf_name,language, toxicity_rating,file_name='user_toxicity_rating.csv'):
    user_data = {
        'User ID'           : user_id,
        'Name'              : name,
        'Email'             : email,
        'Boyfriend Name'    : bf_name,
        'Language'          : language,
        'Toxicity Rating'   : toxicity_rating
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

# %% [markdown]
# # dashboard

# %%
#language = 'TR'
#cat,dt,filters = load_data(file_path)
#data = dt.copy()
#answers = {}
#tot_score = 0
#abs_tot_score = 0
#for index, row in data.iterrows():
#    question = row[f'Question_{language}'].strip()  # Assuming 'Question' is the column header for questions
#    print(question)

# %%
#if "user_details" not in st.session_state:
#    #st.session_state.user_details = {"name": None, "email": None, "language": None}
#    st.session_state.user_details = {"name": 'pelin_deneme', "email": 'pelin@deneme.com', "language": 'TR'}

# %%
def main():
    st.title("RedFlag - Toxic Guy Detector")

    # Initialize session state for user details and submission status
    if "user_details" not in st.session_state:
        st.session_state.user_details = {"name": None, "email": None, "language": None, 'bf_name': None}
    if "filter_responses" not in st.session_state:
        st.session_state.filter_responses = None
        st.session_state.filter_violations = 0
    if "submitted" not in st.session_state:
        st.session_state.submitted = False  # Track if the survey has been submitted
    if "toxic_score" not in st.session_state:
        st.session_state.toxic_score = None  # Store the toxic score in session state
    if "avg_toxic" not in st.session_state:
        st.session_state.avg_toxic = None  # Store the average toxic score in session state
    if "feedback_submitted" not in st.session_state:
        st.session_state.feedback_submitted = False  # Track if feedback has been submitted
    if "toxicity_rating_submitted" not in st.session_state:
        st.session_state.toxicity_rating_submitted = False  # Track if feedback has been submitted
    if "survey_completed" not in st.session_state:
        st.session_state.survey_completed = False  # Track if the survey is fully completed
    if "welcome_shown" not in st.session_state:
        st.session_state.welcome_shown = False  # Track if the survey is fully completed
    if "user_id" not in st.session_state:  # Initialize user_id in session state
        st.session_state.user_id = str(uuid.uuid4())  # Generate a unique ID for the user

    # Ask the user for their preferred language
    if not st.session_state.user_details["language"]:
        st.write("Please select your preferred language / Lütfen tercih ettiğiniz dili seçin:")
        language = st.radio("Language / Dil", options=["TR", "EN"], key="language_select")
        if st.button("Submit / Gönder"):
            st.session_state.user_details["language"] = language
            st.rerun()

    # Ask the user for their name and email using a form
    elif not st.session_state.user_details["name"]:
        language = st.session_state.user_details["language"]
        if language == "EN":
            st.write("Please enter your details:")
        elif language == "TR":
            st.write("Lütfen bilgilerinizi girin:")

        with st.form("user_details_form"):
            selected_language = Language(language)

            name = st.text_input(selected_language.get_text("name_input"), key="name_input")
            email = st.text_input(selected_language.get_text("email_input"), key="email_input")
            if st.form_submit_button("Submit / Gönder"):
                if name:  # Ensure name is provided
                    if email:  # E-posta adresi girildiyse doğrula
                        if is_valid_email(email):  # Validate email format
                            st.session_state.user_details["name"] = name
                            st.session_state.user_details["email"] = email
                            st.rerun()
                        else:
                            if language == "EN":
                                st.error("Please enter a valid email address (e.g., example@domain.com).")
                            elif language == "TR":
                                st.error("Lütfen geçerli bir e-posta adresi girin (örneğin, ornek@alanadi.com).")
                    else:  # E-posta adresi girilmediyse boş bırak
                        st.session_state.user_details["name"] = name
                        st.session_state.user_details["email"] = None  # E-posta adresi opsiyonel
                        st.rerun()
                else:
                    if language == "EN":
                        st.error("Please enter your name.")
                    elif language == "TR":
                        st.error("Lütfen adınızı girin.")

    # Ask the user for their boyfriend's name
    elif not st.session_state.user_details["bf_name"]:
        language = st.session_state.user_details["language"]
        if language == "EN":
            st.write("Please enter your boyfriend's name:")
        elif language == "TR":
            st.write("Lütfen erkek arkadaşınızın adını girin:")

        with st.form("bf_name_form"):
            bf_name = st.text_input("Boyfriend's Name / Erkek Arkadaşın Adı", key="bf_name_input")
            if st.form_submit_button("Submit / Gönder"):
                if bf_name:  # Ensure boyfriend's name is provided
                    st.session_state.user_details["bf_name"] = bf_name
                    st.rerun()
                else:
                    if language == "EN":
                        st.error("Please enter your boyfriend's name.")
                    elif language == "TR":
                        st.error("Lütfen erkek arkadaşınızın adını girin.")

    else:
        name = st.session_state.user_details["name"]
        email = st.session_state.user_details["email"]
        bf_name = st.session_state.user_details["bf_name"]
        language = st.session_state.user_details["language"]
        user_id = st.session_state.user_id  # Use the existing user_id from session state

        # Load the Excel file
        cat, dt, filters = load_data(file_path)

        if not st.session_state.welcome_shown:
            # Generate the survey
            welcome(name, language)
            st.session_state.welcome_shown = True

        if st.session_state.welcome_shown and st.session_state.filter_responses is None:
            filter_responses, filter_violations = ask_filter_questions(filters, language)
            if st.button("Submit Filter Responses / Filtre Cevaplarını Gönder"):
                st.session_state.filter_responses = filter_responses
                st.session_state.filter_violations = filter_violations
                st.rerun()  # Rerun the app to update the state
        else:
            if not st.session_state.submitted and not st.session_state.survey_completed:
                if language == "EN":
                    st.subheader("Please answer the following questions :tulip:", divider=True)
                elif language == "TR":
                    st.subheader("Lütfen aşağıdaki soruları cevaplayın :tulip:", divider=True)
                answers, toxic_score = generate_survey(dt, language)

                # Save the user data and answers
                if st.button('Submit / Gönder'):
                    if name:  # Ensure name is provided
                        avg_toxic = toxic_score_sofar(file_name='user_responses.csv')

                        if st.session_state.filter_responses is not None:
                            save_user_data(user_id, name, email, bf_name, language, answers, toxic_score, st.session_state.filter_responses, st.session_state.filter_violations)

                            # Store the toxic score and average toxic score in session state
                            st.session_state.toxic_score = toxic_score
                            st.session_state.avg_toxic = avg_toxic

                            # Mark the survey as submitted
                            st.session_state.submitted = True
                            st.rerun()  # Rerun the app to show the feedback component
                        else:
                            if language == "EN":
                                st.error("Please complete the filter questions before submitting.")
                            elif language == "TR":
                                st.error("Göndermeden önce lütfen filtre sorularını yanıtlayın.")
                    else:
                        if language == "EN":
                            st.error("Please enter your name before submitting.")
                        elif language == "TR":
                            st.error("Göndermeden önce lütfen adınızı girin.")

            # Show feedback only after submission
            if st.session_state.submitted and not st.session_state.feedback_submitted:
                # Collect feedback after submission
                if language == "EN":
                    st.subheader("Please feedback :gift_heart:", divider=True)
                elif language == "TR":
                    st.subheader("Lütfen feedback :gift_heart:", divider=True)
                rating = generate_feedback(language)
                if rating is not None:  # Only save feedback if a rating is provided
                    save_feedback(user_id, name, email, bf_name, language, rating)
                    st.session_state.feedback_submitted = True  # Mark feedback as submitted
                    st.rerun()  # Rerun the app to show the thank you message

            if st.session_state.feedback_submitted and not st.session_state.toxicity_rating_submitted:
                if language == "EN":
                    st.subheader("You think your boyfriend is .. :man_dancing:", divider=True)
                elif language == "TR":
                    st.subheader("Sence, erkek arkadaşın .. :man_dancing:", divider=True)

                toxicity_rating = ask_toxicity_opinion(language)
                if toxicity_rating is not None:
                    save_toxicity_input(user_id, name, email, bf_name, language, toxicity_rating, file_name='user_toxicity_rating.csv')

                    # Devam etmek için buton ekle
                    if st.button("Proceed to Results / Sonuçlara Geç"):
                        st.session_state.toxicity_rating_submitted = True
                        st.session_state.survey_completed = True
                        st.rerun()  # Sayfayı yeniden yükle

            if st.session_state.feedback_submitted and st.session_state.toxicity_rating_submitted:
                st.subheader("Result/Sonuç :dizzy:", divider=True)
                filter_violations = st.session_state.filter_violations
                toxic_score = st.session_state.toxic_score  # Retrieve the toxic score from session state
                avg_toxic = st.session_state.avg_toxic  # Retrieve the average toxic score from session state

                result_report(language, filter_violations, toxic_score, avg_toxic)
                fig = toxic_graph(language, file_name='user_responses.csv')
                # Display the plot in Streamlit
                if fig:
                    st.pyplot(fig)

            # Show thank you message after feedback is submitted
            if st.session_state.survey_completed:
                goodbye(name, language)

                # Optionally, add a button to restart the survey
                if st.button("Start New Survey / Yeni Anket Başlat"):
                    # Reset only the necessary states, but keep user_id and user_details
                    st.session_state.user_details["bf_name"] = None
                    st.session_state.filter_responses = None
                    st.session_state.filter_violations = 0
                    st.session_state.submitted = False
                    st.session_state.toxic_score = None
                    st.session_state.avg_toxic = None
                    st.session_state.feedback_submitted = False
                    st.session_state.toxicity_rating_submitted = False
                    st.session_state.survey_completed = False
                    st.session_state.welcome_shown = True

                    st.rerun()  # Rerun the app to start a new survey

# %%
# Run the application
if __name__ == "__main__":
    main()


