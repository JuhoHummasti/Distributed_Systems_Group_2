import json
import grpc
import os
from concurrent import futures
from openai import OpenAI
from ai_service_pb2 import AIResponse
from ai_service_pb2_grpc import OpenAIServiceServicer, add_OpenAIServiceServicer_to_server

class OpenAIService(OpenAIServiceServicer):
    def __init__(self):
        self.client = OpenAI()

    def ProcessRequest(self, request, context):
        try:
            # Parse the incoming JSON data
            input_data = json.loads(request.json_data)
            
            # Construct the prompt using the input data
            prompt = f"The following data contains file names and how often they are accessed. Based on this data you have to predict which files will be popular in the next few hours and should be cached. Return a json array containing file names and nothing else. Array should be sorted in a way that most important files are in the start and least important are in the end. Intelligently cache files, don't cache everything. Here's the data: {json.dumps(input_data)}"
            print("Prompt:", prompt)

            # Make the API call to OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a file caching assistant in a CDN service. Your job is to intelligently predict which files to cache based on access patterns."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            
            # Extract the JSON response
            json_response = response.choices[0].message.content
            print("Response:", json_response)
            
            # Validate JSON response
            json.loads(json_response)  # This will raise an exception if the response is not valid JSON
            
            return AIResponse(json_response=json_response)
            
        except json.JSONDecodeError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid JSON format: {str(e)}")
            return AIResponse()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing request: {str(e)}")
            return AIResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_OpenAIServiceServicer_to_server(OpenAIService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()