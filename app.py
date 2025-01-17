from pathlib import Path
import random

from dotenv import dotenv_values
import openai
from pyprojroot import here
from shiny import App, reactive, render, ui

from scripts.personas import personas
# before ------------------------------------------------------------------
secrets = dotenv_values(here(".env"))
openai_key = secrets["OPENAI_KEY"]
openai_client = openai.AsyncOpenAI(api_key=openai_key)
SYS_PROMPT = """
You are a helpful assistant working with the user to identify user
requirements and to edit text according to those needs. The name and
persona that you should use follows in triple-backtick-delimiters:

name: ```{name}```
persona: ```{persona}```

Continue the conversation in this tone. If the user requests it, assist
them in adapting text to the requirements for this persona.
"""

stream0 = []
stream1 = []
stream2 = []
streams = [stream0, stream1, stream2]

for stream in streams:
    persona = random.choice(personas)
    # remove the chosen persona so that it only appears once
    for i, pers in enumerate(personas):
        if pers == persona:
            personas.pop(i)

    sys_prompt = SYS_PROMPT.format(
        name=persona.get("name"), persona=persona.get("persona")
        )
    stream.append({"role": "system", "content": sys_prompt})
    stream.append(
        {"role": "assistant", "content": persona.get("greeting")}
        )

# ui ----------------------------------------------------------------------
app_ui = ui.page_fillable(
    ui.div(
        ui.panel_title("Experiment with User Personas"),
        ui.row(
            ui.div(
                ui.input_text_area(
                    id="user_txt",
                    label="",
                    placeholder="Type your prompt here then submit..."
                    ),
                ui.input_action_button(
                    id="submit_btn",
                    label="Submit",
                    style="margin-top:0px;margin-bottom:15px;"
                    ),
                ui.input_action_button(
                    id="flush_chats",
                    label="Clear Chats",
                    style="margin-top:0px;margin-bottom:15px;"
                    ),
                class_="d-flex gap-2",
            ),
            ),
    style="position: fixed !important; top: 0px; z-index: 1000; background: white; width: 100%;",
    ),
    ui.row(
        *[ui.column(4, ui.chat_ui(id=f"chat{i}", placeholder="Chat appears above ^")) for i in range(0, 3)],
        style="margin-top: 100px;"
    ),
    ui.tags.script("""
        document.addEventListener('DOMContentLoaded', function() {
            for (let i = 0; i < 3; i++) {
                document.querySelector(`#chat${i} textarea`).setAttribute('disabled', 'true');
            }
        });
    """),
    fillable_mobile=True,
)

# server ------------------------------------------------------------------
def server(input, output, session):
    chat0 = ui.Chat(id="chat0", messages=stream0, tokenizer=None)
    chat1 = ui.Chat(id="chat1", messages=stream1, tokenizer=None)
    chat2 = ui.Chat(id="chat2", messages=stream2, tokenizer=None)
    chats = [chat0, chat1, chat2]

    @reactive.Effect
    @reactive.event(input.submit_btn)
    async def respond():
        """Logic for handling prompts & appending to chat stream."""
        usr_prompt = input.user_txt()
        [stream.append({"role": "user", "content": input.user_txt()}) for stream in streams]

        response0 = await openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=stream0,
            stream=True,
        )
        response1 = await openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=stream1,
            stream=True,
        )
        response2 = await openai_client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=stream2,
            stream=True,
        )
        responses = [response0, response1, response2]
        for i, chat in enumerate(chats):
            await chat.append_message_stream(responses[i])


    @reactive.Effect
    @reactive.event(input.flush_chats)
    async def clear_chats():
        """Erase all content from every chat stream"""
        chats = [chat0, chat1, chat2]
        streams = [stream0, stream1, stream2]
        for i, chat in enumerate(chats):
            await chat.clear_messages()
            streams[i] = streams[i][0:2]
            await chat.append_message(streams[i][-1])

app = App(app_ui, server)
