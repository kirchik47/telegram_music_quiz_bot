from abc import ABC, abstractmethod

class AiohttpServiceInterface(ABC):
    @abstractmethod
    async def get(self, url: str, headers: dict = None, params: dict = None) -> dict:
        """
        Sends an asynchronous GET request to the given URL with optional headers and query parameters.

        :param url: The URL to send the GET request to
        :param headers: Optional dictionary of headers to include in the request
        :param params: Optional dictionary of query parameters to include in the request
        :return: The response in JSON format as a dictionary
        """
        pass

    @abstractmethod
    async def post(self, url: str, payload: dict) -> dict:
        """
        Sends an asynchronous POST request to the given URL with the provided payload.

        :param url: The URL to send the POST request to
        :param payload: The JSON payload to send in the POST request
        :return: The response in JSON format as a dictionary
        """
        pass
