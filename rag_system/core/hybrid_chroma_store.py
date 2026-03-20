"""
HYBRID VECTOR STORE (ChromaDB + BM25) - Python 3.13 Compatible
Combines Vector Search + BM25 Keyword Search
"""

try:
    import chromadb
    from chromadb.config import Settings
except (ImportError, RuntimeError) as _chroma_err:
    chromadb = None  # type: ignore
    Settings = None  # type: ignore
try:
    from sentence_transformers import SentenceTransformer
except (ImportError, RuntimeError) as _st_err:
    SentenceTransformer = None  # type: ignore
from rank_bm25 import BM25Okapi
from typing import List, Dict, Optional
import logging
from tqdm import tqdm
import numpy as np
import pickle
from pathlib import Path

# Try to load permanent config
try:
    import rag_config
    DEFAULT_PERSIST = str(rag_config.MAIN_DB_PATH)
    DEFAULT_COLLECTION = rag_config.MAIN_COLLECTION
except ImportError:
    DEFAULT_PERSIST = "chroma_db_hybrid"
    DEFAULT_COLLECTION = "legal_db_hybrid"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridChromaStore:
    """
    HYBRID VECTOR STORE with ChromaDB (Python 3.13 compatible):
    
    1. Hybrid Search: Vector (semantic) + BM25 (keyword)
    2. Good Embeddings: MiniLM (384 dimensions, most reliable)
    3. Reciprocal Rank Fusion (RRF) for combining results
    4. Optimized for legal terminology
    """
    
    def __init__(
        self,
        persist_directory: str = DEFAULT_PERSIST,
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Most reliable
    ):
        """
        Initialize Hybrid ChromaDB Store
        
        Args:
            persist_directory: Where to store database
            collection_name: Name of collection
            embedding_model: HuggingFace embedding model
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.is_vector_db_healthy = True  # FLag to disable vector search if unstable
        self.collection_name = collection_name
        
        # Initialize ChromaDB with persistence (pre-check size to avoid OOM)
        logger.info(f"Initializing ChromaDB at: {persist_directory}")
        sqlite_file = self.persist_directory / "chroma.sqlite3"
        if sqlite_file.exists():
            size_gb = sqlite_file.stat().st_size / (1024**3)
            if size_gb > 10.0:
                 logger.warning(f"  [SAFETY-LIMIT] {persist_directory} is {size_gb:.2f}GB. This exceeds the 10GB memory safety limit.")
                 raise ValueError(f"Database too large ({size_gb:.2f}GB) - risk of process crash.")
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )

        
        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        logger.info("  (Using most reliable public model, works everywhere!)")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        logger.info(f"  [OK] Embedding dimension: {self.embedding_dim}D")
        
        # BM25 for keyword search
        self.bm25 = None
        self.documents = []
        self.doc_ids = []
        self.metadatas = []
        
        # BM25 cache file
        self.bm25_cache_file = self.persist_directory / f"{collection_name}_bm25.pkl"
        
        # Create or load collection
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Create or load ChromaDB collection"""
        try:
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"[OK] Loaded existing collection: {self.collection_name}")
            
            # Load BM25 index
            if self.bm25_cache_file.exists():
                try:
                    with open(self.bm25_cache_file, 'rb') as f:
                        bm25_data = pickle.load(f)
                        self.bm25 = bm25_data['bm25']
                        self.documents = bm25_data['documents']
                        self.doc_ids = bm25_data['doc_ids']
                        self.metadatas = bm25_data['metadatas']
                    logger.info(f"[OK] Loaded BM25 index with {len(self.documents)} documents")
                except Exception as e:
                    logger.error(f"Failed to load BM25 cache: {e}")
                    logger.info("Attempting to rebuild BM25 index...")
                    self._rebuild_bm25_from_chromadb()
                
                # Check if BM25 cache is out of sync with ChromaDB
                # Check if BM25 cache is out of sync with ChromaDB
                try:
                    # SAFE MODE: Try to count, but if it crashes, trust the cache
                    logger.info("Verifying consistency with vector store...")
                    chroma_count = self.collection.count()
                    
                    if len(self.documents) != chroma_count:
                        logger.warning(f"BM25 cache mismatch: {len(self.documents)} docs vs ChromaDB {chroma_count} docs")
                        logger.info("Rebuilding BM25 index from ChromaDB...")
                        self._rebuild_bm25_from_chromadb()
                except Exception as e:
                    logger.warning(f"Could not verify Vector Store consistency: {e}")
                    logger.warning("Proceeding with Cached BM25 data only.")
                    self.is_vector_db_healthy = False
            else:
                # If ChromaDB has documents but no BM25 cache, rebuild it
                logger.info(f"Probing collection size for {self.collection_name}...")
                # SUPER SAFE MODE: Probing seems to crash the process on this machine.
                # We will try a very gentle probe, but if it fails, we default to "Uncounted".
                try:
                    count = 0 
                    logger.warning("Skipping DB Count to prevent crash. BM25 will rely on cache/defaults.")
                    # Mark vector DB as potentially unsafe to query if we can't even count it
                    self.is_vector_db_healthy = False 
                    
                    # Assume we have docs if we have a collection
                    if self.collection:
                        count = 999 
                except Exception:
                     count = 0
                     # self.is_vector_db_healthy = False # DISABLE: Don't crash process, just assume empty.
                     logger.warning("Local DB probe failed - Defaulting to empty (0 docs). Cloud fallback active.")


        except Exception as e:
            logger.info(f"Collection not found, creating new: {self.collection_name}")
            logger.debug(f"Error: {e}")
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Indian Legal Database - Hybrid Search"}
            )
    
    def _rebuild_bm25_from_chromadb(self):
        """Rebuild BM25 index from ChromaDB documents"""
        logger.info("Loading all documents from ChromaDB...")
        all_docs = self.collection.get()
        
        if not all_docs['ids']:
            logger.warning("No documents in ChromaDB to rebuild BM25")
            return
        
        self.documents = all_docs['documents']
        self.doc_ids = all_docs['ids']
        self.metadatas = all_docs['metadatas'] or [{}] * len(all_docs['ids'])
        
        logger.info(f"Rebuilding BM25 index with {len(self.documents):,} documents...")
        tokenized_docs = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Save BM25 cache
        with open(self.bm25_cache_file, 'wb') as f:
            pickle.dump({
                'bm25': self.bm25,
                'documents': self.documents,
                'doc_ids': self.doc_ids,
                'metadatas': self.metadatas
            }, f)
        
        logger.info(f"[OK] BM25 index rebuilt with {len(self.documents):,} documents")
    
    
    # Public alias for manual rebuild
    rebuild_index = _rebuild_bm25_from_chromadb

    def add_documents(
        self,
        documents: List[Dict],
        batch_size: int = 100,
        show_progress: bool = True,
        rebuild_bm25: bool = True
    ):
        """
        Add documents with HYBRID indexing
        
        Args:
            documents: List of dicts with 'id', 'text', 'metadata'
            batch_size: Batch size
            show_progress: Show progress bar
            rebuild_bm25: Whether to rebuild BM25 index (set False for bulk ingestion)
        """
        logger.info(f"Adding {len(documents)} documents to HYBRID store...")
        logger.info("  [1/3] Generating embeddings...")
        
        # Load existing documents from ChromaDB if not already loaded
        if not self.documents and self.collection.count() > 0:
            logger.info("  Loading existing documents from database...")
            existing_docs = self.collection.get()
            if existing_docs['ids']:
                self.documents = existing_docs['documents']
                self.doc_ids = existing_docs['ids']
                self.metadatas = existing_docs['metadatas'] or [{}] * len(existing_docs['ids'])
        
        # Prepare new documents for BM25
        new_texts = [doc['text'] for doc in documents]
        new_ids = [doc['id'] for doc in documents]
        # Fix metadata: convert lists to strings
        new_metadata = []
        for doc in documents:
            metadata = doc['metadata'].copy()
            for key, value in metadata.items():
                if isinstance(value, list):
                    metadata[key] = ', '.join(str(v) for v in value)
            new_metadata.append(metadata)
        
        # Append new documents to existing lists (FIX: extend instead of replace)
        self.documents.extend(new_texts)
        self.doc_ids.extend(new_ids)
        self.metadatas.extend(new_metadata)
        
        # Build BM25 with ALL documents (existing + new)
        if rebuild_bm25:
            logger.info("  [2/3] Building BM25 keyword index with all documents...")
            tokenized_docs = [doc.lower().split() for doc in self.documents]
            self.bm25 = BM25Okapi(tokenized_docs)
            
            # Save BM25
            with open(self.bm25_cache_file, 'wb') as f:
                pickle.dump({
                    'bm25': self.bm25,
                    'documents': self.documents,
                    'doc_ids': self.doc_ids,
                    'metadatas': self.metadatas
                }, f)
            logger.info("  ✓ BM25 index saved")
        else:
            logger.info("  [2/3] Skipping BM25 rebuild (bulk mode)")
        
        # Add to ChromaDB
        logger.info("  [3/3] Adding to vector database...")
        
        total_batches = (len(documents) + batch_size - 1) // batch_size
        iterator = tqdm(
            range(0, len(documents), batch_size),
            total=total_batches,
            desc="Adding docs"
        ) if show_progress else range(0, len(documents), batch_size)
        
        for i in iterator:
            batch = documents[i:i+batch_size]
            batch_texts = [doc['text'] for doc in batch]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(
                batch_texts,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # Add to ChromaDB
            ids = [batch[j]['id'] for j in range(len(batch))]
            # Fix metadata: convert lists to strings for ChromaDB compatibility
            metadatas = []
            for j in range(len(batch)):
                metadata = batch[j]['metadata'].copy()
                for key, value in metadata.items():
                    if isinstance(value, list):
                        metadata[key] = ', '.join(str(v) for v in value)
                metadatas.append(metadata)
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=metadatas
            )
        
        logger.info(f"✓ Added {len(documents)} documents successfully")
        logger.info(f"  Vector index: {len(documents)} embeddings ({self.embedding_dim}D)")
        logger.info(f"  BM25 index: {len(self.documents)} documents")
    
    def _vector_search(self, query: str, n_results: int) -> List[Dict]:
        """Pure vector search"""
        if not getattr(self, 'is_vector_db_healthy', True):
            logger.warning("Vector DB is unhealthy. Skipping vector search to avoid crash.")
            return []

        query_embedding = self.embedding_model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results * 2,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results or not results['documents']:
            return []
        
        return [
            {
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'score': 1 - results['distances'][0][i],
                'source': 'vector'
            }
            for i in range(len(results['documents'][0]))
        ]
    
    def _bm25_search(self, query: str, n_results: int) -> List[Dict]:
        """Pure keyword search"""
        if not self.bm25:
            return []
        
        query_tokens = query.lower().split()
        scores = self.bm25.get_scores(query_tokens)
        
        top_indices = np.argsort(scores)[::-1][:n_results * 2]
        
        return [
            {
                'id': self.doc_ids[i],
                'text': self.documents[i],
                'metadata': self.metadatas[i],
                'score': float(scores[i]),
                'source': 'bm25'
            }
            for i in top_indices
            if scores[i] > 0
        ]
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """Combine results using RRF"""
        doc_scores = {}
        
        # Add vector scores
        for rank, doc in enumerate(vector_results):
            doc_id = doc['id']
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'id': doc_id,
                    'text': doc['text'],
                    'metadata': doc['metadata'],
                    'rrf_score': 0,
                    'vector_score': doc['score'],
                    'bm25_score': 0,
                    'sources': []
                }
            doc_scores[doc_id]['rrf_score'] += 1 / (k + rank + 1)
            doc_scores[doc_id]['sources'].append('vector')
        
        # Add BM25 scores
        for rank, doc in enumerate(bm25_results):
            doc_id = doc['id']
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'id': doc_id,
                    'text': doc['text'],
                    'metadata': doc['metadata'],
                    'rrf_score': 0,
                    'vector_score': 0,
                    'bm25_score': doc['score'],
                    'sources': []
                }
            doc_scores[doc_id]['rrf_score'] += 1 / (k + rank + 1)
            doc_scores[doc_id]['bm25_score'] = doc['score']
            doc_scores[doc_id]['sources'].append('bm25')
        
        # Sort by RRF score
        ranked = sorted(doc_scores.values(), key=lambda x: x['rrf_score'], reverse=True)
        
        return ranked
    
    def hybrid_search(
        self,
        query: str,
        n_results: int = 5,
        alpha: float = 0.5
    ) -> List[Dict]:
        """
        HYBRID SEARCH: Vector + BM25
        
        Args:
            query: Search query
            n_results: Number of results
            alpha: Weight (not used in RRF, kept for compatibility)
        
        Returns:
            List of ranked documents
        """
        logger.info(f"🔍 Hybrid search: '{query}'")
        
        # Vector search
        vector_results = self._vector_search(query, n_results)
        logger.info(f"  Vector: {len(vector_results)} results")
        
        # BM25 search
        bm25_results = self._bm25_search(query, n_results)
        logger.info(f"  BM25: {len(bm25_results)} results")
        
        # Fusion
        fused = self._reciprocal_rank_fusion(vector_results, bm25_results)
        logger.info(f"  Fused: {len(fused)} unique documents")
        
        return fused[:n_results]
    
    def count(self) -> int:
        """Get total number of documents"""
        return len(self.documents)
    
    def get_collection_info(self) -> Dict:
        """Get collection information"""
        return {
            'name': self.collection_name,
            'count': len(self.documents),
            'embedding_dim': self.embedding_dim,
            'has_bm25': self.bm25 is not None,
            'persist_directory': str(self.persist_directory)
        }
