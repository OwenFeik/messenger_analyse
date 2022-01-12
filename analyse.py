import collections
import json
import os
import sys
import time

import matplotlib.pyplot as plt
from wordcloud import WordCloud


def new_fig():
    plt.figure(figsize=(12, 9))


def stackplot(messages, outdir):
    # Wants for higher resolution to reduce aliasing
    plt.figure(figsize=(12, 9), dpi=360)

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
        timeblocks, key=lambda k: time.mktime(time.strptime(k, "%b %y"))
    )

    names = sorted(data.keys())
    ys = [[data[name][timeblock] for timeblock in timeblocks] for name in names]

    plt.stackplot(timeblocks, *ys, labels=names, antialiased=True)
    plt.legend(loc="upper left")
    plt.xticks(rotation=90)
    plt.tight_layout()

    plt.savefig(os.path.join(outdir, "stackplot.png"))


def count_by_month(messages):
    people = []
    data = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
    for m in messages:
        timestamp = m.get("timestamp_ms")
        name = m.get("sender_name")

        if not (timestamp and name):
            continue

        if not name in people:
            people.append(name)

        timestamp //= 1000
        timeblock = time.strftime("%b %y", time.gmtime(timestamp))

        data[timeblock][name] += 1

    return people, data


# A plot where each month has stacked bars to show the number of messages sent
# by each participant that month
def monthly_stacked_bar(messages, outdir):
    people, data = count_by_month(messages)

    ys = sorted(
        list(data), key=lambda k: time.mktime(time.strptime(k, "%b %y"))
    )

    n = len(ys)

    colours = []

    indexes = range(n)
    bottom = [0] * n
    for name in people:
        person_data = [data[y][name] for y in ys]
        colour = plt.barh(indexes, person_data, left=bottom)
        colours.append(colour)
        bottom = [bottom[i] + person_data[i] for i in indexes]

    plt.yticks(range(n), ys)
    plt.legend(colours, people)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "monthly_stacked_bar.png"))


def monthly_line(messages, outdir):
    people, data = count_by_month(messages)

    xs = sorted(
        list(data), key=lambda k: time.mktime(time.strptime(k, "%b %y"))
    )

    for name in people:
        plt.plot(xs, [data[x][name] for x in xs], label=name)
    plt.xticks(rotation=90)
    plt.ylabel("Messages Sent")
    plt.title("Messages by Month")
    plt.legend()
    plt.savefig(os.path.join(outdir, "monthly_lines.png"))


def count_by_person(messages):
    data = collections.defaultdict(lambda: 0)
    for m in messages:
        name = m.get("sender_name")
        if not name:
            continue

        data[name] += 1

    return data


def count_words_by_person(messages):
    data = collections.defaultdict(lambda: 0)
    for m in messages:
        name = m.get("sender_name")
        if not name:
            continue

        data[name] += len(m["content"].split())

    return data


def bar_graph(messages, outdir):
    data = count_by_person(messages)
    i = range(len(data))
    plt.barh(i, list(data.values()))
    plt.yticks(i, list(data))
    plt.xlabel("Messages")
    plt.ylabel("Sender")
    plt.tight_layout()

    plt.savefig(os.path.join(outdir, "count.png"))


def plot_pie_chart_with_values(data):
    labels = sorted(data.keys(), key=lambda k: data[k])
    data = [data[name] for name in labels]
    *_, autotexts = plt.pie(data, labels=labels, autopct="")

    # Change labels to show the datapoint
    for i, a in enumerate(autotexts):
        a.set_text(str(data[i]))


def pie_chart(messages, outdir):
    plot_pie_chart_with_values(count_by_person(messages))
    plt.title("Total Messages Sent")
    plt.savefig(os.path.join(outdir, "proportion.png"))


def pie_chart_words(messages, outdir):
    plot_pie_chart_with_values(count_words_by_person(messages))
    plt.title("Total Words Sent")
    plt.savefig(os.path.join(outdir, "proportion_words.png"))


def words_per_message(messages, outdir):
    message_count = count_by_person(messages)
    words_count = count_words_by_person(messages)

    words_per_message = {
        p: words_count[p] / message_count[p] for p in message_count
    }

    indexes = range(len(words_per_message))
    plt.bar(indexes, list(words_per_message.values()))
    plt.xticks(indexes, list(words_per_message), rotation=45)
    plt.xlabel("Sender")
    plt.ylabel("Words per Message")
    plt.tight_layout()
    plt.title("Words per Message")
    plt.savefig(os.path.join(outdir, "words_per_message.png"))


def wordcloud(messages, outdir):
    corpus = "\n".join([m["content"] for m in messages])

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
        " set the nickname for ",
    ]

    return any(phrase in text for phrase in chat_action_phrases)


def good_message(m):
    return not garbage_message(m)


def get_file_messages(fp):
    # Substitution of messenger's quote mark encoding doesn't work when not read
    # as binary
    with open(fp, "rb") as f:
        raw = f.read()
        raw = raw.replace(b"\u00e2\u0080\u0099", b"'")

        data = json.loads(raw.decode(encoding="utf-8"))

    return list(filter(good_message, data.get("messages", [])))


def get_folder_messages(input_dir):
    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    messages = []
    for f in files:
        messages.extend(get_file_messages(os.path.join(input_dir, f)))
    return messages


def main():
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    else:
        input_dir = os.path.dirname(__file__)

    messages = get_folder_messages(input_dir)

    OUTDIR = "out"

    plt.style.use("dark_background")

    outputs = [
        monthly_line,
        pie_chart,
        pie_chart_words,
        words_per_message,
        stackplot,
    ]

    for f in outputs:
        new_fig()
        f(messages, OUTDIR)


if __name__ == "__main__":
    main()
