import json
import os
from pathlib import Path

# Paths
kanoon_file = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA\kanoon.com\kanoon.com\kanoon_data.json")
legallyin_file = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA\legallyin.com\legallyin.com.json")
output_file = Path(r"c:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT\DATA\Consumer_QA_Harvest.json")

def harvest():
    consumer_docs = []
    
    # Harvest from Kanoon
    print("Harvesting from Kanoon...")
    if kanoon_file.exists():
        with open(kanoon_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                cat = str(item.get("query_category", "")).lower()
                if "consumer" in cat or "protection" in cat:
                    text = f"Category: {item.get('query_category')}\nQuestion: {item.get('query_text')}\nAnswer: {item.get('response_text')}"
                    consumer_docs.append({
                        "id": f"kanoon_{len(consumer_docs)}",
                        "title": item.get("query_title", "Consumer Query"),
                        "content": text,
                        "category": "Consumer Law",
                        "source": "Kaanoon.com"
                    })
    
    # Harvest from LegallyIn
    print("Harvesting from LegallyIn...")
    if legallyin_file.exists():
        with open(legallyin_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # data in legallyin.com.json might be different structure
            # Let's assume list of dicts based on the previous view_file (waiting for it)
            if isinstance(data, list):
                for item in data:
                    # Generic check
                    all_text = str(item).lower()
                    if "consumer protection" in all_text or "deficiency in service" in all_text:
                         consumer_docs.append({
                            "id": f"legallyin_{len(consumer_docs)}",
                            "title": item.get("title", "Consumer Article"),
                            "content": json.dumps(item), # Keep full context for now
                            "category": "Consumer Law",
                            "source": "LegallyIn.com"
                        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"documents": consumer_docs}, f, indent=4)
    
    print(f"DONE. Harvested {len(consumer_docs)} consumer documents to {output_file}")

if __name__ == "__main__":
    harvest()
