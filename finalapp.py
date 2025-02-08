# finalapp.py
import streamlit as st
import json
from tools import tool_functions
from dataclasses import dataclass
from typing import List, Dict, Optional
from groq import Groq
import logging
from datetime import datetime
from pathlib import Path
from memory import Memory
from context import ContextManager
from tools.tools import tools
from tools.parser import parse_tool_response
from models.config_loader import ConfigLoader

# Initialize memory and context
memory = Memory()
context_manager = ContextManager()

class ChatBot:
    def __init__(self, api_key: str, config):
        self.client = Groq(api_key=api_key)
        self.conversation_history = []
        self.config = config
        self.tools = tools
    
    def process_message(self, user_message: str) -> str:
        self.conversation_history.append({"role": "user", "content": user_message})
        
        try:
            completion = self.client.chat.completions.create(
                model=self.config.get_config("model_config")["model"],
                messages=[{"role": "user", "content": user_message}],
                tools=self.tools,
                tool_choice="auto"
            )
            response_message = completion.choices[0].message
            print(str(response_message))
            # If there are tool calls, execute them
            if response_message.tool_calls:
                tool_responses = self._handle_tool_calls(response_message.tool_calls)
                print(tool_responses)
                return tool_responses
            
            return response_message.content
        
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return "I encountered an issue processing your request. Please try again."
    
    def _handle_tool_calls(self, tool_calls: list) -> str:
        """Dynamically call tools and return response."""
        tool_responses = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            for tool in self.tools:
                if tool["function"]["name"] == tool_name:
                    tool_function = getattr(tool_functions, tool_name, None)
                    if callable(tool_function):
                        tool_responses.append(tool_function(**tool_args))
                    else:
                        tool_responses.append(f"Tool {tool_name} is not implemented.")
        
        return "\n".join(tool_responses) if tool_responses else "Tool execution complete."


def main():
    st.set_page_config(
        page_title="GreenLife Foods Assistant",
        page_icon="🌱",
        layout="wide"
    )
    
    config_loader = ConfigLoader()
    config_loader.load_all_configs()
    ui_config = config_loader.get_config("ui_config")

    # Apply styling
    st.markdown(f"""
    <style>
    .stTextInput > div > div > input {{
        background-color: {ui_config["colors"]["background"]};
        border-color: {ui_config["colors"]["secondary"]};
    }}
    .stButton > button {{
        background-color: {ui_config["colors"]["primary"]};
        color: white;
        border-radius: {ui_config["spacing"]["border_radius"]};
    }}
    .chat-message {{
        padding: {ui_config["spacing"]["chat_padding"]};
        border-radius: {ui_config["spacing"]["border_radius"]};
        margin-bottom: {ui_config["spacing"]["message_margin"]};
        background-color: {ui_config["colors"]["background"]};
    }}
    * {{
        font-family: {ui_config["fonts"]["primary"]}, sans-serif;
    }}
    .main {{
        padding: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.title("🌱 GreenLife Foods Assistant")

    # Initialize session state
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = ChatBot(st.secrets["GROQ_API_KEY"], config_loader)
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = st.session_state.chatbot.process_message(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

if __name__ == "__main__":
    main()