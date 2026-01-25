# Adapter Interface Protocol

Never access adapters directly. Always access storage, models, and vector stores through protocol interfaces in `rentl-core`.

```python
# ✓ Good: Access through protocol interface
from rentl_core.adapters.vector import VectorStoreProtocol

async def search_context(query: str, vector_store: VectorStoreProtocol):
    """Search vector context via protocol - implementation agnostic."""
    return await vector_store.search(query)

# ✗ Bad: Direct access to implementation
import chromadb

async def search_context(query: str):
    """Search vector context - hardcoded to Chroma."""
    client = chromadb.Client()
    collection = client.get_collection("context")
    return collection.query(query)
```

**Adapter protocols in `rentl-core`:**
- `rentl_core.adapters.vector.VectorStoreProtocol` - Vector storage and retrieval
- `rentl_core.adapters.model.ModelClientProtocol` - LLM model integration
- `rentl_core.adapters.storage.StorageProtocol` - Run metadata and artifact storage

**Default implementations (never accessed directly from surfaces):**
- `rentl_core.adapters.vector.chroma_store.ChromaVectorStore`
- `rentl_core.adapters.model.openai_client.OpenAIClient`
- `rentl_core.adapters.storage.sqlite_index.SQLiteIndex`

**Access pattern:**
1. Define protocol interface in `rentl_core.adapters.*`
2. Provide default implementation behind interface
3. Inject protocol dependency (or resolve from factory in core)
4. Use only protocol methods - never concrete class

**Why:** Enables swapping implementations (Chroma → pgvector, OpenAI → local models) without changing client code, makes testing easier with mock protocols, and ensures consistent behavior across all surface layers.
