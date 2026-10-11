import streamlit as st
import asyncio

# Import your agent execution function from harness.py
from harness import run_mcp_agent

# Configure the Streamlit page
st.set_page_config(page_title="MCP Agent Interface", page_icon="🤖")
st.title("🤖 MCP + OpenAI Agent")

# 1. Initialize session state for standard OpenAI message history
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Display the existing conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. Handle new user input
if prompt := st.chat_input("Ask the agent something..."):
    
    # Append and display the user's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. Execute the agent and display the response
    with st.chat_message("assistant"):
        
        # Show a status spinner while the async agent runs
        with st.status("Agent is thinking and querying MCP servers...", expanded=True) as status:
            try:
                # Bridge Streamlit's sync environment with your async agent
                final_answer = asyncio.run(
                    run_mcp_agent(prompt, st.session_state.messages)
                )
                status.update(label="Task completed!", state="complete", expanded=False)
            except Exception as e:
                final_answer = f"An error occurred while running the agent: {e}"
                status.update(label="Error", state="error", expanded=False)
                
        # Display the final answer from the agent
        st.markdown(final_answer)
        
    # 5. Save the assistant's final response to memory
    st.session_state.messages.append({"role": "assistant", "content": final_answer})