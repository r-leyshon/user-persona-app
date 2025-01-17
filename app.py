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
    ui.panel_title("Experiment with User Personas"),
    ui.div(
        ui.row(
            ui.div(
                ui.input_text_area(
                    id=f"user_txt",
                    label="",
                    placeholder="Type your prompt here then submit..."
                    ),
                ui.input_action_button(
                    id=f"submit_btn",
                    label="Submit",
                    style="margin-top:0px;margin-bottom:15px;"
                    ),
                class_="d-flex gap-2",
            ),
            ),
    style="position: sticky; top: 0px; z-index: 1000; background: white;",
    ),
    ui.row(
        *[ui.column(4, ui.chat_ui(id=f"chat{i}", placeholder="Chat appears above ^")) for i in range(0, 3)]
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

    # Define a callback to run when the user submits a message
    # @chat.on_user_submit

    @reactive.Effect
    @reactive.event(input.submit_btn)
    async def respond():
        """Logic for handling prompts & appending to chat stream."""
        usr_prompt = input.user_txt()

        stream0.append({"role": "user", "content": input.user_txt()})
        stream1.append({"role": "user", "content": input.user_txt()})
        stream2.append({"role": "user", "content": input.user_txt()})
        await chat0.append_message_stream(input.user_txt())
        await chat1.append_message_stream(input.user_txt())
        await chat2.append_message_stream(input.user_txt())

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
        await chat0.append_message_stream(response0)
        await chat1.append_message_stream(response1)
        await chat2.append_message_stream(response2)

app = App(app_ui, server)
