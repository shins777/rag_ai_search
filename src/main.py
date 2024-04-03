import os
from flask import Flask, request, json
from controller import Controller
from daou.price import Calculator

app = Flask(__name__)

"""
Fuction descriptioin
    - search: return string outcome for the mixed question
        : For Dialogflow CX
    - context: return searched relevant contexts
        : For Dialogflow CX
"""

# Production env.
prod = True

@app.route("/response_segments", methods=['POST'])
def response_segments():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : False,
        "detailed_return" : False,
        "answer_only" : False # Answers + segments
    }

    outcome = controller.response( question, condition )

    print(f"result {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)


@app.route("/response_answers", methods=['POST'])
def response_answers():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : False,
        "detailed_return" : False,
        "answer_only" : True  # Answer Only.
    }

    outcome = controller.response( question, condition )

    print(f"result {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)

@app.route("/search_segments", methods=['POST'])
def search_segments():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : False,
        "detailed_return" : False,
        "answer_only" : False   # Answers + Segments
    }

    outcome = controller.response( question, condition )

    print(f"context {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)


@app.route("/search_answers", methods=['POST'])
def search_answers():

    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : False,
        "detailed_return" : False, 
        "answer_only" : True  # Only answers
    }

    outcome = controller.response( question, condition )

    print(f"context {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)


@app.route("/search_detailed", methods=['POST'])
def search_detailed():

    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : True,
        "detailed_return" : True,
        "answer_only" : False
    }

    question_list, contexts_list, final_contexts, final_outcome, elapsed_time = controller.response(question, condition)

    print(f"context {final_outcome}")

    response = {
        "question_list": question_list,
        "contexts_list": contexts_list,
        "final_contexts": final_contexts,
        "final_outcome": final_outcome,
        "elapsed_time": elapsed_time
    }

    return json.dumps(response,ensure_ascii=False)


@app.route("/get_price", methods=['POST'])
def get_price():

    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    prod = True
    cal = Calculator(prod)

    outcome, cal_eq = cal.calculate_price(question)

    print(f"context {outcome}")
    print(f"context {cal_eq}")

    response = {
        "result": outcome,
        "calculation steps" : cal_eq
    }

    return json.dumps(response,ensure_ascii=False)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))