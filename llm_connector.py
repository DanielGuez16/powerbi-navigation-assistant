import json
import traceback
from typing import Any, Union
import requests
import streamlit as st
import urllib3
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()  # Load environment variables from .env file

# Disable HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LLMConnector:
    def __init__(self):
        """ Initializes the LLMConnector class. """
        self.URL_GET_TOKENS = {
            "bench": "https://api.ai.bench.intranet.groupebpce.fr/oauth2/token",
            "prod": "https://api.ai.intranet.groupebpce.fr/oauth2/token",
            "dev": "https://api.ai.uat.intranet.groupebpce.fr/oauth2/token",
        }

        self.URL_IA_ENDPOINTS = {
            "bench": "https://api.ai.bench.intranet.groupebpce.fr/generativeAI/v2/texts",
            "prod": "https://api.ai.intranet.groupebpce.fr/generativeAI/v2/texts",
            "dev": "https://api.ai.uat.intranet.groupebpce.fr/generativeAI/v2/texts",
        }

        if "env" not in st.session_state:
            st.session_state.env = "dev" # os.environ.get("ENV")  # ----------------------------------> Check with the server later

        self.username = os.environ.get("genai-api-user-id")
        self.password = os.environ.get("genai-api-user-secret")

    def get_access_token(self, url: str) -> Union[str, None]:
        """
        Get access token needed to reach model API endpoints.
        
        Args:
            url (str): The URL of the OAuth2 token endpoint.

        Returns:
            str: The access token if the request is successful, None otherwise.
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {USERNAME}:{PASSWORD}".format(USERNAME=self.username, PASSWORD=self.password),
            "Accept": "application/json",
        }
        data = {"grant_type": "client_credentials"}
        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=data,
                auth=HTTPBasicAuth(self.username, self.password),
                verify=False,
            )
            response.raise_for_status()
            access_token = str(response.json().get("access_token"))
            return access_token
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 401:
                raise http_err
            else:
                print(f"HTTP error: {http_err}")
                print(traceback.format_exc())
                raise http_err
        except requests.exceptions.SSLError as ssl_err:
            print(f"SSL error: {ssl_err}")
            print(traceback.format_exc())
            raise ssl_err
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            raise e


    def check_token_validity(self, access_token: str) -> tuple[str, str]:
        """
        Validates the given access token by making a request to the OAuth2 token endpoint.

        Args:
            access_token (str): The access token to be validated.

        Returns:
            str: The original access token if it is valid, otherwise a new access token.
            str: The environment for which the access token is valid.
        """
        if st.session_state.env == "":
            chosen_env = list(self.URL_GET_TOKENS.keys())[0]
            for env, url in self.URL_GET_TOKENS.items():
                try:
                    st.session_state.logger.info(f"Checking token validity for environment: {env}")
                    if self.get_access_token(url):
                        chosen_env = env
                        break
                    else:
                        st.session_state.logger.error(f"Failed to check token validity for environment: {env} : {url}")
                        continue
                except Exception as e:
                    st.session_state.logger.error(e)
                    continue

            st.session_state.logger.info(f"This is chosen env >>>> {chosen_env}")
            st.session_state.env = chosen_env
        else:
            chosen_env = st.session_state.env

        headers = {"Authorization": "Bearer " + access_token}
        response = requests.get(self.URL_GET_TOKENS[chosen_env], headers=headers, verify=False)

        if response.status_code == 200:
            pass
        else:
            access_token = str(self.get_access_token(self.URL_GET_TOKENS[chosen_env]))

        return access_token, chosen_env

    # @st.cache_data(show_spinner=False)
    def get_cached_api_response(self, url: str, _headers: dict[str, str], json: dict[str, Any]) -> requests.Response:
        """
        Sends a POST request to the specified URL with the given headers and JSON payload.
        This is a cached Streamlit function.

        Args:
            url (str): The URL to which the POST request is sent.
            _headers (dict): A dictionary of HTTP headers to include in the request.
            json (dict): A dictionary representing the JSON payload to include in the request.

        Returns:
            requests.Response: The response object resulting from the POST request.
        """
        return requests.post(url, headers=_headers, json=json, verify=False)

    def generate_answer(
        self,
        access_token: str = "B26qqQ3zzvqWU18UH7fOeneR1SSEkPo5uL3yXNnuIVXK1mFYo83cZg",
        modelID: str = "gpt-4o-2024-05-13",
        context: str = "",
        messages: list[dict[str, Any]] = [{"author": "USER", "contents": [{"text": ""}]}],
        topP: float = 0.0,
        temperature: float = 0.0,
        maxCandidates: int = 1,
        outputMaxTokens: int = 200,
        stopSequences: list[str] = ["[STOP]", "[END]"],
        outputFormat: str = "TEXT",  # "JSON" or "TEXT"
    ) -> Any:
        """
        Generates an answer using a generative AI model.

        Args:
            access_token (str): The access token for authentication.
            modelID (str): The ID of the model to use.
            context (str): The context or system instructions for the model.
            messages (list): The list of messages to provide as input.
            topP (float): The top-p sampling parameter.
            temperature (float): The temperature parameter for creativity.
            maxCandidates (int): The maximum number of candidates to generate.
            outputMaxTokens (int): The maximum number of tokens in the output.
            stopSequences (list): The sequences at which to stop generation.
            outputFormat (str): The format of the output, either "TEXT" or "JSON".

        Returns:
            list: A list of generated candidates.
        """
        
        access_token, chosen_env = self.check_token_validity(access_token)

        url = self.URL_IA_ENDPOINTS[chosen_env]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "modelId": modelID,
            "input": {"messages": messages, "systemInstructions": [{"text": context}]},
            "generationConfig": {
                "topP": topP,
                "temperature": temperature,
                "maxCandidates": maxCandidates,
                "outputMaxTokens": outputMaxTokens,
                "stopSequences": stopSequences,
                "outputFormat": outputFormat,
            },
        }

        try:
            if "make_cached_api_call" not in st.session_state:
                st.session_state.make_cached_api_call = True
                # ->>>>>>>>>>>>>>>>>>>>>>>>>>>>>> self.get_cached_api_response.clear()  # Clear cached data

            response = self.get_cached_api_response(url=url, _headers=headers, json=payload)
            return response.json().get("candidates")  # type: ignore
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error: {http_err}")
            print(traceback.format_exc())
            return []
        except requests.exceptions.SSLError as ssl_err:
            print(f"SSL error: {ssl_err}")
            print(traceback.format_exc())
            return []
        except Exception as err:
            print(f"Error: {err}")
            print(traceback.format_exc())
            return []

    # @st.cache_data(show_spinner=False)
    def get_llm_response(
        self,
        user_prompt: str,
        context_prompt: str = "",
        modelID: str = "gpt-4o-mini-2024-07-18",
        temperature: float = 0.0,
        outputMaxTokens: int = 1000,
        outputFormat: str = "TEXT",  # "JSON" or "TEXT"
    ) -> str:
        """
        Generates a response from a language model based on the provided user prompt and context.

        Args:
            user_prompt (str): The main prompt provided by the user.
            context_prompt (str): Additional context to provide to the model.
            modelID (str): The ID of the model to use.
            temperature (float): Temperature level for creativity.
            outputMaxTokens (int): The maximum number of tokens to generate in the response.

        Returns:
            str: The generated response from the language model.
        """
        messages = [{"author": "USER", "contents": [{"text": user_prompt}]}]

        response = "TOTO"
        
        try:
            response = self.generate_answer(
                modelID=modelID,
                messages=messages,
                context=context_prompt,
                temperature=temperature,
                outputMaxTokens=outputMaxTokens,
                outputFormat=outputFormat,
            )[0]["text"]
        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            st.error(
                "We're sorry, but there seems to be a problem retrieving the response from the API. Please try again later.",
                icon="🚨",
            )
            response = "We're sorry, but there seems to be a problem retrieving the response from the API. Please try again later."

        return str(response)

    def list_all_models(self, access_token: str = ""):
        """
        List all available models from the generative AI API.

        Returns:
            list: A list of all available models.
        """
        access_token, _ = self.check_token_validity(access_token)

        url = "https://api.ai.uat.intranet.groupebpce.fr/generativeAI/v2/models"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        res = json.dumps(
            requests.get(url, headers=headers, verify=False).json(),
            indent=4,
            sort_keys=True,
        )

        return res


if __name__ == "__main__":
    # Example usage
    llm_connector = LLMConnector()
    print(llm_connector.list_all_models())
    # Optionally test generating a response
    response = llm_connector.get_llm_response(user_prompt="What is the capital of France?")
    print(response)
