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
import google
import google.oauth2.credentials
import google.auth.transport.requests
from google.oauth2 import service_account

from vertexai.language_models import TextGenerationModel
from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

import logging

logging.basicConfig(
  format = '%(asctime)s:%(levelname)s:%(message)s',
  #datefmt = '%Y-%m-%d: %I:%M:%S %p',
  level = logging.INFO
)

import constant as env

class Controller():
    """
    Class to perform the RAG architecture with Vertex AI Search
    Specific flows are as follows.
        1. Divide and verify the given complex question 
        2. Search relavant contexts for the respective question by using Vertex AI Search
        3. Verifying the contexts searched from Vertex AI Search
        4. Building a final context with the question.
        5. Return back to the results in the two ways of detailed and simple. 
    """
    gemini_pro = None
    gemini_native = None
    bison = None
    credentials = None

    # Langchain verbose
    globals.set_verbose(False)

    def __init__(self, prod:bool ):

        # Logger setting. 
        if env.logging == "INFO": logging.getLogger().setLevel(logging.INFO)
        else: logging.getLogger().setLevel(logging.DEBUG)

        # if prod = False, use svc account.
        if not prod:
            
            # the location of service account in Cloud Shell.
            svc_file = "/home/admin_/keys/ai-hangsik-71898c80c9a5.json"
            Controller.credentials = service_account.Credentials.from_service_account_file(
                svc_file, 
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
        else:
            # Use default auth in Cloud Run env. 
            Controller.credentials, project_id = google.auth.default()

        # Initialize Vertex AI env with the credentials. 
        vertexai.init(project=env.project_id, location=env.region, credentials = Controller.credentials )

        # Initialize Gemini Pro on native way using API.
        Controller.gemini_native = GenerativeModel(env.gemini_model)

        # Initialize Text Bison by using native way. 
        Controller.bison = TextGenerationModel.from_pretrained(env.bison_model)

        logging.info(f"[Controller][__init__] Controller.gemini_pro langchain : {Controller.gemini_pro}")
        logging.info(f"[Controller][__init__] Controller.gemini_pro native : {Controller.gemini_native}")
        logging.info(f"[Controller][__init__] Controller.bison : {Controller.bison}")
        logging.info(f"[Controller][__init__] Initialize Controller done!")

    def response(self, question:str, condition:dict ):
        """
        Controller to execute the RAG processes.
        """

        mixed_question = condition['mixed_question']
        detailed_return = condition['detailed_return']
        answer_only = condition['answer_only']

        t1 = time.time()
        final_contexts = self.search(question, condition)

        t2 = time.time()
        prompt = PromptTemplate.from_template("""
        당신은 지식을 검색해서 상담해주는 AI 어시스턴트입니다.
        아래 Question 에 대해서 반드시 [Facts]들에 있는 내용만을 참고해서 단계적으로 추론 후 요약해서 답변해주세요.
        답변은 결론을 먼저 언급하고, 그 뒤에 이유를 최대한 상세하게 정리해서 답해주세요.
        {context}
        Question : {question}
        """)

        prompt = prompt.format(context=final_contexts, question=question)

        # text bison is more detail to answer as of Mar 12, 2024.
        #outcome = self.call_bison(prompt)
        
        # gemini is more concise to answer as of Mar 12, 2024.
        final_outcome = self.call_gemini(prompt)

        logging.debug(f"[Controller][response] Prompt : {prompt}")

        t3 = time.time()

        elapsed_time = f"Search [{t2-t1} : LLM Request[{t3-t2}] : Total elapsed time : [{t3-t1}] :  "

        logging.info(f"[Controller][response] Final_outcome : {final_outcome}")
        logging.info(f"[Controller][response] Elapsed time : {elapsed_time}")

        if detailed_return:
            return question_list, contexts_list, final_contexts, final_outcome, elapsed_time
        else:
            return final_outcome

    def search(self, question:str, condition:dict ):
        """
        Controller to execute the RAG processes.

        1. Call flow for mixed question:
            question_splitter --> ai_search
        2. Call flow for singuar question: 
            ai_search
        
        - quesiton : user query.
        - mixed_question : complex and composite questions 
        - detailed : return more detailed information.

        """
        
        mixed_question = condition['mixed_question']
        answer_only = condition['answer_only']

        t1 = time.time()

        if mixed_question:
            
            logging.info(f"[Controller][search] Mixed Question Processing Start! : {question}")

            # Question split for the composite question which contains several questions in a sentence.
            splitted_questions = self.question_splitter(question)

            t2 = time.time()

            # Parallel processing to reduce the latency for the Vertex AI Search. 
            with ThreadPoolExecutor(max_workers=10) as executor:
                searched_contexts = executor.map(self.ai_search, splitted_questions, answer_only )

            two_nested_list = [context for context in searched_contexts]
            one_nested_list = list(np.concatenate(two_nested_list))            
            contexts_list = list(np.concatenate(one_nested_list))
            
            logging.info(f"[Controller][search] len(contexts_list) : {len(contexts_list)}")
            logging.debug(f"[Controller][search] contexts_list : {contexts_list}")

        else:
    
            logging.info(f"[Controller][search] Simple Question Processing Start! : {question}")
            
            t2 = time.time()            

            # Search contexts from the question directly in the different way which one question is searched. 
            contexts = self.ai_search(question, answer_only )
            contexts_list = contexts[0]

            logging.info(f"[Controller][search] len(contexts_list) : {len(contexts_list)}")
            logging.debug(f"[Controller][search] contexts_list : {contexts_list}")

        t3 = time.time()

        question_list =[]

        for context in contexts_list:
            question_list.append(context['query'])

        logging.debug(f"[Controller][search] question_list : {question_list}")

        # Context Verification for the each contex searched from the Vertex AI Search.
        with ThreadPoolExecutor(max_workers=10) as executor:
            verified_contexts = executor.map(self.context_verifier, contexts_list, question_list)

        logging.debug(f"[Controller][search] verified_contexts : {verified_contexts}")

        # Build the final context consolidated from verified contexts.
        final_contexts = ""
        for context in verified_contexts:
            if context != None:
                final_contexts = final_contexts + "\n[Facts] : " + context['facts']

        logging.debug(f"[Controller][search] final_contexts : {final_contexts}")

        t4 = time.time()

        elapsed_time = f"question_splitter[{t2-t1}] : ai_search {t3-t2}] : context_verifier [{t4-t3}] : Total search time : {t4-t1} "
        logging.info(f"[Controller][search] Elapsed time : {elapsed_time}")

        logging.debug(f"[Controller][search] Final_outcome : {final_contexts}")

        return final_contexts


    def question_splitter(self, question :str )->list:

        prompt = PromptTemplate.from_template("""
            당신을 정확한 검색을 위한 질문 생성기 입니다.
            아래 [Question]에 답하기 위한 사실을 검색할 목적으로, [Question]을 기반으로 2가지 질문을 만들어 주세요.
            답변 형태는 반드시 아래와 같은 파이썬 리스트 포맷으로 답해주세요.
                                              
            [Question] : {question}
            답변 포맷 : ["질문1", "질문2"]

        """)

        prompt = prompt.format(question=question)

        questions = self.call_gemini(prompt)

        num_q = 2
        try:
            q_list = ast.literal_eval(questions)

        # Handling for exception when splitting mixed question.
        except Exception as e:
            logging.info(f"[Controller][question_splitter] Splitting failed")
            for i in range(num_q):
                q_list.append(question)            

        logging.info(f"[Controller][question_verifier] Generated Question List : {q_list}")

        return q_list 

    def ai_search(self, question : str, answer_only:bool)->dict:

        searched_ctx = self.retrieve_vertex_ai_search(question,env.search_url)
        context = self.parse_discovery_results(question, searched_ctx, answer_only)
        
        logging.info(f"[Controller][ai_search] AI Search Done! {len(context)}")

        return context

    def retrieve_vertex_ai_search(self, question:str, search_url:str )->str:

        request = google.auth.transport.requests.Request()
        Controller.credentials.refresh(request)

        headers = {
            "Authorization": "Bearer "+ Controller.credentials.token,
            "Content-Type": "application/json"
        }
        
        query_dic ={
            "query": question,
            "page_size": str(env.num_search),
            "offset": 0,
            "contentSearchSpec":{
                # "snippetSpec": {"maxSnippetCount": 0,
                #                 },

                # INFO : Summary needs another LLM call so that that makes more latency than normal.
                # "summarySpec": { "summaryResultCount": 5,
                #                  "includeCitations": False},
                "extractiveContentSpec":{
                    "maxExtractiveAnswerCount": str(env.maxExtractiveAnswerCount),
                    "maxExtractiveSegmentCount": str(env.maxExtractiveSegmentCount),
                    "num_previous_segments" : str(env.num_previous_segments),
                    "num_next_segments" : str(env.num_next_segments),
                    }
            },
            # "queryExpansionSpec":{"condition":"AUTO"}
        }

        data = json.dumps(query_dic)
        data=data.encode("utf8")
        response = requests.post(search_url,headers=headers, data=data)

        logging.info(f"[Controller][retrieve_vertex_ai_search] Response len : {len(response.text)}")
        logging.debug(f"[Controller][retrieve_vertex_ai_search] Response len : {response.text}")

        return response.text

    def parse_discovery_results(self, question:str, response_text:str, answer_only:bool)->dict:

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

                if answer_only: 
                    item['facts']= " "+ answer_ctx
                else: 
                    item['facts']= " "+ answer_ctx + " " + segments_ctx

                searched_ctx_dic.append(item)

            serched_documents.append(searched_ctx_dic)

        logging.info(f"[Controller][parse_discovery_results] serched_documents len : {len(serched_documents)}")
        logging.debug(f"[Controller][parse_discovery_results] serched_documents len : {serched_documents}")

        return serched_documents

    def context_verifier(self, context : str, question : str)->str:

        """
        The purpose of this function is to decrease the context size for the better latency. 
        Small context size helps to decrease the latency. 
        """

        prompt = PromptTemplate.from_template("""
            당신은 아래 Context가 Question과 관련되어 있는지 확인하는 AI 입니다.
            아래 [Context]의 일부 내용이 아래 [Question]과 조금이라도 관련이 있으면 "Yes" 라고 말하세요.
            만일, 아래 [Context]의 내용이 아래 [Question]과 전혀 관련이 없으면 "No"라고 말하세요.

            [Context] : {context}
            [Question] : {question}        
                                              
        """)

        prompt = prompt.format(context=context,
                            question=question)

        result = self.call_gemini(prompt)

        logging.info(f"[Controller][context_verifier] Question : {question}, Verification Result : {result}")

        # if the context is relevant to the question, return the context. 
        if result == "Yes":
            return context

    def call_bison(self, prompt):
        
        parameters = {
            "candidate_count": 2,
            "max_output_tokens": 2048,
            "temperature": 0.2,
            "top_p": 1
        }
        responses = Controller.bison.predict(
            prompt=prompt,
            **parameters
        )

        logging.debug(f"[Controller][call_bison] Final response Len {len(responses.text)}")

        return responses.text    

    def call_gemini(self, prompt):
        
        generation_config = {
            "candidate_count": 1,
            "max_output_tokens": 2048,
            "temperature": 0.2,
            "top_p": 1
        }
        responses = Controller.gemini_native.generate_content(
            [prompt],
            generation_config = generation_config
        ) 

        logging.debug(f"[Controller][call_bison] Final response Len {len(responses.text)}")

        return responses.text            

