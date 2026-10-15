def compute_relevance_text(q, index):
    id = q["id"]
    results = index.search(q["question"])

    relevance = []
    for result in results:
        relevance.append(int(result["id"] == id))

    return relevance

def compute_relevance_metric(ground_truth, index):
    relevances = []
    for q in ground_truth:
        relevance = compute_relevance_text(q, index)
        relevances.append(relevance)

    return relevances

def hit_rate(relevances):
    cnt = 0
    for relevance in relevances:
        if 1 in relevance:
            cnt = cnt + 1
    return cnt / len(relevances)

def mrr(relevances):
    cnt = 0.0
    for relevance in relevances:
        for rank in range(len(relevance)):
            if relevance[rank] == 1:
                cnt = cnt + 1 / (rank + 1)

    return cnt / len(relevances)

        