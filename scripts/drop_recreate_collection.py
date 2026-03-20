"""Drop old Zilliz collection (dim=384) so it gets recreated with dim=2048"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import connections, utility, Collection
import rag_config

connections.connect(
    alias="default",
    uri=rag_config.ZILLIZ_CLUSTER_ENDPOINT,
    token=rag_config.ZILLIZ_TOKEN
)

name = rag_config.ZILLIZ_COLLECTION_NAME
print(f"Collection: {name}")

if utility.has_collection(name):
    col = Collection(name)
    for f in col.schema.fields:
        dim = getattr(f, 'params', {}).get('dim', None)
        print(f"  Field: {f.name}, dtype={f.dtype}, dim={dim}")
    print("\nDropping old collection (wrong dim)...")
    utility.drop_collection(name)
    print("Done! Collection dropped.")
    print("It will be recreated with dim=2048 when upload_to_zilliz_now.py runs.")
else:
    print("Collection does not exist - nothing to drop.")
