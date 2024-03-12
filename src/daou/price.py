
import vertexai
import google
import google.oauth2.credentials
import google.auth.transport.requests
from google.oauth2 import service_account

from vertexai.preview.generative_models import FunctionDeclaration
from vertexai.preview.generative_models import GenerativeModel
from vertexai.preview.generative_models import Part
from vertexai.preview.generative_models import Tool

import constant as env
import logging

logging.basicConfig(
  format = '%(asctime)s:%(levelname)s:%(message)s',
  #datefmt = '%Y-%m-%d: %I:%M:%S %p',
  level = logging.INFO
)

class Calculator():
    
    gemini_native = None

    def __init__(self, prod:bool):

        # Logger setting. 
        if env.logging == "INFO": logging.getLogger().setLevel(logging.INFO)
        else: logging.getLogger().setLevel(logging.DEBUG)

        # if prod = False, use svc account.
        if not prod:
            
            # the location of service account in Cloud Shell.
            svc_file = "/home/admin_/keys/ai-hangsik-71898c80c9a5.json"
            Calculator.credentials = service_account.Credentials.from_service_account_file(
                svc_file, 
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
        else:
            # Use default auth in Cloud Run env. 
            Calculator.credentials, project_id = google.auth.default()

        # Initialize Vertex AI env with the credentials. 
        vertexai.init(project=env.project_id, location=env.region, credentials = Calculator.credentials )

        get_product_price = FunctionDeclaration(
                name="get_price",
                description="사용자 수, 제품 타입, 계약기간, 용량 추가 기반으로 클라우드 오피스 제품의 1개월 단위 가격을 알아내는 함수",
                parameters={
                    "type": "object",
                    "properties": {
                        "users": { "type": "string","description": "사용자 수"},
                        "product_type": { "type": "string","description": "제품 타입(공유형, 단독형"},
                        "months": { "type": "string","description": "계약 기간 개월 수"},
                        "capacity": { "type": "string","description": "용량 추가"},
                    },
                },
            )
        # Tools
        tools = Tool(function_declarations=[get_product_price,],)

        generation_config = {
            "candidate_count": 1,
            "max_output_tokens": 2048,
            "temperature": 0.2,
            "top_p": 1
        }

        # Initialize Gemini Pro on native way using API.
        Calculator.gemini_native = GenerativeModel(env.gemini_model,
                        generation_config=generation_config,
                        tools=[tools])


    def get_price(self, parameters):
        product_type = parameters['product_type']
        months = int(parameters['months'])
        users = int(parameters['users'])
        capacity = int(parameters['capacity'])

        print("===[ 가격 계산 요청값]===")
        print(f"제품 유형 :{product_type}")
        print(f"사용자 유저수 :{users}")

        max_users_range = [100,200,200]
        excl_users_range =[100,300,500]

        if product_type =='공유형':
            unit_price_range= [4000,3200,2400,1600]
        elif product_type =='단독형':
            unit_price_range= [5000,4000,3000,2000]
        else:
            print("No product type : default : 공유형 ")
            unit_price_range= [4000,3200,2400,1600]

        # 사용자 기준 가격 산정
        user_total_price = self.price_calculation(users = users,
                                        max_users_range = max_users_range ,
                                        unit_price_range = unit_price_range,
                                        excl_users_range = excl_users_range )
        print(f"사용자 수 기준 가격 : {user_total_price}")

        # 단독형은 월 200,000 만원 추가.
        type_total_price = user_total_price + 200000 if product_type == "단독형" else user_total_price
        print(f"공유형/단독형 기반 가격 계산 :{type_total_price}")

        # 용량 추가 기반 가격 계산.
        capacity_total_price,add_capacity = self.capacity_calculation(type_total_price,capacity )
        print(f"용량 추가 기반 가격 계산 :{capacity_total_price}")

        # 할인율 적용.
        discounted_price, discount = self.discount_calculation(product_type = product_type,
                                                total_price = capacity_total_price,
                                                months = months)
        print(f"{months} 개월 할인률 적용 가격 :{discounted_price}")

        #output = f"클라우드 {product_type} 오피스 제품 총 {users}명의 1개월 최종 {discount} 가격은 {discounted_price} 입니다."
        output = f"""
[계산 결과]
클라우드 {product_type} 오피스 제품 총 {users}명의 1개월 최종 {discount} 가격은 {discounted_price} 입니다.

[계산 과정]
- 사용자 {users}명 기준 가격 : {user_total_price}
- 제품 타입 : {product_type}
: 제품 타입 적용 후 가격 : {type_total_price} (단독형일 경우 기본가격(200,000) 추가됨.)
- {add_capacity}
: 용량 추가 관련 계산 후 가격 :{capacity_total_price}
- {months} 개월 할인률 적용 후 최종 가격 :{discounted_price}

        """

        #print(f"최종 가격 계산 : {output}" )

        return output

    def price_calculation(self, users, max_users_range, unit_price_range, excl_users_range  ):

        price1,price2,price3,price4,total_price = 0,0,0,0,0

        if users >= 501:
            price1 = max_users_range[0]*unit_price_range[0]
            price2 = max_users_range[1]*unit_price_range[1]
            price3 = max_users_range[2]*unit_price_range[2]
            price4 = (users- excl_users_range[2])*unit_price_range[3]

        elif users >= 301 and users <= 500:
            price1 = max_users_range[0]*unit_price_range[0]
            price2 = max_users_range[1]*unit_price_range[1]
            price3 = (users-excl_users_range[1])*unit_price_range[2]

        elif users >= 101 and users <= 300:
            price1 = max_users_range[0]*unit_price_range[0]
            price2 = (users-excl_users_range[0])*unit_price_range[1]

        elif users <= 100:
            price1 = max_users_range[0]*unit_price_range[0]
        else:
            print(f"No users : {users}")

        total_price = price1+price2+price3+price4

        return total_price

    def discount_calculation(self, product_type,total_price, months):
        discount ="할인율 적용 없음"

        if months >= 12:
            if product_type == '공유형':
                discount = "공유형 할인율 50% 적용"

                total_price = total_price - total_price*0.5
            elif product_type == '단독형':
                discount = "단독형 할인율 5% 적용"

                total_price = total_price - total_price*0.05

        return total_price, discount

    def capacity_calculation(self, total_price, capacity):

        add_capacity = f"용량 추가 있음 {capacity} GB"

        if capacity == 0: 
            add_capacity = "용량추가 없음"
        elif capacity == 10: 
            total_price = total_price + 10000
        elif capacity == 100: 
            total_price = total_price + 50000 - 20000
        elif capacity == 500: 
            total_price = total_price + 100000 - 30000
        elif capacity == 1000: 
            total_price = total_price + 150000 - 50000

        return total_price, add_capacity

    def calculate_price(self, question):

        chat = Calculator.gemini_native.start_chat()

        prompt = f"""
            당신은 다우오피스 공유형과 단독형의 오피스 제품의 가격을 계산하는 AI 어시스턴트입니다.
            아래 Question 에 제시된 정보를 기준으로 1개월 기준 가격과 함께 해당 계약기간에 따른 가격 알려주세요.

            만일 Question에 계산을 위해서 사용자수, 제품타입, 계약기간, 용량추가에 대해서 참조할 값이 없다면 아래 디폴트 값을 참조하고 계산해주세요.

            [디폴트 값]
            * 사용자수(users) : 550
            * 제품타입(product_type) : 공유형
            * 계약기간(months) : 12개월
            * 용량추가(capacity) : 0

            Question : {question}

            """
        response = chat.send_message(prompt)

        # Check for function call and dispatch accordingly - This is mandatory
        function_call = response.candidates[0].content.parts[0].function_call

        # function_call.args['users']

        # Dispatch table for function handling
        function_handlers = {
            "get_price": self.get_price,
            #"get_discounted_price": get_discounted_price,

        }

        if function_call.name in function_handlers:
            function_name = function_call.name

            chat_response = ""

            # Directly extract arguments from function call
            args = {key: value for key, value in function_call.args.items()}

            # Call the function with the extracted arguments
            if args:
                function_response = function_handlers[function_name](args)
                part_data = Part.from_function_response(
                        name=function_name,
                        response={
                            "content": function_response,
                        }
                )
                cal_eq = part_data.to_dict()['function_response']['response']['content']

                response = chat.send_message(part_data,)
                chat_response = response.candidates[0].content.parts[0].text

            else:
                print("가격 계산을 위한 적합한 정보가 없습니다.")
        else:
            print("\n 좀더 가격계산을 위한 자세한 정보를 주세요.(제품종류, 유저수, 계약개월수, 용량추가)", response.text)

            return response.text, None

        return chat_response, cal_eq
