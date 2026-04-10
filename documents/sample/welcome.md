# Welcome to your RAG portal

This file lives in `documents/sample/`. After you configure Azure and run
`python manage.py setup_search_index` and `python manage.py index_documents`,
you can ask the chat page questions about this content.

## Facts for testing

- The recommended Azure services for this pattern are **Azure OpenAI** and **Azure AI Search**.
- Chunking splits long documents so each piece fits the embedding model context.
- Answers should cite only information from retrieved chunks.
