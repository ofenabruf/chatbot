import time
import streamlit as st
from openai import OpenAI

ASSISTANT_ID = "asst_u3LOqVkIQNe0KjxToHj8tKoG"

st.title("💬 Chatbot (Assistants API)")
st.write(
    "Dieses Demo nutzt einen vordefinierten OpenAI Assistant über die Assistants API. "
    "Gib deinen OpenAI API Key ein, um loszulegen."
)

openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Bitte füge deinen OpenAI API Key ein, um fortzufahren.", icon="🗝️")
    st.stop()

# OpenAI Client
client = OpenAI(api_key=openai_api_key)

# Session-State initialisieren
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    # Neuen Thread anlegen und merken
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# Bisherige Chat-Nachrichten anzeigen
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat-Eingabe
if prompt := st.chat_input("Was möchtest du fragen?"):
    # 1) Lokal anzeigen
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Nachricht in den Assistant-Thread posten
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
    )

    # 3) Run starten (nutzt deinen bestehenden Assistant)
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=ASSISTANT_ID,
    )

    # 4) Auf Abschluss warten (einfaches Polling)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        spinner_text = "Assistent denkt nach …"
        with st.spinner(spinner_text):
            status = run.status
            while status in ("queued", "in_progress", "requires_action"):
                time.sleep(0.6)
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id,
                )
                status = run.status

        # 5) Nach Abschluss: letzte Assistant-Antwort aus dem Thread holen
        if status == "completed":
            msgs = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id,
                order="desc",  # neueste zuerst
                limit=10
            )

            # Erstes Assistant-Message-Item finden
            assistant_text = None
            for m in msgs.data:
                if m.role == "assistant":
                    # Inhalte zusammensetzen (nur Textteile)
                    parts = []
                    for c in m.content:
                        if c.type == "text":
                            parts.append(c.text.value)
                    assistant_text = "\n".join(parts).strip() if parts else ""
                    if assistant_text:
                        break

            if not assistant_text:
                assistant_text = "_(Keine Text-Antwort gefunden – evtl. Tool-Ausgabe oder leere Nachricht.)_"

            placeholder.markdown(assistant_text)
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})

        else:
            # Fehler-/Sonderfälle anzeigen
            error_msg = f"Run beendet mit Status: **{status}**"
            if getattr(run, "last_error", None):
                error_msg += f"\n\nFehler: `{run.last_error}`"
            placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
