from data_ingest import load_knowledge_data

documents = load_knowledge_data()

def match_section(section, documents):
    section_topic = []
    for d in documents:
        if d["章节"] == section:
            section_topic.append({"主题": d["主题"], "id": d["知识点id"]})

    return section_topic

def match_topic(section_topic, topic):
    knowledge = []
    for t in section_topic:
        if t["主题"] == topic:
            knowledge.append(t["id"])

    return knowledge

def get_knowledge(knowledge, documents):
    knowledge_content = []
    for kn in knowledge:
        for d in documents:
            if d["知识点id"] == kn:
                knowledge_content.append(d)

    return knowledge_content