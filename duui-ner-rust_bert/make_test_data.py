import json
import random

random.seed(42)

utf8_lens = False

if utf8_lens:
    newline_len = len("\n".encode())
else:
    newline_len = 1


def format(sub, utf8_lens=False):
    jsn = {"text": "\n".join(sub), "language": "de", "sentences": []}
    last = 0
    for sent in sub:
        if utf8_lens:
            sent_len = len(sent.encode())
        else:
            sent_len = len(sent)
        jsn["sentences"].append({"begin": last, "end": last + sent_len})
        last += sent_len + newline_len
    return jsn


if __name__ == "__main__":
    data = [
        l.strip()
        for l in open(
            "/hot_storage/Data/Leipzig/deu/deu_wikipedia_2016_10K-formatted.txt",
            encoding="utf-8",
        ).readlines()
    ]
    random.shuffle(data)

    # data = json.load(open("data/broken.json", encoding="utf-8"))["text"].split("\n")

    # with open(f"data/test_broken.json", "w", encoding="utf-8") as fp:
    #     json.dump(format(data, utf8_lens=utf8_lens), fp, ensure_ascii=False)

    step = 500
    for start, end in zip(
        range(0, len(data) + 1, step), range(step, len(data) + 1, step)
    ):
        sub = data[start:end]
        jsn = format(sub, utf8_lens=utf8_lens)

        with open(f"data/test_split_{start//step}.json", "w", encoding="utf-8") as fp:
            json.dump(jsn, fp, ensure_ascii=False)
