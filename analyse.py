import collections
import json
import os
import time

import matplotlib.pyplot as plt
from wordcloud import WordCloud

def new_fig():
    plt.figure(figsize=(8, 6), dpi=360)


def cumulative(messages, outdir):
    timeblocks = [] 
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
    for m in messages:
        timestamp = m.get("timestamp_ms")
        name = m.get("sender_name")

        if not (timestamp and name):
            continue

        timestamp //= 1000
        timeblock = time.strftime("%b %y", time.gmtime(timestamp))

        if not timeblock in timeblocks:
            timeblocks.append(timeblock)

        data[name][timeblock] += 1

    timeblocks = sorted(
        timeblocks,
        key=lambda k: time.mktime(time.strptime(k, "%b %y"))
    )

    names = sorted(data.keys())
    ys = [[data[name][timeblock] for timeblock in timeblocks] for name in names]

    plt.stackplot(timeblocks, *ys, labels=names, antialiased=True)
    plt.legend(loc="upper left")
    plt.xticks(rotation=90)
    plt.tight_layout()
    
    plt.savefig(os.path.join(outdir, "cumulative.png"))

def count_by_person(messages):
    data = collections.defaultdict(lambda: 0)
    for m in messages:
        name = m.get("sender_name")
        if not name:
            continue

        data[name] += 1

    return data


def bar_graph(messages, outdir):
    data = count_by_person(messages)
    i = range(len(data))
    plt.barh(i, list(data.values()))
    plt.yticks(i, list(data))
    plt.xlabel('Messages')
    plt.ylabel('Sender')
    plt.tight_layout()

    plt.savefig(os.path.join(outdir, "count.png"))

def pie_chart(messages, outdir):
    data = count_by_person(messages)

    # Sort by number of messages
    labels = sorted(data.keys(), key=lambda k: data[k])
    data = [data[name] for name in labels]
    *_, autotexts = plt.pie(data, labels=labels, autopct="")

    # Change labels to show the datapoint
    for i, a in enumerate(autotexts):
        a.set_text(str(data[i]))

    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "proportion.png"))


def wordcloud(messages, outdir):
    corpus = "\n".join([m.get("content") for m in messages])
    
    plt.figure(figsize=(24, 18), dpi=128)
    plt.imshow(WordCloud().generate(corpus))
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "wordcloud.png"))


# Check for plain text messages only
def garbage_message(m):
    if not m.get("type") == "Generic":
        return True
    
    text = m.get("content")
    if not text:
        return True

    chat_action_phrases = [
        " in the poll.",
        " created a poll: ",
        " responded with ", 
        " created the reminder: ",
        " created the group.",
        " created a plan.",
        " set the nickname for "
    ]

    return any(phrase in text for phrase in chat_action_phrases)
    

def good_message(m):
    return not garbage_message(m)


# Substitution of messenger's quote mark encoding doesn't work when not read
# as binary
with open("messages.json", "rb") as f:
    raw = f.read()
    raw = raw.replace(b"\u00e2\u0080\u0099", b"'")

    messages = json.loads(raw.decode(encoding="utf-8"))

messages = list(filter(good_message, messages))

OUTDIR = "out"

plt.style.use("dark_background")

outputs = [
    bar_graph,
    cumulative,
    pie_chart,
    wordcloud
]

for f in outputs:
    new_fig()
    f(messages, OUTDIR)
