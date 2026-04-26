"""UI strings, model lists and asset paths used across the Streamlit app."""


class Streamlit:
    # Titles
    APP_TITLE = "Power BI Assistant"
    PAGE_TITLE = "AI Assistant - Power BI"
    SUBTITLE = "Your smart copilot for navigating Power BI reports"
    LOG_FILE_NAME = "app.log"

    # Inputs
    AI_QUERY = "💬 How can I help you?"
    PLACEHOLDER = (
        "E.g.: Show me the reports on consolidated balance sheet. "
        "Or: Where can I find the cash-flow forecast?"
    )
    ANALYSE = "Analysing the Power BI catalog…"

    # Sidebar
    PARAM = "Search mode:"
    MODE_LABEL = "Search mode"
    MODES = ["Smart search", "Data analysis (coming soon)"]
    MODEL_LABEL = "AI Model"
    IAS = "Choose an available AI model:"
    IA_MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-3.5-turbo",
    ]
    PROMPT = "Open backend prompts"

    # Buttons
    SEND_BUTTON = "📤"
    RESET_BUTTON = "🧹 Reset conversation"
    CLEAR_HISTORY = "Clear history"

    # History
    HISTORY_TITLE = "## 💬 Conversation history"
    USER_ICON = "🧑‍💼"
    ASSISTANT_ICON = "🤖"

    # Colors
    USER_COLOR = "#4A3A69"
    ASSISTANT_COLOR = "#F0F0F5"
    FONT_COLOR_USER = "white"
    FONT_COLOR_ASSISTANT = "black"

    # Logos / assets (relative to the project root)
    LOGO_URL = "assets/logo.png"
    LOGO_URL_LIGHT = "assets/logo_light.png"
    PBI_LOGO_URL = "assets/powerbi_logo.png"

    # Feedback
    FEEDBACK = "Give feedback on the assistant"
    ISSUES = [
        "Incomplete answer",
        "Imprecise answer",
        "Vague answer",
        "Bad formulation",
        "Bad behaviour of the AI",
        "Correct answer",
        "Other comment",
    ]
    QUESTION = "Any issue with the answer?"
    SEND = "Send feedback"
    THANKS = "Thanks for the feedback!"
    COM = "Free comment (optional)"

    # AI parameters
    AI_ANALYSIS_HEADER = "AI-Powered Analysis"
    AI_PROMPT_LABEL = "Ask a question about this data"
    AI_DEFAULT_PROMPT = "Analyse key trends and insights from this pivot table"
    AI_BUTTON_LABEL = "Get AI Analysis"
    AI_SEND_LABEL = "Send"
    AI_ANALYSIS_PROMPTS = [
        "What are the main trends?",
        "Identify anomalies or outliers",
        "Suggest business recommendations",
        "Compare performance across segments",
    ]
    AI_MODEL_NAME = "gpt-4o-mini"
    AI_TEMPERATURE = 0.3
    AI_MODES = ["Automatic analysis", "Chatbot"]
    AI_AUTO = "General analysis of the table"
    AI_LOAD = "Analysis in progress…"
    AI_RESOURCES = "AI Resources Configuration"
    GLOSS = "Personal definitions"

    EXCEL = "Knowledge Base for AI"
