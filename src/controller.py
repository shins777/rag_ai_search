import time
import ast
import requests
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from langchain_google_vertexai.llms import VertexAI
from langchain.prompts import PromptTemplate
from langchain import globals

import vertexai
from vertexai.language_models import TextGenerationModel
import google
import google.oauth2.credentials
import google.auth.transport.requests
from google.oauth2 import service_account
import vertexai

from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

import constant as env

class Controller():

    gemini_pro = None
    gemini_native = None
    bison = None
    credentials = None

    # Langchain verbose
    globals.set_verbose(False)

    def __init__(self):

        Controller.gemini_pro = VertexAI( model_name = env.gemini_model,
                    project=env.project_id,
                    location=env.region,
                    streaming=False,
                    temperature = 0.2,
                    top_p = 1,
                    top_k = 40
                    )

        Controller.gemini_native = GenerativeModel("gemini-1.0-pro-001")

        if env.request == "dev":

            svc_file = "/Users/hangsik/projects24/_service_account_key/ai-hangsik-71898c80c9a5.json"
            Controller.credentials = service_account.Credentials.from_service_account_file(
                svc_file, 
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
        else:
            Controller.credentials, project_id = google.auth.default()

        vertexai.init(project=env.project_id, location=env.region, credentials = Controller.credentials )
        Controller.bison = TextGenerationModel.from_pretrained(env.bison_model)

        print(f"[Controller][__init__] Controller.gemini_pro langchain : {Controller.gemini_pro}")
        print(f"[Controller][__init__] Controller.gemini_pro native : {Controller.gemini_native}")
        print(f"[Controller][__init__] Controller.bison : {Controller.bison}")
        print(f"[Controller][__init__] Initialize Controller done!")


    def process(self, question:str, detailed:str ):

        t1 = time.time()

        question_list = self.question_verifier(question)

        t2 = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            searched_contexts = executor.map(self.ai_search, question_list)

        two_nested_list = [context for context in searched_contexts]

        one_nested_list = list(np.concatenate(two_nested_list))
        contexts_list = list(np.concatenate(one_nested_list))

        t3 = time.time()

        new_question_list =[]

        for context in contexts_list:
            new_question_list.append(context['query'])

        with ThreadPoolExecutor(max_workers=10) as executor:
            verified_contexts = executor.map(self.context_verifier, contexts_list, new_question_list)

        final_contexts = ""
        for context in verified_contexts:
            if context !=None:
                final_contexts = final_contexts + "\n\n[SEARCHED CONTEXT] : " + context['facts']

        t4 = time.time()
        
        final_outcome = self.final_request( question, final_contexts)

        t5 = time.time()

        elapsed_time = f"Total elapsed time : {t5-t1} : question_verifier[{t2-t1}], ai_search {t3-t2}], context_verifier [{t4-t3}], final_request [{t5-t4}] "

        print(f"[Controller][process] Final_outcome : {final_outcome}")
        print(f"[Controller][process] Elapsed time : {elapsed_time}")

        if detailed:
            return question_list, contexts_list, final_contexts, final_outcome, elapsed_time
        else:
            return final_outcome

    def question_verifier(self, question :str ):

        prompt = PromptTemplate.from_template("""
            당신을 정확한 검색을 위한 질문 생성기 입니다.
            아래 [Question]에 답하기 위한 사실을 검색할 목적으로, [Question]을 기반으로 2가지 질문을 만들어 주세요.
            답변 형태는 반드시 아래와 같은 파이썬 리스트 포맷으로 답해주세요.
                                              
            [Question] : {question}
            답변 포맷 : ["질문1", "질문2"]

        """)

        prompt = prompt.format(question=question)

        questions = Controller.gemini_pro.invoke(prompt)

        num_q = 2
        try:
            q_list = ast.literal_eval(questions)

        # 만일 질문 생성 후 파싱이 에러가 나면 아래 로직으로 처리.
        except Exception as e:
            for i in range(num_q):
                q_list.append(question)            

        print(f"[Controller][question_verifier] Generated Question List : {q_list}")

        return q_list 

    def ai_search(self, question : str):

        searched_ctx = self.retrieve_vertex_ai_search(question, env.search_url, env.num_docs )
        context = self.parse_discovery_results(question, searched_ctx)
        
        print(f"[Controller][ai_search] AI Search Done! {len(context)}")

        return context

    def retrieve_vertex_ai_search(self, question, search_url, retrival_num):

        request = google.auth.transport.requests.Request()
        Controller.credentials.refresh(request)

        #print(f"credentials :{credentials}")
        #print(f"credentials.token :{credentials.token}")

        headers = {
            "Authorization": "Bearer "+ Controller.credentials.token,
            "Content-Type": "application/json"
        }
        
        query_dic ={
            "query": question,
            "page_size": str(retrival_num),
            "offset": 0,
            "contentSearchSpec":{
                # "snippetSpec": {"maxSnippetCount": 5,
                #                 },
                # "summarySpec": { "summaryResultCount": 5,
                #                  "includeCitations": True},
                "extractiveContentSpec":{
                    "maxExtractiveAnswerCount": 3,
                    "maxExtractiveSegmentCount": 1,
                    "num_previous_segments" : 1,
                    "num_next_segments" : 1,
                    }
            },
            # "queryExpansionSpec":{"condition":"AUTO"}
        }

        data = json.dumps(query_dic)
        data=data.encode("utf8")
        response = requests.post(search_url,headers=headers, data=data)

        print(f"[Controller][retrieve_vertex_ai_search] Response len : {len(response.text)}")

        return response.text

    def parse_discovery_results(self, question, response_text):

        """Parse response to build a conext to be sent to LLM"""

        dict_results = json.loads(response_text)

        serched_documents = []
        searched_ctx_dic = []

        if dict_results.get('results'):
            for result in dict_results['results']:
                answer_ctx =""
                segments_ctx =""
                item = {}
                derivedStructData = result['document']['derivedStructData']

                #reference = derivedStructData['link']
                #reference__name = reference.rsplit('/', 1)[1].strip()
                #reference_link = reference.replace("gs://","https://storage.cloud.google.com/")

                if derivedStructData['extractive_answers']:
                    for answer in derivedStructData['extractive_answers']:
                        answer_ctx = answer_ctx + answer['content']

                if derivedStructData.get('extractive_segments'):
                    for segment in derivedStructData['extractive_segments']:
                        segments_ctx = segments_ctx + segment['content']

                answer_ctx = answer_ctx.replace("<b>","").replace("</b>","").replace("&quot;","")
                segments_ctx = segments_ctx.replace("<b>","").replace("</b>","").replace("&quot;","")

                item['query']= question
                item['facts']= "\nAnswer : "+ answer_ctx + "\nSegments : " + segments_ctx

                searched_ctx_dic.append(item)

            serched_documents.append(searched_ctx_dic)

        print(f"[Controller][searched_ctx_dic] serched_documents len : {len(serched_documents)}")

        return serched_documents

    def context_verifier(self, context : str, question : str):


        prompt = PromptTemplate.from_template("""
            당신은 아래 Context가 Question과 관련되어 있는지 확인하는 AI 입니다.
            아래 [Context]의 일부 내용이 아래 [Question]과 조금이라도 관련이 있으면 "Yes" 라고 말하세요.
            만일, 아래 [Context]의 내용이 아래 [Question]과 전혀 관련이 없으면 "No"라고 말하세요.

            [Context] : {context}
            [Question] : {question}        
                                              
        """)

        prompt = prompt.format(context=context,
                            question=question)

        result = Controller.gemini_pro.invoke(prompt)

        print(f"[Controller][context_verifier] Question : {question}, Verification Result : {result}")
        # print(f"context : {context}")

        if result == "Yes":
            return context
            #return json.dumps(context,ensure_ascii=False)

    def final_request(self, question, context):

        prompt = PromptTemplate.from_template("""

        당신은 지식을 검색해서 상담해주는 AI 어시스턴트입니다.
        아래 Question 에 대해서 반드시 [SEARCHED CONTEXT]들에 있는 내용만을 참고해서 단계적으로 추론 후 요약해서 답변해주세요.
        답변은 결론을 먼저 언급하고, 그 뒤에 이유를 최대한 상세하게 정리해서 답해주세요.

        {context}
        Question : {question}

        """)

        prompt = prompt.format(context=context,
                                question=question)

        #outcome = Controller.gemini_pro.invoke(prompt)
        outcome = self.call_bision(prompt)
        outcome = self.call_gemini(prompt)

        #print(f"[Controller][final_request] Prompt : {prompt}")

        return outcome

    def call_bision(self, prompt):
        
        parameters = {
            "candidate_count": 1,
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 1
        }
        response = Controller.bison.predict(
            prompt=prompt,
            **parameters
        )

        print(f"[Controller][call_bision] Final response Len {len(response.text)}")

        return response.text    

    def call_gemini(self, prompt):
        
        generation_config = {
            "candidate_count": 1,
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 1
        }
        responses = Controller.gemini_native.generate_content(
            [prompt],
            generation_config = generation_config
        ) 
        return responses.text            
