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

@app.route("/search", methods=['POST'])
def search():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")

    controller = Controller(prod)

    condition = {
        "mixed_question" : False,
        "detailed_return" : False,
    }

    outcome = controller.response( question, condition )

    print(f"result {outcome}")

    response = {
        "result": outcome
    }

    return json.dumps(response,ensure_ascii=False)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))