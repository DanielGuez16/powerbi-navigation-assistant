class Streamlit:
    # Titres et descriptions
    APP_TITLE = "Power BI Assistant"
    PAGE_TITLE = "AI Assistant - Power BI"
    X ="X"
    SUBTITLE = "Your smart copilot for navigating Power BI reports"
    LOG_FILE_NAME = "log_PBIxAI"

    # Champ de saisie
    AI_QUERY = "💬 How can I help you ?"
    PLACEHOLDER = "E.g. : Show me the reports on consolidated balance sheet. Or : Rapports sur le MTLO ? "
    ANALYSE = "Analysis of the Power BI reports ..."

 
    # Barre latérale
    PARAM = "You can choose the search mode :"
    MODE_LABEL = "Search mode"
    MODES = ["Smart search", "Data analysis (coming soon)"]
    MODEL_LABEL = "AI Models"
    IAS = "You can choose between the available AI models :"
    IA_MODELS = [
    "gemini-1.5-pro-002",
    "gpt-4o-2024-08-06",
    "gpt-4-32k-0613",
    "gpt-4o-2024-05-13",
    "gpt-4o-mini-2024-07-18",
    "gemini-1.5-flash-002",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite-001"
] #à remplir manuellement en exécutant llm_connector.list_all_models dans utils/llm_connector.py
    PROMPT = "Access the backend prompts"


    # Boutons
    SEND_BUTTON = "📤"
    RESET_BUTTON = "🧹 Reset conversation"
    CLEAR_HISTORY = "Clear history"

    # Historique
    HISTORY_TITLE = "## 💬 Conversation history"
    USER_ICON = "🧑‍💼"
    ASSISTANT_ICON = "🤖"

    # Couleurs
    USER_COLOR = "#4A3A69"
    ASSISTANT_COLOR = "#F0F0F5"
    FONT_COLOR_USER = "white"
    FONT_COLOR_ASSISTANT = "black"

    # Logos
    BPCE_LOGO_URL_BLANC = "front/src/bpce_logo_blanc.png"
    BPCE_LOGO_URL = "front/src/bpce_logo.png"
    PBI_LOGO_URL = "front/src/image_pbi.png.png"
    LOGO = "front/src/bpce_x_ai_x_pbi.png"

    # Feedback
    FEEDBACK = "Give your feedback on the assistant"
    ISSUES = [
                "Uncomplete answer",
                "Imprecise answer",
                "Vague answer",
                "Bad formulation",
                "Bad behavior of the AI",
                "Correct answer",
                "Other comment",
]
    QUESTION = "Any issue with the answer ?"
    SEND = "Send feedback"
    THANKS = "Thanks for the feedback !"
    COM = "Free comment (optional)"


    # ========== AI PARAMETERS ==========
    AI_ANALYSIS_HEADER = "AI-Powered Analysis"
    AI_PROMPT_LABEL = "Ask a question about this data"
    AI_DEFAULT_PROMPT = "Analyze key trends and insights from this pivot table"
    AI_BUTTON_LABEL = "Get AI Analysis"
    AI_SEND_LABEL = "Send"
    AI_ANALYSIS_PROMPTS = [
        "What are the main trends?",
        "Identify anomalies or outliers",
        "Suggest business recommendations",
        "Compare performance across segments"
    ]
    AI_MODEL_NAME = "gpt-4"  # ou "gpt-3.5-turbo" selon votre budget
    AI_TEMPERATURE = 0.3  # Pour des réponses plus factuelles
    AI_MODES = ["Automatic analysis", "ChatBot"]
    AI_AUTO = "General analysis of the table"
    AI_LOAD = "Analysis in progress by AI..."
    AI_RESSOURCES = "AI Ressources Configuration"
    GLOSS = "Personnal definitions"

    EXCEL = "Knowledge Base for AI"
