import os
import re 
import uuid  # To generate unique IDs
import ast

import boto3
import streamlit as st

import pandas as pd
import numpy as np

import math
from decimal import Decimal,ROUND_HALF_UP, getcontext
from datetime import datetime

from plotnine import ggplot, aes, geom_point, labs, theme_minimal, theme
import matplotlib.pyplot as plt

# Import the Message class
from message_class import Message
getcontext().prec = 5



def safe_decimal(value):
    """Convert numeric values to Decimal, replacing Infinity/NaN with None"""
    if isinstance(value, (int, float)):
        if math.isinf(value) or math.isnan(value):
            return None
        return Decimal(str(value))
    return value

def natural_sort_key(item):
    key = item[0]  # the dictionary key (e.g., "Q1")
    # Extract the number part and convert to integer for proper numerical sorting
    return int(key[1:]) if key[1:].isdigit() else 0

def is_valid_email(email):
    """
    Validate the email format using a simple regex.
    """
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None


def ask_language():
    st.write("Please select your preferred language / Lütfen tercih ettiğiniz dili seçin:")
    language = st.radio("Language / Dil", options=["TR", "EN"], key="language_select")
    msg = Message(language)
    if st.button(msg.get_text("continue_msg")):
        st.session_state.user_details["language"] = language
        st.rerun()

def ask_user_details():
    language = st.session_state.user_details["language"]
    msg = Message(language)
    st.write(msg.get_text("enter_details_msg"))
    
    with st.form("user_details_form"):
        name    = st.text_input(msg.get_text("name_input"), key="name_input")
        email   = st.text_input(msg.get_text("email_input"), key="email_input")
        if st.form_submit_button(msg.get_text("continue_msg")):
            if name:
                if email and is_valid_email(email):
                    st.session_state.user_details["name"] = name
                    st.session_state.user_details["email"] = email
                    st.rerun()
                else:
                    st.error(msg.get_text("enter_valid_email_msg"))
            else:
                st.error(msg.get_text("enter_name_msg"))

def ask_bf_name():
    language = st.session_state.user_details["language"]
    msg = Message(language)
    st.write(msg.get_text("enter_bf_name_msg"))

    with st.form("bf_name_form"):
        bf_name = st.text_input(msg.get_text("bf_name_input"), key="bf_name_input")
        if st.form_submit_button(msg.get_text("continue_msg")):
            if bf_name:
                st.session_state.user_details["bf_name"] = bf_name
                st.rerun()
            else:
                st.error(msg.get_text("enter_bf_name_msg"))

def transform_db_to_df(table_name,TABLES_AND_COLUMNS):
    table = dynamodb.Table(table_name)

    # Perform the initial scan
    response = table.scan()
    items = response['Items']  # Extract the items from the response

    # Handle pagination if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response['Items'])  # Add the next batch of items

    # Convert the list of items to a Pandas DataFrame
    df = pd.DataFrame(items, columns=TABLES_AND_COLUMNS[table_name]).sort_values(TABLES_AND_COLUMNS[table_name][0]).reset_index(drop =True)

    return df

def randomize_questions(data):
    data= data.sample(frac=1).reset_index(drop=True)
    print(f"data is randomized")
    return data


def load_data(DB_READ, table_name):
    correspondence_dict = { # dynamo db table names to excel names
        'RedFlagCategories' :"RedFlagQuestions_Source",
        'RedFlagQuestions'  :"RedFlagQuestions_Source",
        'RedFlagFilters'    :"RedFlagQuestions_Source",
        'GetToKnowQuestions':"RedFlagQuestions_Source",
        'Summary_Sessions'  :"Summary_Sessions",
        'session_responses' :"session_responses"
    }

    if DB_READ:
        data  =  transform_db_to_df(table_name,TABLES_AND_COLUMNS)
    else:
        file_path = os.path.join(correspondence_dict[table_name] + '.xlsx')
        print(file_path)
        data  = pd.read_excel(file_path, sheet_name=table_name)

    print(f"{table_name} is read")
    return data

def welcome(name, language):
    msg = Message(language)
    st.markdown(msg.get_text("welcome_message", name=name))
    st.markdown(msg.get_text("welcome_description"))
    st.markdown(msg.get_text("welcome_instruction"))
    


def select_discrete_score_options(language):
    msg= Message(language)
    opts        = msg.get_text("limited_opt_answer")
    yes_no_opts = msg.get_text("boolean_answer")
        
    return opts,yes_no_opts

def get_filter_questions():
    if "randomized_filters" not in st.session_state:
        data = load_data(DB_READ, 'RedFlagFilters')
        data = randomize_questions(data)
        st.session_state.randomized_filters = data
    
    return st.session_state.randomized_filters


def ask_filter_questions(data, language):
    """
    Ask the filter questions and collect responses.
    """
    msg = Message(language)
    st.subheader(msg.get_text("filter_header"), divider=True)
    
    responses = {}
    filter_violations = 0
    
    for index, row in data.iterrows():
        question        = row[f"Filter_Question_{language}"]  # Get the question in the selected language
        upper_limit     = row["Upper_Limit"]  # Get the upper limit for the response
        scoring_type    = row['Scoring']

        opts,yes_no_opts = select_discrete_score_options(language)

        #print(f"filter Q: {row['Filter_ID']}, quetion: {question}")
        print(f"{scoring_type=}")
        print(f"{upper_limit=}")

        
        if scoring_type == "Limit":
            # Map the selected option to a score
            option_to_score = {opt: idx for idx, opt in enumerate(opts)}
            respons_txt     = st.select_slider(f"{question}", options=opts, key=f"filter_{index}")
            response        = option_to_score[respons_txt]
        
        elif scoring_type == "YES/NO":
            response_txt    = st.radio(f"{question}", options=yes_no_opts, key=f"radio_{index}")
            response        = 1 if response_txt == yes_no_opts[0] else 0  # Convert "Yes" or "Evet" to 1, else 0


        # Store the response and check for violations
        responses[f"F{row['Filter_ID']}"] = response
        #print(f"{responses=}")
        if response >= upper_limit:
            filter_violations += 1

        st.divider()

    responses = dict(sorted(responses.items(), key=natural_sort_key))
    print(f"{filter_violations=}")
    return responses,filter_violations

def get_redflag_questions():
    if "randomized_questions" not in st.session_state:
        data = load_data(DB_READ, 'RedFlagQuestions')
        data = randomize_questions(data)
        st.session_state.randomized_questions = data
    
    return st.session_state.randomized_questions



def ask_redflag_questions(data, language):
    """Generate the main survey questions."""
    msg = Message(language)

    answers = {}
    tot_score = 0
    abs_tot_score = 0
    applicable_questions = 0  # Track the number of applicable questions
    yes_no_default_score = 7

    #applicability_text      = msg.get_text("applicability_check")
    not_applicable_msg      = msg.get_text("not_applicable_msg")
    select_score_msg        = msg.get_text("select_score_msg")
    select_option_msg       = msg.get_text("select_option_msg")
    boolean_answer          = msg.get_text("boolean_answer")

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
                not_applicable_msg,
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
                    answer = st.slider(select_score_msg, min_value=0, max_value=10, key=f"slider_{index}")
                elif scoring_type == "YES/NO":
                    answer = st.radio(select_option_msg, options=boolean_answer, key=f"radio_{index}")
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
        toxic_score = Decimal('1.0') * tot_score / abs_tot_score
    else:
        toxic_score = 0  # Default score if no questions are applicable

    answers = dict(sorted(answers.items(), key=natural_sort_key))
    print(f"{toxic_score=}")
    return answers, toxic_score

def parse_levels(levels_str):
    """
    Parse the Levels column string into a list of levels.
    Example: "[level1, level2, level3]" -> ["level1", "level2", "level3"]
    """
    if pd.isna(levels_str) or levels_str.strip() == "":
        return None  # No levels provided
    try:
        # Safely evaluate the string as a Python list
        return ast.literal_eval(levels_str)
    except (ValueError, SyntaxError):
        st.error(f"Invalid Levels format: {levels_str}")
        return None
    
def get_gtk_questions():
    if "gtk_questions" not in st.session_state:
        st.session_state.gtk_questions = load_data(DB_READ, 'GetToKnowQuestions')
    return st.session_state.gtk_questions

def ask_gtk_questions(gtk_questions, language):
    """
    Ask the GetToKnow questions and collect responses.
    """
    selected_language = Message(language)
    responses = {}

    for index, row in gtk_questions.iterrows():
        question = row[f"Question_{language}"]  # Get the question in the selected language
        scoring_type = row["Scoring"]  # Get the scoring type (e.g., Range, YES/NO)
        levels = parse_levels(row[f"Levels_{language}"])  # Parse the Levels column

        if scoring_type.startswith("Range"):
            if levels:
                # Use levels as options for the slider
                options = levels
                response = st.select_slider(question, options=options, key=f"gtk_{row['GTK_ID']}")
            else:
                # Extract range from the scoring type (e.g., "Range(18-101)" -> min=18, max=101)
                range_values = scoring_type.replace("Range(", "").replace(")", "").split("-")
                min_value = int(range_values[0])
                max_value = int(range_values[1])
                options = list(range(min_value, max_value + 1))
                response = st.select_slider(question, options=options, key=f"gtk_{row['GTK_ID']}")
        elif scoring_type == "YES/NO":
            options = selected_language.get_text("boolean_answer")
            response = st.radio(question, options=options, key=f"gtk_{row['GTK_ID']}")
        else:
            st.error(f"Unsupported scoring type: {scoring_type}")
            continue

        response_int = options.index(response) + 1
        responses[f"GTK{row["GTK_ID"]}"] = response_int

        st.divider()

    return responses

def generate_feedback(language):
    msg = Message(language)
    st.write(msg.get_text("feedback_msg"))

    sentiment_mapping = msg.get_text("sentiment_mapping")
    selected = st.feedback("stars")     
    if selected is None:
        st.warning(msg.get_text("please_rate_msg"))
        return None
    
    # Convert feedback to 1-based index (if needed)
    selected = selected + 1  # Now safe because we checked for None
    
    st.markdown(msg.get_text("feedback_result_msg", star=sentiment_mapping[selected-1]))
    return selected


def ask_toxicity_opinion(language):
    msg = Message(language)
    st.subheader(msg.get_text("toxicity_self_rating"), divider=True)
    
    opt = msg.get_text("toxicity_answer")
    selected = st.select_slider(msg.get_text("select_toxicity_msg"),
                                options=opt, 
                                label_visibility = 'hidden',
                                 value = opt[2] )
       
    # Map the selected option to an integer value (1 to 5)
    toxicity_rating = opt.index(selected) + 1  # +1 because index starts from 0
    st.markdown(msg.get_text("rating_result_msg", selected = selected ))
    st.markdown(msg.get_text("toxicity_result_msg", toxicity_rating = toxicity_rating ))

    return toxicity_rating 


def toxic_graph(curr_toxic_score,data,language):
    try:# later ensure that the guy scored is in the tail, and ensure the names are the same 
        # Prepare the data
        temp = data[['id','toxic_score']].tail(20)
        if temp.empty:
            return None
        
        temp.loc[-1] = [0,curr_toxic_score]
        boyfriend_name = st.session_state.user_details['bf_name']

        temp.loc[:,'FLAG'] = np.where(temp['id'] == 0, 1,0)
        temp.loc[:,'guys'] = 'others'
        temp.loc[temp['FLAG']== 1, 'guys'] = boyfriend_name
        temp = temp.sort_values('toxic_score').reset_index(drop=True).reset_index()
        temp['toxic_score'] = temp['toxic_score'].apply(lambda x: x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        guy_cnt = temp.shape[0]

        msg = Message(language)
        st.markdown(msg.get_text("toxic_graph_guy_cnt", guy_cnt= guy_cnt))
        #st.markdown(msg.get_text("toxic_graph_msg"))

        # Create the plot
        p = (
            ggplot(temp, aes(x="index", y="toxic_score", color = 'guys'))
            + geom_point()  # Scatter plot with color based on frequency
            + labs(title="", 
                   x= msg.get_text("toxic_graph_x") , 
                   y= msg.get_text("toxic_graph_y")) 
            + theme_minimal()
            #+ theme(legend_position="none") 
        )
        #print(p)
        # Convert the plotnine plot to a matplotlib figure
        fig = p.draw()
        return fig
    
    except FileNotFoundError:
        return None  # Default value if the file does not exist
    

def present_result_report():
    language = st.session_state.user_details["language"]
    msg = Message(language)

    avg_toxic_score         = st.session_state.avg_toxic_score
    toxic_score             = st.session_state.toxic_score
    avg_filter_violations   = st.session_state.avg_filter_violations
    filter_violations       = st.session_state.filter_violations
    bf_name                 = st.session_state.user_details["bf_name"]

    #st.success(msg.get_text("survey_complete_msg", toxic_score=toxic_score))
    if toxic_score: 
        st.info(msg.get_text("toxic_score_info", toxic_score= round(100*toxic_score,1)), icon=":material/bolt:")
        #st.markdown(toxic_score)
        #st.markdown(avg_toxic_score)
        if round(toxic_score,5) > round(avg_toxic_score,5):
            st.error(msg.get_text("red_flag_fail_msg", bf_name= bf_name))
        else:
            st.success(msg.get_text("red_flag_pass_msg", bf_name= bf_name))
    else:
            st.success(msg.get_text("red_flag_pass_msg", bf_name= bf_name))

    st.divider()

    if filter_violations:
        #st.info(msg.get_text("filter_viol_info", avg_filter_violations= avg_filter_violations, icon=":material/filter_alt:"))
        if filter_violations > 0:
            st.error(msg.get_text("filter_fail_msg", bf_name= bf_name, filter_violations = filter_violations))
    else:
            st.success(msg.get_text("filter_pass_msg", bf_name= bf_name))
    
        
    st.divider()

    session_responses = load_data(DB_READ, 'session_responses')
    fig = toxic_graph(toxic_score,session_responses,language)
    # Display the plot in Streamlit
    if fig:
        st.pyplot(fig)


def goodbye(name, language):
    msg = Message(language)
    st.success(msg.get_text("goodbye_message", name=name))


def get_output_summary(DB_READ):
    output_summary = load_data(DB_READ, "Summary_Sessions")

    st.session_state.sum_toxic_score                  = Decimal(output_summary['sum_toxic_score'].values[0])
    st.session_state.max_toxic_score                  = Decimal(output_summary['max_toxic_score'].values[0])
    st.session_state.min_toxic_score                  = Decimal(output_summary['min_toxic_score'].values[0])
    st.session_state.avg_toxic_score                  = Decimal(output_summary['avg_toxic_score'].values[0])
    
    st.session_state.sum_filter_violations             = output_summary['sum_filter_violations'].values[0]
    st.session_state.avg_filter_violations             = output_summary['avg_filter_violations'].values[0]

    st.session_state.count_guys                       = output_summary['count_guys'].values[0]
    st.session_state.max_id_session_responses         = output_summary['max_id_session_responses'].values[0]
    st.session_state.max_id_gtk_responses             = output_summary['max_id_gtk_responses'].values[0]
    st.session_state.max_id_feedback                  = output_summary['max_id_feedback'].values[0]
    st.session_state.max_id_session_toxicity_rating   = output_summary['max_id_session_toxicity_rating'].values[0]
            
def add_data(DB_WRITE, table_name, newdata_dict):
    print("add new data")
    write_succes = False
    if DB_WRITE:
        try:
            table = dynamodb.Table(table_name)
            table.put_item(Item=newdata_dict)
            print(f"Data written to DynamoDB : {table_name}")
            write_succes =True
        except Exception as e:
            print(f"Error writing to DynamoDB: {e}")
    else:
        file_path = os.path.join(table_name + '.xlsx')
        print(file_path)
        temp = pd.DataFrame([newdata_dict])
        try:
            existing_data = pd.read_excel(file_path)
            updated_data = pd.concat([existing_data, temp], ignore_index=True)
            write_succes =True
        except FileNotFoundError:
            updated_data = temp

        updated_data.to_excel(file_path,sheet_name=table_name, index=False)
        print(f"Data saved to excel file: {file_path}")
    
    return write_succes


def save_session_response(DB_WRITE):
    print("save response data")
    table_name  = "session_responses"
    user_id     = st.session_state.user_details["user_id"]
    name        = st.session_state.user_details["name"]
    email       = st.session_state.user_details["email"]
    language    = st.session_state.user_details["language"]
    bf_name     = st.session_state.user_details["bf_name"]

    redflag_responses   = st.session_state.redflag_responses
    toxic_score         = st.session_state.toxic_score
    filter_responses    = st.session_state.filter_responses
    filter_violations   = st.session_state.filter_violations
    session_start_time  = st.session_state.session_start_time
    result_start_time   = st.session_state.result_start_time
    session_end_time    = st.session_state.session_end_time

    session_response_id = st.session_state.max_id_session_responses + 1
    print(session_response_id)

    newdata_dict = {'id'                 :session_response_id,
                    'user_id'            :user_id,
                    'name'               :name,
                    'email'              :email,
                    'boyfriend_name'     :bf_name,
                    'language'           :language,
                    'toxic_score': safe_decimal(toxic_score),
                    **{k: safe_decimal(v) for k, v in redflag_responses.items()},
                    **{k: safe_decimal(v) for k, v in filter_responses.items()},
                    'filter_violations': safe_decimal(filter_violations),
                    'session_start_time' :session_start_time,
                    'result_start_time'  :result_start_time,
                    'session_end_time'   :session_end_time
                    }
    try:
        write_sucess = add_data(DB_WRITE, table_name, newdata_dict)
        if write_sucess:
            # Update the max_id only if write was successful
            st.session_state.max_id_session_responses = session_response_id
        print("Data successfully written to database")
    except Exception as e:
        print(f"Error writing to database: {str(e)}")
    

def save_gtk_response(DB_WRITE):
    print("save gtk response data to both local and db")   
    table_name  = "session_gtk_responses"
    user_id     = st.session_state.user_details["user_id"]
    name        = st.session_state.user_details["name"]
    email       = st.session_state.user_details["email"]
    language    = st.session_state.user_details["language"]
    bf_name     = st.session_state.user_details["bf_name"]

    gtk_responses       = st.session_state.extra_questions_responses

    session_start_time  = st.session_state.session_start_time
    gtk_response_id     = st.session_state.max_id_gtk_responses + 1

    newdata_dict = {'id'                 :gtk_response_id,
                    'user_id'            :user_id,
                    'name'               :name,
                    'email'              :email,
                    'boyfriend_name'     :bf_name,
                    'language'           :language,
                    'test_date'          :session_start_time,
                    **gtk_responses                    
                    }
    try:
        write_sucess = add_data(DB_WRITE, table_name, newdata_dict)
        if write_sucess:
            # Update the max_id only if write was successful
            st.session_state.max_id_gtk_responses = gtk_response_id
        print("Data successfully written to database")
    except Exception as e:
        print(f"Error writing to database: {str(e)}") 

def save_feedback(DB_WRITE):
    print("save feedback data to both local and db")   
    table_name  = "session_feedback"
    user_id     = st.session_state.user_details["user_id"]
    name        = st.session_state.user_details["name"]
    email       = st.session_state.user_details["email"]
    language    = st.session_state.user_details["language"]
    bf_name     = st.session_state.user_details["bf_name"]

    rating   = st.session_state.feedback_rating

    session_start_time  = st.session_state.session_start_time
    feedback_id         = st.session_state.max_id_feedback +1 
     
    newdata_dict = {'id'                 :feedback_id,
                    'user_id'            :user_id,
                    'user_name'          :name,
                    'email'              :email,
                    'boyfriend_name'     :bf_name,
                    'language'           :language,
                    'test_date'          :session_start_time,
                    'rating'             :rating
                    }
    try:
        write_sucess = add_data(DB_WRITE, table_name, newdata_dict)
        if write_sucess:
            # Update the max_id only if write was successful
            st.session_state.max_id_feedback = feedback_id
        print("Data successfully written to database")
    except Exception as e:
        print(f"Error writing to database: {str(e)}") 

def save_toxicity_rating(DB_WRITE):
    print("save toxicity rating data to both local and db")   
    table_name  = "session_toxicity_rating"
    user_id     = st.session_state.user_details["user_id"]
    name        = st.session_state.user_details["name"]
    email       = st.session_state.user_details["email"]
    language    = st.session_state.user_details["language"]
    bf_name     = st.session_state.user_details["bf_name"]

    toxicity_rating     = st.session_state.toxicity_rating
    session_start_time  = st.session_state.session_start_time
    toxicity_rating_id  = st.session_state.max_id_session_toxicity_rating + 1 

    newdata_dict = {'id'                 :toxicity_rating_id,
                    'user_id'            :user_id,
                    'name'               :name,
                    'email'              :email,
                    'boyfriend_name'     :bf_name,
                    'language'           :language,
                    'test_date'          :session_start_time,
                    'toxicity_rating'    :toxicity_rating
                    }
    try:
        write_sucess = add_data(DB_WRITE, table_name, newdata_dict)
        if write_sucess:
            # Update the max_id only if write was successful
            st.session_state.max_id_session_toxicity_rating = toxicity_rating_id
        print("Data successfully written to database")
    except Exception as e:
        print(f"Error writing to database: {str(e)}") 



def update_output_summary(DB_WRITE):
    print("update Session Summary")
    cur_toxic_score = st.session_state.toxic_score
    sum_toxic_score = st.session_state.sum_toxic_score + Decimal(str(cur_toxic_score))
    count_guys      = st.session_state.count_guys + 1
    avg_toxic_score = Decimal(1.0)*sum_toxic_score/count_guys
    max_toxic_score = st.session_state.max_toxic_score
    max_toxic_score = max_toxic_score if max_toxic_score >cur_toxic_score else cur_toxic_score
    min_toxic_score = st.session_state.min_toxic_score
    min_toxic_score = min_toxic_score if min_toxic_score < cur_toxic_score else cur_toxic_score

    cur_filter_violations = st.session_state.filter_violations
    sum_filter_violations = st.session_state.sum_filter_violations + cur_filter_violations
    avg_filter_violations = Decimal(1.0)*sum_filter_violations /count_guys

    max_id_session_responses        = st.session_state.max_id_session_responses     
    max_id_gtk_responses            = st.session_state.max_id_gtk_responses      
    max_id_feedback                 = st.session_state.max_id_feedback   
    max_id_session_toxicity_rating  = st.session_state.max_id_session_toxicity_rating
    last_date                       = st.session_state.session_start_time
    
    update_dict = {'sum_toxic_score':sum_toxic_score,
                   'max_toxic_score':max_toxic_score,
                   'min_toxic_score':min_toxic_score,
                   'avg_toxic_score':avg_toxic_score,
                   'sum_filter_violations':sum_filter_violations,
                   'avg_filter_violations':avg_filter_violations,
                   'count_guys':count_guys,
                   'max_id_session_responses':max_id_session_responses,
                   'max_id_gtk_responses':max_id_gtk_responses,
                   'max_id_feedback':max_id_feedback,
                   'max_id_session_toxicity_rating':max_id_session_toxicity_rating,
                   'last_update_date':last_date
                   }


    if DB_WRITE:
        table = dynamodb.Table('Summary_Sessions')
        update_expression = "SET " + ", ".join(f"{k} = :{k}" for k in update_dict.keys())
        expression_attribute_values = {f":{k}": v for k, v in update_dict.items()}
        table.update_item(
            Key={'summary_id': 1},  # Your primary key
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

    else:
        file_path = os.path.join('Summary_Sessions' + '.xlsx')
        temp = pd.DataFrame([update_dict])
        cols = ['summary_id']+ list(temp.columns) 
        temp['summary_id'] = 1
        temp = temp[cols].copy()
        temp.to_excel(file_path,sheet_name='Summary_Sessions', index=False)


def get_progress(current_step):
    """Calculate progress percentage based on current step"""
    # Define the survey steps and progress
    SURVEY_STEPS = ["language_selection","user_details","bf_name","welcome","filter_questions","redflag_questions","gtk_questions","toxicity_opinion","results","feedback","goodbye"]
    try:
        progress = (SURVEY_STEPS.index(current_step) + 1) / len(SURVEY_STEPS)
        return min(progress, 1.0)  # Ensure we don't exceed 100%
    except ValueError:
        return 0.0

def initialize_session_state():
        if "counter" not in st.session_state:
            st.session_state.counter = 0
        if "user_details" not in st.session_state:
            st.session_state.user_details = {"user_id":str(uuid.uuid4()),
                                             "name": None, 
                                             "email": None, 
                                             "language": None, 
                                             'bf_name': None}
            

        if "welcome_shown" not in st.session_state:
            st.session_state.welcome_shown = False
        
        if "session_start_time" not in st.session_state:
            test_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.session_start_time = test_date

        if "filter_responses" not in st.session_state:
            st.session_state.filter_responses   = None
            st.session_state.filter_violations  = 0

        if "redflag_responses" not in st.session_state:
            st.session_state.redflag_responses  = None
            st.session_state.toxic_score        = None
            st.session_state.avg_toxic          = None

        if "extra_questions_responses" not in st.session_state:
            st.session_state.extra_questions_responses = None
        if "toxicity_rating" not in st.session_state:
            st.session_state.toxicity_rating    = None
        if "feedback_rating" not in st.session_state:
            st.session_state.feedback_rating    = None
        if "survey_completed" not in st.session_state:
            st.session_state.survey_completed   = False
        if "submitted" not in st.session_state:
            st.session_state.submitted          = False  


def start_new_survey():  
    st.session_state.user_details["bf_name"] = None
    st.session_state.welcome_shown = True
    st.session_state.new_survey_opt = False

    del st.session_state.counter
    del st.session_state.session_start_time, st.session_state.session_end_time , st.session_state.result_start_time
    del st.session_state.filter_responses,st.session_state.redflag_responses,st.session_state.toxic_score,st.session_state.avg_toxic
    del st.session_state.extra_questions_responses, st.session_state.toxicity_rating, st.session_state.survey_completed,st.session_state.submitted 

    if "randomized_questions" in st.session_state:
        del st.session_state.randomized_questions
    if "randomized_filters" in st.session_state:
        del st.session_state.randomized_filters
    


## MAIN ##
def main(DB_READ,DB_WRITE):
    print("*******************************************")
    print("initialize the survey")
    initialize_session_state()
    st.session_state.counter = st.session_state.counter + 1
    print(f"counter: {st.session_state.counter}")

    msg = Message(st.session_state.user_details["language"] or "TR")
    st.title(msg.get_text("survey_title"))

    current_step = "language_selection"
    if not st.session_state.user_details["language"]:
        current_step = "language_selection"
        st.progress(get_progress(current_step))
        print(f"{current_step=}")
        st.session_state.user_details["language"] = 'TR'
        st.rerun()
        #ask_language()
        
    elif not st.session_state.user_details["name"]:
        current_step = "user_details"
        st.progress(get_progress(current_step))
        print(f"{current_step=}")
        #ask_user_details()
        st.session_state.user_details["name"] ='deneme'
        st.session_state.user_details["email"] = 'deneme@deneme.com'
        st.rerun()
        
    elif not st.session_state.user_details["bf_name"]:
        current_step = "bf_name"
        st.progress(get_progress(current_step))
        print(f"{current_step=}")
        ask_bf_name()
        #st.session_state.user_details["bf_name"] ='deneme guy'
        #st.rerun()
        
    else:
        name        = st.session_state.user_details["name"]
        email       = st.session_state.user_details["email"]
        bf_name     = st.session_state.user_details["bf_name"]
        language    = st.session_state.user_details["language"]
        user_id     = st.session_state.user_details["user_id"]  # Use the existing user_id from session state

        print(f"language : {st.session_state.user_details["language"]}")
        print(f"name : {st.session_state.user_details["name"]}")
        print(f"bf_name : {st.session_state.user_details["bf_name"]}")

        #print(f"filter_responses : {st.session_state.filter_responses}")

        msg = Message(language)

        if not st.session_state.welcome_shown:
            current_step = "welcome"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            welcome(name, language)
            if st.button(msg.get_text("continue_msg")):
                st.session_state.welcome_shown = True 
                st.rerun()

        elif not st.session_state.filter_responses:
            current_step = "filter_questions"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            filters = get_filter_questions()
            filter_responses,filter_violations = ask_filter_questions(filters, language)
            if st.button(msg.get_text("continue_msg")):
                if filter_responses:
                    st.session_state.filter_responses     = filter_responses
                    st.session_state.filter_violations    = filter_violations              
                    st.rerun()

        elif not st.session_state.redflag_responses:
            current_step = "redflag_questions"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            st.subheader(msg.get_text("toxicity_header"), divider=True)
            questions = get_redflag_questions()
            answers, toxic_score = ask_redflag_questions(questions, language)
            if st.button(msg.get_text("continue_msg")):
                st.session_state.redflag_responses     = answers
                st.session_state.toxic_score           = toxic_score
                st.rerun()

            
        elif not st.session_state.extra_questions_responses:
            current_step = "gtk_questions"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            st.subheader(msg.get_text("gtk_header"), divider=True)
            gtk_questions = get_gtk_questions()
            gtk_responses = ask_gtk_questions(gtk_questions, language)
            if st.button(msg.get_text("continue_msg")):
                st.session_state.extra_questions_responses = gtk_responses
                st.rerun()
    
        elif not st.session_state.toxicity_rating:
            current_step = "toxicity_opinion"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            toxicity_rating = ask_toxicity_opinion(language)
            if st.button(msg.get_text("see_results")):
                if toxicity_rating:
                    st.session_state.toxicity_rating = toxicity_rating
                    st.rerun()
        

        elif not st.session_state.survey_completed:
            st.balloons()
            current_step = "results"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")

            if "result_start_time" not in st.session_state:
                st.session_state.result_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            get_output_summary(DB_READ)

            st.subheader(msg.get_text("result_header"), divider=True)
            present_result_report()
            if st.button(msg.get_text("survey_complete_msg")):
                st.session_state.survey_completed = True     
                st.rerun()

        elif not st.session_state.feedback_rating:
            current_step = "feedback"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            st.subheader(msg.get_text("enter_feedback_msg"), divider=True)
            rating = generate_feedback(language)
            
            if st.button(msg.get_text("continue_msg")):
                if rating:
                    st.session_state.feedback_rating = rating  # Mark feedback as submitted
                    st.rerun()
                else:
                    st.error(msg.get_text("please_rate_msg"))

        elif not st.session_state.submitted:
            current_step = "goodbye"
            st.progress(get_progress(current_step))
            print(f"{current_step=}")
            print(f"final counter: {st.session_state.counter}")

            if "session_end_time" not in st.session_state:
                st.session_state.session_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            save_session_response(DB_WRITE)
            save_gtk_response(DB_WRITE)
            save_toxicity_rating(DB_WRITE)
            save_feedback(DB_WRITE)

            update_output_summary(DB_WRITE)

            goodbye(name, language)
            st.session_state.submitted = True
            st.session_state.new_survey_opt = True
        
        if "new_survey_opt" in st.session_state:
            if st.session_state.new_survey_opt:
                if st.button(msg.get_text("start_new_survey")):
                    print(f"start new survey")
                    start_new_survey()
                    st.rerun()
                
               
                


# Table and Column Mappings
TABLES_AND_COLUMNS = {'RedFlagQuestions'        : ["ID","Category_ID","Category_Name","RedFLag_ID","RedFlag_Name","Scoring","Weight","Worst_Situation","Question_TR","Question_EN","Hint"],
                      'RedFlagFilters'          : ["Filter_ID","Filter_Name","Scoring","Upper_Limit","Filter_Question_TR","Filter_Question_EN"],
                      'RedFlagCategories'       : ["Category_ID","Category_Name_TR","Category_Name_EN"],
                      'GetToKnowQuestions'      : ["GTK_ID","GTK_Name","Scoring","Levels_TR","Levels_EN","Question_TR","Question_EN","Hint"],
                      'session_responses'       : ["id","user_id","name","email","boyfriend_name","language","toxic_score","Q1","Q2","Q3","Q4","Q5","Q6","Q7","Q8","Q9","Q10","Q11","Q12","Q13","Q14",'Q15','Q16','Q17','Q18','Q19','Q20','Q21','Q22','Q23','Q24','Q25','Q26','Q27','Q28','Q29','Q30','Q31','Q32','Q33','Q34','Q35','Q36','Q37','Q38','Q39','Q40','Q41','Q42','Q43','Q44','Q45','Q46','Q47','Q48','Q49','Q50','Q51','Q52','Q53','Q54','Q55','Q56','Q57','Q58','Q59','Q60','Q61','Q62','Q63','Q64','Q65','Q66','Q67','Q68','Q69','Q70','Q71','Q72','Q73','Q74','Q75','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','F13','F14','F15','filter_violations','session_start_time','result_start_time','session_end_time'],
                      'session_feedback'        : ['id','user_id','user_name','email','boyfriend_name','language','test_date','rating'],
                      'session_gtk_responses'   : ['id','user_id','name','email','boyfriend_name','language','test_date','GTK1','GTK2','GTK3','GTK4','GTK5'],
                      'session_toxicity_rating' : ['id','user_id','name','email','boyfriend_name','language','test_date','toxicity_rating'],
                      'Summary_Sessions'        : ['summary_id', 'sum_toxic_score', 'max_toxic_score', 'min_toxic_score','avg_toxic_score', 
                                                   'sum_filter_violations','avg_filter_violations',
                                                   'count_guys', 'max_id_session_responses','max_id_gtk_responses', 'max_id_feedback','max_id_session_toxicity_rating', 'last_update_date']

}

###
DB_READ = True
DB_WRITE = True


# AWS Credentials
access_code = os.getenv("AWS_ACCESS_KEY_ID")
secret_key  = os.getenv("AWS_SECRET_ACCESS_KEY")
region_name = os.getenv("AWS_DEFAULT_REGION")

if access_code and secret_key and region_name:
    print("running in app service")
else:
    print("running locally, looking for credentials in file")
    secret_file = "aws_credentials.txt"
    secret_file_path = os.getcwd() + '\\' +secret_file
    try:
        with open(secret_file_path, 'r') as file:
            access_code = file.readline().strip()
            secret_key  = file.readline().strip()
            region_name = file.readline().strip()
            if not access_code or not secret_key:
                raise ValueError("File is missing credentials!")
    except FileNotFoundError:
        print("Error: aws_credentials.txt not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if DB_READ or DB_WRITE:
    aws_client = boto3.Session(
        aws_access_key_id=access_code,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )
    dynamodb = aws_client.resource('dynamodb')

# Run the application
if __name__ == "__main__":
    main(DB_READ,DB_WRITE)