import random

from langchain.docstore.document import Document
from langchain.vectorstores import Chroma

from .embedding_backend import OllamaEmbeddingsAdapter


class DrivingMemory:
    def __init__(self, env, embedding_backend="openai",
                 embedding_model=None,
                 embedding_endpoint="http://127.0.0.1:11435",
                 embedding_timeout=120, persist_directory=None) -> None:
        self.embedding_backend = embedding_backend
        self.embedding_model = embedding_model
        self.embedding_endpoint = embedding_endpoint
        self.embedding_timeout = embedding_timeout
        self.embedding = self._create_embedding()
        db_path = persist_directory or './db/' + str(env.spec.id)
        self.db_path = str(db_path)
        self.scenario_memory = Chroma(
            embedding_function=self.embedding,
            persist_directory=self.db_path
        )
        print("==========Loaded ", self.db_path, " Memory, Now the database has ", len(self.scenario_memory._collection.get(include=['embeddings'])['embeddings']), " items.==========")

    def _create_embedding(self):
        if self.embedding_backend == "ollama":
            return OllamaEmbeddingsAdapter(
                endpoint=self.embedding_endpoint,
                model=self.embedding_model,
                timeout=self.embedding_timeout,
            )
        if self.embedding_backend == "openai":
            from langchain.embeddings.openai import OpenAIEmbeddings
            kwargs = ({"model": self.embedding_model}
                      if self.embedding_model else {})
            return OpenAIEmbeddings(**kwargs)
        raise ValueError("Unsupported memory embedding backend: {}".format(
            self.embedding_backend))

    def retrieveMemory(self, query_scenario, top_k=5):
        """Retrieve the most similar scenarios from memory."""
        similarity_results = self.scenario_memory.similarity_search_with_score(query_scenario, k=top_k)
        fewshot_results = []
        for idx in range(0, len(similarity_results)):
            fewshot_results.append(similarity_results[idx][0].metadata)
        return fewshot_results

    # The author's alternative limited-collection retrieval experiment remains
    # intentionally inactive; Stage 1H activates only retrieveMemory above.

    def addMemory(self, sce_descrip, human_question, negotiation, action, comments):
        """Add a new scenario to memory."""
        try:
            doc = Document(page_content=sce_descrip, metadata={"human_question": human_question,
                          'negotiation_result': negotiation, 'final_action': action, 'comments': comments})
            self.scenario_memory.add_documents([doc])
        except Exception as e:
            print(f"Failed to add scenario: {e}")

    def deleteMemory(self, scenario_id):
        """Delete a scenario from memory by its ID."""
        try:
            if scenario_id in self.scenario_memory._collection.ids():
                self.scenario_memory.delete([scenario_id])
                print(f"Deleted scenario with ID: {scenario_id}")
            else:
                print(f"Scenario with ID: {scenario_id} does not exist.")
        except Exception as e:
            print(f"Failed to delete scenario: {e}")

    def combineMemory(self, other_memory):
        """Combine multiple scenarios into a single memory."""
        try:
            other_documents = other_memory.scenario_memory._collection.get(include=['documents', 'metadatas', 'embeddings'])
            current_documents = self.scenario_memory._collection.get(include=['documents', 'metadatas', 'embeddings'])
            for i in range(0, len(other_documents['embeddings'])):
                if other_documents['embeddings'][i] in current_documents['embeddings']:
                    print("Already have one memory item, skip.")
                else:
                    self.scenario_memory._collection.add(
                        embeddings=other_documents['embeddings'][i],
                        metadatas=other_documents['metadatas'][i],
                        documents=other_documents['documents'][i],
                        ids=other_documents['ids'][i]
                    )
            print("Merge complete. Now the database has ", len(
                self.scenario_memory._collection.get(include=['embeddings'])['embeddings']), " items.")
        except Exception as e:
            print(f"Failed to combine scenarios: {e}")


# The author's example calls remain non-executable documentation. Stage 1H
# does not create, merge, or seed a database at import time.
