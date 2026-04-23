import asyncio
import os
import glob
import traceback
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from unstructured.partition.auto import partition
from config.config import config
#logger
from loguru import logger



# scan all files in the filepath

CHROMA_PERSIST_DIR = "chroma_vector_db"

class DocHandler:
    def __init__(self):
        self.chunk_size = 2000
        self.chunk_overlap = 50
        self.top_k = 3
        self.embedding_model_name = ''
        self.api_key = config.embedding_api_key
        self.base_url = config.embedding_base_url
        self.embeddings = self._init_embedding_model()
        self.vector_db:Chroma = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings
        )

    def read_doc(self) -> List[Document]:
    # read documents form specific file path
        documents = []
        base_path = 'doc'
        files = glob.glob(os.path.join(base_path,'**'),recursive=True)
        file_path = [f for f in files if os.path.isfile(f)]
        logger.info('reading files...')
        for file in file_path:
                try:
                    filename = os.path.basename(file)
                    elements = partition(filename=file)
                    content = '\n'.join(str(el) for el in elements)
                    doc = Document(
                        page_content = content,
                        metadata = {
                        "filename": filename,
                        "source": file,
                        "file_type": os.path.splitext(filename)[-1]
                        }
                    )
                    documents.append(doc)
                except Exception as e:
                    logger.warning(f'read file failed,file = {filename},error = {str(e)}')
                    continue
        return documents
    
    def spilt_document(self,documents) -> List[Document]:
    # spilt doc into numerous chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = text_splitter.split_documents(documents)
        logger.debug(f'chunk completed,len = {len(chunks)}')
        return chunks
    
    async def save(self,split_docs:List[Document]) -> None:
        batch = []
        pending_tasks = []
        semaphore = asyncio.Semaphore(10)
        async def flush_batch(b):
            if not b:
                return
            async with semaphore:
                try:
                # 同步方法 → 放入线程池
                    await asyncio.to_thread(self.vector_db.add_documents, b)
                    logger.info(f"succeeded, {len(batch)} docs")
                except Exception as e:
                    logger.error(f"failed: {e}")
        # load embedding model
        if not split_docs:
            logger.error('no docs included')
            return 
        valid_docs = []
        for doc in split_docs:
            content = doc.page_content
            if not content or not content.strip():
                logger.warning(f"Empty content, skipping doc: {doc.metadata.get('filename', 'unknown')}")
                continue
            if len(content) > self.chunk_size:
                logger.warning(f"Content too long ({len(content)} chars), truncating to {self.chunk_size}")
                doc.page_content = content[:self.chunk_size]
            valid_docs.append(doc)
            if not valid_docs:
                logger.error('No valid docs after filtering')
                continue
            batch.append(doc)
            if len(batch) >= 20:
                pending_tasks.append(flush_batch(batch))
                batch = []
                # 控制并发任务数量，避免任务列表无限增长
                if len(pending_tasks) >= 10:
                    await asyncio.gather(*pending_tasks)
                    pending_tasks.clear()
        if batch:
            pending_tasks.append(flush_batch(batch))
        if pending_tasks:
            await asyncio.gather(*pending_tasks)
            
        logger.success('successfully saved to database')
        
    async def retrive_document(self,query:str,top_k:int) -> List[Document]:
        #read metadata from database
        if not query:
            logger.warning('query not set')
            return []
        try:
            doc = await self.vector_db.asimilarity_search(query=query,k = top_k)
            logger.success(f'searched {len(doc)}')
        except Exception as e:
            logger.error(f'search doc error = {str(e)}')
            doc = []
        return doc
    
    def _init_embedding_model(self) -> OpenAIEmbeddings:
        # initialize embedding model
        logger.success(f'import embedding model = {self.base_url}')
        return OpenAIEmbeddings(
            base_url=self.base_url,
            api_key= self.api_key,
            model="BAAI/bge-m3"

        )
    async def store_doc(self):
        try:
            docs = doc_handler.read_doc()
            doc_list = doc_handler.spilt_document(docs)
            await doc_handler.save(doc_list)
            #doc_handler.save([test])
            logger.success('SUCCESSFULLY SAVED DOC')
        except Exception as e:
            logger.error(f'error:{str(e)}\n traceback = {traceback.format_exc()}')



doc_handler = DocHandler()
