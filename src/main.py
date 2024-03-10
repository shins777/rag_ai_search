import os
from flask import Flask, request, json
from controller import Controller

app = Flask(__name__)

@app.route("/search", methods=['POST'])
def search():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")
    
    controller = Controller()

    detailed = False
    outcome = controller.process(question,detailed)

    print(f"outcome {outcome}")

    # Return final outcome only.
    response = {
        "result": outcome
    }

    #return jsonify(response)
    return json.dumps(response,ensure_ascii=False)

@app.route("/search_detail", methods=['POST'])
def search_streamlit():
    params = request.get_json()
    
    question = params['question']
    print(f" question : {question}")
    
    controller = Controller()
    
    detailed = True
    question_list, contexts_list, final_contexts, final_outcome, elapsed_time = controller.process(question, detailed)

    response = {
        "result": "shins"
    }

    #return jsonify(response)
    return json.dumps(response,ensure_ascii=False)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))