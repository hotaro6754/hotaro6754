"""Deterministic synthetic WhatsApp exports for tests and demos.

The generated conversations are entirely fictional. They exist so that the
parser, analytics and UI can be developed without anyone's real messages.

Usage::

    python -m openmirror.synthetic --layout android --out sample.txt
    python -m openmirror.synthetic --layout ios --zip --out sample.zip
"""

from __future__ import annotations

import argparse
import io
import random
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class SynthMessage:
    sender: str | None  # None = system notice
    ts: datetime
    text: str


TOPICS = {
    "trip": [
        "Did you check the train tickets for the Goa trip?",
        "Goa trip budget is looking tight, maybe we skip the cruise",
        "Booked the homestay in Goa! Check-in is at noon",
        "What should we pack for the trip? Sunscreen for sure",
        "The trip photos are still on my laptop, will send",
    ],
    "exam": [
        "Exam schedule is out, the first paper is on Monday",
        "I haven't even started the syllabus for the exam",
        "How did your exam go?",
        "Exam hall was freezing today",
    ],
    "project": [
        "The project deadline moved to Friday",
        "Can you review my project report tonight?",
        "Project demo went well, the professor liked the dashboard",
        "Pushing the project code now, check the repo",
        "Stuck on the database part of the project",
    ],
    "cricket": [
        "Did you watch the cricket match last night?",
        "That last over in the cricket match was unreal",
        "Cricket at the ground on Sunday morning?",
    ],
    "food": [
        "Biryani at the usual place tonight?",
        "That biryani was overrated honestly",
        "Ordering biryani, want some?",
        "Chai break?",
    ],
    "movie": [
        "New movie releases this Friday, want to go?",
        "The movie was way too long",
        "Movie tickets booked for the 7pm show",
    ],
}

SMALL_TALK = [
    "haha",
    "ok",
    "yes",
    "nope",
    "sure",
    "lol 😂",
    "same",
    "Good morning!",
    "Good night 🌙",
    "what are you doing?",
    "sorry, was busy",
    "call me when you're free",
    "on my way",
    "reached",
    "👍",
    "true",
    "ya ya",
    "where are you?",
    "omg",
    "thanks!",
]

REPLIES = [
    "yes, makes sense",
    "hmm let me think",
    "definitely",
    "not sure about that",
    "haha true",
    "ok done",
    "will check and tell you",
    "agreed",
    "really? 😮",
    "that's great!",
]


def _pick_topic(rng: random.Random, weights: dict[str, float]) -> str:
    names = list(weights)
    return rng.choices(names, weights=[weights[n] for n in names])[0]


def generate_two_person(seed: int = 7) -> list[SynthMessage]:
    """A 14-month fictional chat between Asha and Ravi with three phases.

    * Jan–Jun 2023: frequent conversations, Asha starts most of them.
    * Jul–Sep 2023: volume drops, including a ~3-week silence in August.
    * Oct 2023–Feb 2024: recovery, Ravi starts most conversations.
    """
    rng = random.Random(seed)
    people = ("Asha", "Ravi")
    msgs: list[SynthMessage] = [
        SynthMessage(
            None,
            datetime(2023, 1, 2, 9, 0),
            "Messages and calls are end-to-end encrypted. No one outside of this chat, not even "
            "WhatsApp, can read or listen to them. Tap to learn more.",
        )
    ]
    day = datetime(2023, 1, 2)
    end = datetime(2024, 2, 28)
    cursor = msgs[0].ts
    while day <= end:
        month = (day.year - 2023) * 12 + day.month
        if month <= 6:
            p_session, starter_bias, topic_w = 0.85, 0.68, {"exam": 3, "project": 2, "trip": 1, "food": 2, "cricket": 1, "movie": 1}
        elif month <= 9:
            p_session, starter_bias, topic_w = 0.30, 0.5, {"project": 3, "exam": 1, "food": 1, "cricket": 1, "movie": 1, "trip": 0.2}
        else:
            p_session, starter_bias, topic_w = 0.75, 0.3, {"trip": 4, "food": 2, "movie": 2, "cricket": 1, "project": 1, "exam": 0.2}
        if datetime(2023, 8, 3) <= day <= datetime(2023, 8, 24):
            p_session = 0.0  # the silent stretch
        sessions = 0
        if rng.random() < p_session:
            sessions = 1 + (rng.random() < 0.35)
        for s in range(sessions):
            hour = rng.choice([8, 9, 13, 18, 20, 21, 22, 23]) if s == 0 else rng.choice([21, 22, 23])
            t = day.replace(hour=hour, minute=rng.randint(0, 59))
            # Keep the transcript chronological, as real exports are.
            t = max(t, cursor + timedelta(hours=5))
            starter = people[0] if rng.random() < starter_bias else people[1]
            other = people[1] if starter == people[0] else people[0]
            topic = _pick_topic(rng, topic_w)
            turns = rng.randint(3, 14)
            speaker = starter
            for turn in range(turns):
                burst = 1 + (rng.random() < (0.45 if speaker == "Asha" else 0.2))
                for b in range(burst):
                    if turn == 0 and b == 0:
                        text = rng.choice(TOPICS[topic])
                    elif rng.random() < 0.35:
                        text = rng.choice(TOPICS[topic])
                    elif rng.random() < 0.5:
                        text = rng.choice(REPLIES)
                    else:
                        text = rng.choice(SMALL_TALK)
                    r = rng.random()
                    if r < 0.03:
                        text = "<Media omitted>"
                    elif r < 0.04:
                        text = "This message was deleted"
                    elif r < 0.06 and speaker == "Asha":
                        text = text + "\nAlso, " + rng.choice(TOPICS[topic]).lower() + "\nlet me know"
                    elif r < 0.07:
                        text = text + " <This message was edited>"
                    msgs.append(SynthMessage(speaker, t, text))
                    t += timedelta(seconds=rng.randint(5, 50))
                # Ravi is quick early on and slower in the middle phase.
                if speaker == "Ravi":
                    delay = rng.expovariate(1 / 240)
                else:
                    delay = rng.expovariate(1 / (90 if month <= 6 else 900 if month <= 9 else 180))
                t += timedelta(seconds=int(30 + delay))
                speaker = other if speaker == starter else starter
            cursor = t
        day += timedelta(days=1)
    return msgs


def generate_group(seed: int = 11) -> list[SynthMessage]:
    """A short fictional group chat with system notices and four members."""
    rng = random.Random(seed)
    members = ["Meera", "Kiran", "Dev", "Farah"]
    t = datetime(2024, 3, 1, 10, 0)
    msgs = [
        SynthMessage(None, t, 'Meera created group "Weekend Plans"'),
        SynthMessage(None, t + timedelta(minutes=1), "Meera added Kiran"),
        SynthMessage(None, t + timedelta(minutes=1), "Meera added Dev"),
        SynthMessage(None, t + timedelta(minutes=2), "Meera added Farah"),
    ]
    t += timedelta(minutes=5)
    for _ in range(160):
        who = rng.choices(members, weights=[4, 3, 2, 1])[0]
        text = rng.choice(TOPICS[rng.choice(list(TOPICS))] + SMALL_TALK)
        msgs.append(SynthMessage(who, t, text))
        t += timedelta(minutes=rng.randint(1, 600))
    msgs.append(SynthMessage(None, t, 'Kiran changed the subject from "Weekend Plans" to "Re: Goa"'))
    msgs.append(SynthMessage(None, t + timedelta(minutes=3), "Farah left"))
    return msgs


def _fmt_android(ts: datetime, date_style: str, h12: bool) -> str:
    if date_style == "DMY":
        date = ts.strftime("%d/%m/%Y")
    elif date_style == "MDY":
        date = f"{ts.month}/{ts.day}/{ts:%y}"
    else:
        date = ts.strftime("%d.%m.%y")
    if h12:
        hour = ts.hour % 12 or 12
        time = f"{hour}:{ts:%M} {'PM' if ts.hour >= 12 else 'AM'}"
    else:
        time = ts.strftime("%H:%M")
    return f"{date}, {time}"


def render_android(msgs: list[SynthMessage], date_style: str = "DMY", h12: bool = False) -> str:
    out = []
    for m in msgs:
        head = _fmt_android(m.ts, date_style, h12)
        out.append(f"{head} - {m.text}" if m.sender is None else f"{head} - {m.sender}: {m.text}")
    return "\n".join(out) + "\n"


_IOS_MEDIA = {"<Media omitted>": "‎image omitted"}


def render_ios(msgs: list[SynthMessage], chat_name: str = "Ravi", h12: bool = True) -> str:
    out = []
    for m in msgs:
        if h12:
            hour = m.ts.hour % 12 or 12
            time = f"{hour}:{m.ts:%M:%S} {'PM' if m.ts.hour >= 12 else 'AM'}"
            date = f"{m.ts.month}/{m.ts.day}/{m.ts:%y}"
        else:
            time = m.ts.strftime("%H:%M:%S")
            date = m.ts.strftime("%d/%m/%Y")
        text = _IOS_MEDIA.get(m.text, m.text)
        if text == "This message was deleted":
            text = "‎This message was deleted."
        if text.endswith(" <This message was edited>"):
            text = text.replace(" <This message was edited>", " ‎<This message was edited>")
        if m.sender is None:
            out.append(f"‎[{date}, {time}] {chat_name}: ‎{text}")
        else:
            prefix = "‎" if text.startswith("‎") else ""
            out.append(f"{prefix}[{date}, {time}] {m.sender}: {text}")
    return "\r\n".join(out) + "\r\n"


def write_zip(path: Path, chat_text: str, member: str = "_chat.txt") -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member, chat_text.encode("utf-8"))
        zf.writestr("00000012-PHOTO-2023-03-01-21-15-03.jpg", b"\xff\xd8\xff\xe0 synthetic")
    path.write_bytes(buf.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a fictional WhatsApp export.")
    parser.add_argument("--layout", choices=["android", "ios"], default="android")
    parser.add_argument("--kind", choices=["pair", "group"], default="pair")
    parser.add_argument("--date-style", choices=["DMY", "MDY", "DOT"], default="DMY")
    parser.add_argument("--h12", action="store_true")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    msgs = generate_two_person() if args.kind == "pair" else generate_group()
    if args.layout == "android":
        text = render_android(msgs, args.date_style, args.h12)
    else:
        text = render_ios(msgs, h12=args.h12)
    if args.zip:
        write_zip(args.out, text)
    else:
        args.out.write_text(text, encoding="utf-8")
    print(f"wrote {len(msgs)} fictional messages to {args.out}")


if __name__ == "__main__":
    main()
