import os
import sys
# Add project root to path so we can import 'app' package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
from app.tools.search.embedder import generate_embeddings

print(asyncio.run(generate_embeddings(request_id="011PR", texts=["what is python "])))
    