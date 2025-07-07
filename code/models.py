from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain.embeddings.base import Embeddings
from typing import Any, Dict, List, Optional
import os
from pydantic import BaseModel, root_validator
class SiliconFlowLLM(LLM):
    """A custom chat model for SiliconFlow."""

    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    base_url: str = "https://api.siliconflow.cn/v1"
    token: Optional[str] = None
    client: Any = None

    def __init__(self):
        super().__init__()
        print("Initializing model...")
        from openai import OpenAI
        self.token = os.getenv("OPENAI_API_KEY")
        if not self.token:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(
            api_key=self.token,
            base_url=self.base_url
        )
        print("Model initialization complete")

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Run the LLM on the given input."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "你是航天器测试专家"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.7,
            response_format={"type": "text"},
        )
        return response.choices[0].message.content

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return a dictionary of identifying parameters."""
        return {"model_name": self.model_name}

    @property
    def _llm_type(self) -> str:
        """Get the type of language model used by this chat model."""
        return "SiliconFlow"
# 以下为embedding模型


class SiliconFlowEmbeddings(BaseModel, Embeddings):
    """`SiliconFlow Embeddings` embedding models."""

    openai_api_key: Optional[str] = None
    model_name: str = "BAAI/bge-m3"

    @root_validator(skip_on_failure=True)
    def validate_environment(cls, values: Dict) -> Dict:
        values["openai_api_key"] = values.get("openai_api_key") or os.getenv(
            "OPENAI_API_KEY"
        )
        if not values["openai_api_key"]:
            raise ValueError("OpenAI API key not found")
        try:
            from openai import OpenAI
            values["client"] = OpenAI(
                api_key=values["openai_api_key"],
                base_url="https://api.siliconflow.cn/v1"
            )
        except ImportError:
            raise ValueError(
                "OpenAI package not found, please install it with `pip install openai`"
            )
        return values

    def _embed(self, texts: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

    def embed_query(self, text: str) -> List[float]:
        resp = self.embed_documents([text])
        return resp[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]