import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from slack_sdk.errors import SlackApiError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


# Initialize Slack Bolt App with tokens
app = App(token=os.environ.get("SLACK_BOT_TOKEN"),
          signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))

# --- Configure Ollama ---
model_name = os.environ.get("OLLAMA_MODEL")
if not model_name:
    raise ValueError("Please set OLLAMA_MODEL environment variable.")

try:
    # Initialize Ollama with proper error handling
    llm = OllamaLLM(
        model=model_name,
        base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        temperature=0.7,
    )
    # Test the connection
    print(f"Testing connection to Ollama with model {model_name}...")
    test_response = llm("test")
    print("Successfully connected to Ollama")
except Exception as e:
    print(f"Error initializing Ollama: {e}")
    raise

# --- Configure Langchain Prompt and Chain ---
chat_prompt_template = """
    You are a helpful chatbot. Answer the following question based on your general knowledge:

    Question: {question}
    Answer:
"""

summarize_prompt_template = """
    You are a helpful assistant that summarizes Slack conversations. Create a clear and concise summary of the following conversation.
    Focus on the main points, decisions, and action items if any.

    Conversation:
    {messages}

    Summary:
"""

chat_prompt = PromptTemplate(template=chat_prompt_template, input_variables=["question"])
summarize_prompt = PromptTemplate(template=summarize_prompt_template, input_variables=["messages"])

chat_chain = chat_prompt | llm
summarize_chain = summarize_prompt | llm

def get_thread_messages(client, channel_id, thread_ts):
    """Fetch all messages in a thread."""
    try:
        logger.info(f"Fetching thread messages for channel: {channel_id}, thread_ts: {thread_ts}")
        
        # Get thread replies
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            inclusive=True  # Include the parent message
        )
        
        if not result["ok"]:
            logger.error(f"Error fetching replies: {result}")
            return None
            
        logger.info(f"Found {len(result['messages'])} messages in thread")
        
        # Format messages into a readable conversation
        formatted_messages = []
        for msg in result["messages"]:
            try:
                # Get user info - handle the case where we don't have users:read scope
                try:
                    user_info = client.users_info(user=msg["user"])
                    if user_info["ok"]:
                        username = user_info["user"]["real_name"]
                    else:
                        username = f"User-{msg['user']}"
                except SlackApiError as e:
                    if "missing_scope" in str(e):
                        username = f"User-{msg['user']}"
                    else:
                        raise
                
                # Clean up message text (remove mentions)
                text = msg["text"]
                # Replace user mentions with generic user references if we can't get user info
                for item in msg.get("blocks", []):
                    if item["type"] == "rich_text":
                        for element in item["elements"]:
                            if element["type"] == "rich_text_section":
                                for mention in element["elements"]:
                                    if mention["type"] == "user":
                                        user_id = mention["user_id"]
                                        try:
                                            user_info = client.users_info(user=user_id)
                                            if user_info["ok"]:
                                                mention_name = user_info["user"]["real_name"]
                                            else:
                                                mention_name = f"User-{user_id}"
                                        except SlackApiError as e:
                                            if "missing_scope" in str(e):
                                                mention_name = f"User-{user_id}"
                                            else:
                                                raise
                                        text = text.replace(f"<@{user_id}>", f"@{mention_name}")
                
                formatted_messages.append(f"{username}: {text}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Still include the message even if we can't get user info
                formatted_messages.append(f"Unknown User: {msg.get('text', 'No text available')}")
                continue
        
        thread_text = "\n".join(formatted_messages)
        logger.info(f"Formatted thread text: {thread_text}")
        return thread_text
        
    except SlackApiError as e:
        logger.error(f"Slack API Error: {e.response.get('error', str(e))}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_thread_messages: {e}")
        return None

def clean_message_text(text):
    """Remove mentions and clean up message text."""
    # Remove any <@USER_ID> mentions from the text
    import re
    text = re.sub(r'<@[A-Z0-9]+>', '', text)
    # Remove extra whitespace
    text = ' '.join(text.strip().split())
    return text

@app.event("app_mention")
def handle_mention(body, say, client, logger):
    """Handles mentions of the bot in Slack."""
    try:
        text = body['event']['text']
        user = body['event']['user']
        channel = body['event']['channel']
        event_ts = body['event']['ts']
        thread_ts = body['event'].get('thread_ts', event_ts)  # Use event_ts if no thread_ts
        
        # Clean and normalize the message text
        cleaned_text = clean_message_text(text).lower()
        logger.info(f"Cleaned message text: {cleaned_text}")
        
        # Check if this is a request for thread summary
        if any(cmd in cleaned_text for cmd in ['summarize thread', 'sumarize thread', 'thread summary']):
            logger.info("Thread summary requested")
            
            # Determine if this should be a private summary
            is_private = 'private' in cleaned_text or 'me only' in cleaned_text
            
            # Get the thread messages
            thread_messages = get_thread_messages(client, channel, thread_ts)
            
            if thread_messages:
                logger.info("Successfully retrieved thread messages, generating summary...")
                # Create a more specific prompt for the summary
                summary_input = {
                    "messages": (
                        "Please summarize the following Slack conversation, "
                        "focusing on key points, decisions, and action items:\n\n" +
                        thread_messages
                    )
                }
                response = summarize_chain.invoke(summary_input)
                
                # Format the response
                formatted_response = (
                    "*Thread Summary:*\n\n"
                    f"{response}\n\n"
                    "_Note: This summary was generated using AI and may not be perfect._"
                )
                
                if is_private:
                    # Send as ephemeral message using client.chat_postEphemeral
                    try:
                        client.chat_postEphemeral(
                            channel=channel,
                            user=user,
                            text=formatted_response,
                            thread_ts=thread_ts
                        )
                    except SlackApiError as e:
                        logger.error(f"Error posting ephemeral message: {e}")
                        say(text="I encountered an error sending you a private message. Please check my permissions.", 
                            thread_ts=event_ts)
                else:
                    # Send as regular thread reply (visible to everyone)
                    say(text=formatted_response, thread_ts=event_ts)
            else:
                error_msg = (
                    "I couldn't fetch the thread messages. This might be because:\n"
                    "1. I don't have permission to access the channel history\n"
                    "2. The thread is too old or has been deleted\n"
                    "3. There was an error connecting to Slack\n\n"
                    "Please make sure I have the necessary permissions and try again."
                )
                # Send error message with same visibility as request
                if is_private:
                    try:
                        client.chat_postEphemeral(
                            channel=channel,
                            user=user,
                            text=error_msg,
                            thread_ts=thread_ts
                        )
                    except SlackApiError as e:
                        logger.error(f"Error posting ephemeral message: {e}")
                        say(text="I encountered an error sending you a private message. Please check my permissions.", 
                            thread_ts=event_ts)
                else:
                    say(text=error_msg, thread_ts=event_ts)
        else:
            # Regular chat response
            response = chat_chain.invoke({"question": cleaned_text})
            if response:
                say(text=response, thread_ts=event_ts)
            else:
                say(text="I couldn't generate a response. Please try rephrasing your question.",
                    thread_ts=event_ts)

    except KeyError as ke:
        logger.error(f"KeyError: {ke}. This might be due to unexpected message structure.")
        logger.error(f"Message body: {body}")
        say(text="I encountered an error processing your message. Please try again.", thread_ts=body['event']['ts'])
    except Exception as exp:
        logger.error(f"An error occurred: {exp}")
        logger.error(f"Full error details: {str(exp)}")
        logger.error(f"Message body: {body}")
        say(text="I encountered an unexpected error. Please try again later.", thread_ts=body['event']['ts'])


if __name__ == "__main__":
    try:
        handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        print("Starting the app...")
        handler.start()
    except Exception as e:
        print(f"Error starting app: {e}")
        print(f"Full error details: {str(e)}")
