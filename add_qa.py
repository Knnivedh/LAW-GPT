import json

file_path = 'C:/Users/LOQ/Downloads/LAW-GPT_new/LAW-GPT_new/LAW-GPT/kaanoon_test/kaanoon_qa_expanded.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_entries = [
    {
        "question": "What is IPC Section 302?",
        "answer": "Section 302 of the Indian Penal Code (IPC) prescribes the punishment for murder. It states: 'Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.'"
    },
    {
        "question": "What is IPC Section 304A?",
        "answer": "Section 304A of the Indian Penal Code (IPC) deals with causing death by negligence. It states: 'Whoever causes the death of any person by doing any rash or negligent act not amounting to culpable homicide, shall be punished with imprisonment of either description for a term which may extend to two years, or with fine, or with both.'"
    }
]

if isinstance(data, list):
    data.extend(new_entries)

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print("Updated kaanoon_qa_expanded.json successfully.")
