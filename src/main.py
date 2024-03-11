import os
from flask import Flask, request, json
from controller import Controller

app = Flask(__name__)

"""
Fuction descriptioin
    - search: return string outcome for the mixed question
        : For Dialogflow CX
    - context: return searched relevant contexts
        : For Dialogflow CX
"""

@app.route("/response", methods=['POST'])
def response():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")
    
    controller = Controller()

    mixed_question = False
    detailed = False
    outcome = controller.response(question,mixed_question, detailed)

    print(f"result {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)


@app.route("/search", methods=['POST'])
def search():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")
    
    controller = Controller()

    mixed_question = False
    detailed = False
    outcome = controller.search(question,mixed_question,detailed)

    print(f"context {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))