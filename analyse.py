import collections
import json
import os
import random
import re
import sys
import time
from datetime import datetime

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


def markov_generate_message(data):
    message = ""

    # regexp start and end string characters used to indicate start and end of
    # message
    word = "^"
    while word != "$":
        if word not in ".,":
            message += " "
        message += word

        word_list = list(data[word])
        prob_dist = list(data[word].values())

        word = random.choices(population=word_list, weights=prob_dist, k=1)[0]

    return message[3:].capitalize()


def markov_chain(messages, outdir):
    # { name: { word: { following_word: 0 } } }
    data = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(lambda: 0)
        )
    )
    pattern = re.compile(r"[a-z\'\-]+|[.,]+")
    for m in messages:
        prev = "^"
        for word in re.findall(pattern, m["content"].lower()):
            data[m["sender_name"]][prev][word] += 1
            prev = word
        data[m["sender_name"]][prev]["$"] += 1

    generated = {}
    for name in data:
        generated[name] = [
            markov_generate_message(data[name]) for _ in range(10)
        ]

    with open(os.path.join(outdir, "markov_messages.json"), "w") as f:
        json.dump(generated, f, indent=4)


def kick_counts(messages, outdir):
    # {person: n}
    kicked = collections.defaultdict(lambda: 0)
    for m in messages:
        if "content" in m and "users" in m:
            if m["content"].endswith("from the group."):
                name = m["users"][0]["name"]
                kicked[name] += 1

    plot_pie_chart_with_values(kicked)
    plt.title("Times Kicked")
    plt.savefig(os.path.join(outdir, "proportion_kicked.png"))


# Check for plain text messages only
def garbage_message(m):
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
        " to your message "
    ]

    return any(phrase in text for phrase in chat_action_phrases)


def good_message(m):
    return not garbage_message(m)


def get_messages_and_participants(input_dir):
    files = [f for f in os.listdir(input_dir) if f.endswith(".json") and f.startswith("message_")]
    messages = []
    participants = set()

    for f in files:
        file_path = os.path.join(input_dir, f)

        with open(file_path, "rb") as file:
            raw = file.read()
            raw = raw.replace(b"\u00e2\u0080\u0099", b"'")
            data = json.loads(raw.decode(encoding="utf-8"))

            messages.extend(data.get("messages", []))

            for participant in data["participants"]:
                participants.add(participant["name"])

    return messages, participants

def save_nicknames(messages, participants, input_dir, outdir):
    nicknames = {}

    def append_nickname(person, nickname_entry):
        if person not in nicknames:
            nicknames[person] = []

        nicknames[person].append(nickname_entry)

    def append_output(output, nickname_entries):
        longest_standing_nickname = None
        longest_standing_days = 0
        longest_standing_start_date = None
        longest_standing_end_date = None

        for i in range(len(nickname_entries) - 1):
            current_entry = nickname_entries[i]
            next_entry = nickname_entries[i + 1]
            current_timestamp = current_entry["timestamp"]
            next_timestamp = next_entry["timestamp"]
            days_diff = (next_timestamp - current_timestamp) // (1000 * 60 * 60 * 24)

            if days_diff > longest_standing_days:
                longest_standing_nickname = current_entry["nickname"]
                longest_standing_days = days_diff
                longest_standing_start_date = timestamp_to_date(int(current_entry["timestamp"]))
                longest_standing_end_date = timestamp_to_date(int(next_entry["timestamp"]))

        if nickname_entries:
            final_entry = nickname_entries[-1]
            final_timestamp = final_entry["timestamp"]
            final_nickname = final_entry["nickname"]
            final_start_date = timestamp_to_date(int(final_timestamp))
            current_date = datetime.now().strftime("%d/%m/%Y")
            final_duration = (datetime.now() - datetime.fromtimestamp(int(final_timestamp) / 1000)).days

            if final_duration > longest_standing_days:
                longest_standing_nickname = final_nickname
                longest_standing_days = final_duration
                longest_standing_start_date = final_start_date
                longest_standing_end_date = current_date

        if longest_standing_nickname:
            output += f"Longest Standing Nickname: {longest_standing_nickname} " \
                      f"({longest_standing_days} days, from {longest_standing_start_date} " \
                      f"to {longest_standing_end_date})\n"

        for entry in nickname_entries:
            timestamp = entry["timestamp"]
            nickname = entry["nickname"]
            date_str = timestamp_to_date(int(timestamp))

            output += f"{date_str} - {nickname.rstrip('.')}\n"

        output += "\n"

        return output

    for message in messages:
        content = message.get("content", "")
        timestamp = message.get("timestamp_ms", 0)

        if "set the nickname for" in content:
            parts = content.split(" set the nickname for ")
            nickname_parts = parts[1].split(" to ")
            person = nickname_parts[0]
            nickname = " ".join(nickname_parts[1:])
            nickname_entry = {
                "timestamp": timestamp,
                "nickname": nickname
            }

            append_nickname(person, nickname_entry)
            participants.discard(person)

        elif "set your nickname to" in content:
            parts = content.split("set your nickname to")
            if len(parts) == 2:
                nickname = parts[1].strip(".")
                nickname_entry = {
                    "timestamp": timestamp,
                    "nickname": nickname
                }

                append_nickname("owner", nickname_entry)

    owner = None
    owner_entries = []

    if len(participants) == 1:
        owner = participants.pop()

    if owner:
        owner_entries = nicknames.get("owner", [])
        owner_entries = sorted(owner_entries, key=lambda x: x["timestamp"])

    output = ""

    if owner:
        output += f"{owner} ({len(owner_entries)} nicknames):\n"
        output = append_output(output, owner_entries)

    for person, entries in nicknames.items():
        if person == "owner" or person == owner:
            continue

        entries = sorted(entries, key=lambda x: x["timestamp"])
        count = len(entries)
        output += f"{person} ({count} nicknames):\n"
        output = append_output(output, entries)

    with open(os.path.join(outdir, f"{os.path.basename(input_dir)}_nicknames.txt"), "w", encoding="utf-8", errors="replace") as file:
        file.write(output)

def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp / 1000).strftime("%d/%m/%Y")


def main():
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    else:
        input_dir = os.path.dirname(__file__)

    all_messages, participants = get_messages_and_participants(input_dir)
    good_messages = list(filter(good_message, all_messages))

    outdir = "out"

    if os.path.exists(outdir):
        if not os.path.isdir(outdir):
            print('Output directory "out" exists and is not a directory.')
            exit(1)
    else:
        os.makedirs(outdir)
        with open(os.path.join(outdir, ".gitignore")) as f:
            f.write("*")
        
    plt.style.use("dark_background")

    outputs = [
        monthly_line,
        pie_chart,
        pie_chart_words,
        words_per_message,
        stackplot,
        markov_chain,
    ]

    for f in outputs:
        new_fig()
        f(good_messages, outdir)

    kick_counts(all_messages, outdir)

    save_nicknames(all_messages, participants, input_dir, outdir)


if __name__ == "__main__":
    main()
